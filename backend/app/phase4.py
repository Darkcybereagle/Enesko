import heapq
from math import inf

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Float, ForeignKey, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base, get_db


class MapNode(Base):
    __tablename__ = "map_nodes"
    id: Mapped[int] = mapped_column(primary_key=True)
    mall_id: Mapped[int] = mapped_column(ForeignKey("malls.id", ondelete="CASCADE"), index=True)
    floor_id: Mapped[int | None] = mapped_column(ForeignKey("floors.id", ondelete="SET NULL"), nullable=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    node_type: Mapped[str] = mapped_column(String(50), default="WAYPOINT")
    qr_code: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    data_status: Mapped[str] = mapped_column(String(30), default="REFERENCE_MODEL")


class MapEdge(Base):
    __tablename__ = "map_edges"
    id: Mapped[int] = mapped_column(primary_key=True)
    from_node_id: Mapped[int] = mapped_column(ForeignKey("map_nodes.id", ondelete="CASCADE"), index=True)
    to_node_id: Mapped[int] = mapped_column(ForeignKey("map_nodes.id", ondelete="CASCADE"), index=True)
    distance_m: Mapped[float] = mapped_column(Float)
    instruction: Mapped[str] = mapped_column(String(300))
    accessible: Mapped[bool] = mapped_column(Boolean, default=True)
    bidirectional: Mapped[bool] = mapped_column(Boolean, default=True)


class MapNodeOut(BaseModel):
    id: int
    mall_id: int
    floor_id: int | None
    zone_id: int | None
    code: str
    name: str
    node_type: str
    qr_code: str | None
    data_status: str
    model_config = ConfigDict(from_attributes=True)


class MapEdgeOut(BaseModel):
    id: int
    from_node_id: int
    to_node_id: int
    distance_m: float
    instruction: str
    accessible: bool
    bidirectional: bool
    model_config = ConfigDict(from_attributes=True)


class RouteStep(BaseModel):
    from_node: str
    to_node: str
    instruction: str
    distance_m: float


class RouteOut(BaseModel):
    from_node: str
    to_node: str
    total_distance_m: float
    accessible_only: bool
    steps: list[RouteStep]
    data_status: str


def calculate_route(db: Session, start_code: str, end_code: str, accessible_only: bool) -> dict:
    nodes = list(db.scalars(select(MapNode)).all())
    by_id = {n.id: n for n in nodes}
    by_code = {n.code: n for n in nodes}
    start, end = by_code.get(start_code), by_code.get(end_code)
    if not start or not end:
        raise HTTPException(status_code=404, detail="Start or destination map node not found")

    graph: dict[int, list[tuple[int, float, str]]] = {n.id: [] for n in nodes}
    for edge in db.scalars(select(MapEdge)).all():
        if accessible_only and not edge.accessible:
            continue
        graph[edge.from_node_id].append((edge.to_node_id, edge.distance_m, edge.instruction))
        if edge.bidirectional:
            graph[edge.to_node_id].append((edge.from_node_id, edge.distance_m, f"Return via {edge.instruction}"))

    distances = {n.id: inf for n in nodes}
    distances[start.id] = 0.0
    previous: dict[int, tuple[int, str, float]] = {}
    queue = [(0.0, start.id)]
    while queue:
        current_distance, node_id = heapq.heappop(queue)
        if current_distance != distances[node_id]:
            continue
        if node_id == end.id:
            break
        for neighbor, distance, instruction in graph[node_id]:
            candidate = current_distance + distance
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                previous[neighbor] = (node_id, instruction, distance)
                heapq.heappush(queue, (candidate, neighbor))

    if distances[end.id] == inf:
        raise HTTPException(status_code=404, detail="No route found for the requested accessibility mode")

    reversed_steps = []
    cursor = end.id
    while cursor != start.id:
        parent, instruction, distance = previous[cursor]
        reversed_steps.append({
            "from_node": by_id[parent].code,
            "to_node": by_id[cursor].code,
            "instruction": instruction,
            "distance_m": distance,
        })
        cursor = parent

    steps = list(reversed(reversed_steps))
    statuses = {by_id[start.id].data_status, by_id[end.id].data_status}
    if statuses == {"VERIFIED"}:
        route_status = "VERIFIED"
    elif "REFERENCE_MODEL" in statuses:
        route_status = "REFERENCE_MODEL"
    else:
        route_status = "UNVERIFIED"

    return {
        "from_node": start.code,
        "to_node": end.code,
        "total_distance_m": round(distances[end.id], 1),
        "accessible_only": accessible_only,
        "steps": steps,
        "data_status": route_status,
    }


def _node_by_any_code(db: Session, *codes: str) -> MapNode | None:
    return db.scalar(select(MapNode).where(MapNode.code.in_(codes)).order_by(MapNode.id))


def _upsert_reference_node(
    db: Session,
    *,
    mall_id: int,
    code: str,
    name: str,
    node_type: str,
    floor_id: int | None,
    zone_id: int | None = None,
) -> MapNode:
    node = db.scalar(select(MapNode).where(MapNode.code == code))
    if not node:
        node = MapNode(mall_id=mall_id, code=code, name=name)
        db.add(node)
    node.mall_id = mall_id
    node.floor_id = floor_id
    node.zone_id = zone_id
    node.name = name
    node.node_type = node_type
    node.qr_code = f"ENESKO-{code}"
    node.data_status = "REFERENCE_MODEL"
    db.flush()
    return node


def _upsert_reference_edge(
    db: Session,
    *,
    start: MapNode,
    end: MapNode,
    distance_m: float,
    instruction: str,
    accessible: bool = True,
) -> MapEdge:
    edge = db.scalar(
        select(MapEdge).where(
            MapEdge.from_node_id == start.id,
            MapEdge.to_node_id == end.id,
        )
    )
    if not edge:
        edge = MapEdge(from_node_id=start.id, to_node_id=end.id)
        db.add(edge)
    edge.distance_m = distance_m
    edge.instruction = instruction
    edge.accessible = accessible
    edge.bidirectional = True
    return edge


def seed_phase4(db: Session) -> None:
    from app.models import Floor, Mall, Zone

    mall = db.scalar(select(Mall).where(Mall.name == "Ikeja City Mall"))
    if not mall:
        return

    ground = db.scalar(select(Floor).where(Floor.mall_id == mall.id, Floor.level == 0))
    top = db.scalar(select(Floor).where(Floor.mall_id == mall.id, Floor.level == 1))
    ground_zone = (
        db.scalar(select(Zone).where(Zone.floor_id == ground.id).order_by(Zone.id))
        if ground
        else None
    )
    top_zone = (
        db.scalar(select(Zone).where(Zone.floor_id == top.id).order_by(Zone.id))
        if top
        else None
    )

    entrance1 = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-ENTRANCE-1",
        name="Entrance 1",
        node_type="ENTRANCE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    entrance2 = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-ENTRANCE-2",
        name="Entrance 2",
        node_type="ENTRANCE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    entrance3 = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-ENTRANCE-3",
        name="Food Court-side Entrance",
        node_type="ENTRANCE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    atrium = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-ATRIUM-1",
        name="Atrium One Reference",
        node_type="LANDMARK",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    concourse = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-CONCOURSE-A",
        name="Main Concourse",
        node_type="WAYPOINT",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    vertical_ground = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-VERTICAL-CORE-G",
        name="Escalator / Elevator Core — Ground",
        node_type="VERTICAL_CIRCULATION",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    vertical_top = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-VERTICAL-CORE-T",
        name="Escalator / Elevator Core — Top",
        node_type="VERTICAL_CIRCULATION",
        floor_id=top.id if top else None,
        zone_id=top_zone.id if top_zone else None,
    )
    top_concourse = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-TOP-CONCOURSE",
        name="Top Floor Concourse",
        node_type="WAYPOINT",
        floor_id=top.id if top else None,
        zone_id=top_zone.id if top_zone else None,
    )
    food_court = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-FOOD-COURT",
        name="Food Court Reference Area",
        node_type="LANDMARK",
        floor_id=top.id if top else None,
        zone_id=top_zone.id if top_zone else None,
    )

    samsung = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-SAMSUNG",
        name="Samsung Experience Store",
        node_type="STORE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    miniso = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-MINISO",
        name="Miniso — Shop 19+20",
        node_type="STORE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    istore = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-ISTORE",
        name="iStore — Shop L62",
        node_type="STORE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    pointek = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-POINTEK",
        name="Pointek — Shop L28",
        node_type="STORE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    healthplus = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-HEALTHPLUS",
        name="HealthPlus — Shop L29",
        node_type="STORE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    ruff = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-RUFF",
        name="Ruff 'n' Tumble — Shop L47",
        node_type="STORE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    studio24 = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-STUDIO24",
        name="Studio24 — Shop L48",
        node_type="STORE",
        floor_id=ground.id if ground else None,
        zone_id=ground_zone.id if ground_zone else None,
    )
    ocean = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-OCEAN-BASKET",
        name="Ocean Basket — Shop U06",
        node_type="STORE",
        floor_id=top.id if top else None,
        zone_id=top_zone.id if top_zone else None,
    )
    silverbird = _upsert_reference_node(
        db,
        mall_id=mall.id,
        code="ICM-SILVERBIRD",
        name="Silverbird Cinemas",
        node_type="ENTERTAINMENT",
        floor_id=top.id if top else None,
        zone_id=top_zone.id if top_zone else None,
    )

    # Reference topology only. Distances and turns are indicative until ICM supplies
    # an authorized current floor plan or ENESKO completes a measured site survey.
    _upsert_reference_edge(
        db,
        start=entrance2,
        end=concourse,
        distance_m=25.0,
        instruction="Proceed from Entrance 2 toward the main concourse.",
    )
    _upsert_reference_edge(
        db,
        start=concourse,
        end=samsung,
        distance_m=18.0,
        instruction="Continue from the main concourse toward the Samsung Experience Store.",
    )
    _upsert_reference_edge(
        db,
        start=entrance1,
        end=atrium,
        distance_m=22.0,
        instruction="Proceed from Entrance 1 toward the central atrium reference area.",
    )
    _upsert_reference_edge(
        db,
        start=atrium,
        end=concourse,
        distance_m=20.0,
        instruction="Continue from the atrium reference area toward the main concourse.",
    )
    _upsert_reference_edge(
        db,
        start=entrance3,
        end=vertical_ground,
        distance_m=16.0,
        instruction="Proceed from the food-court-side entrance toward the escalator and elevator core.",
    )
    _upsert_reference_edge(
        db,
        start=concourse,
        end=vertical_ground,
        distance_m=18.0,
        instruction="Continue from the main concourse toward the escalator and elevator core.",
    )
    _upsert_reference_edge(
        db,
        start=vertical_ground,
        end=vertical_top,
        distance_m=12.0,
        instruction="Use the elevator for an accessible route to the top floor.",
        accessible=True,
    )
    _upsert_reference_edge(
        db,
        start=vertical_top,
        end=top_concourse,
        distance_m=10.0,
        instruction="Exit the vertical circulation core into the top-floor concourse.",
    )
    _upsert_reference_edge(
        db,
        start=top_concourse,
        end=food_court,
        distance_m=16.0,
        instruction="Continue along the top-floor reference concourse toward the food court.",
    )

    for node, distance, instruction in (
        (miniso, 14.0, "Continue from the main concourse toward the Miniso reference position."),
        (istore, 24.0, "Continue along the ground-floor reference concourse toward iStore."),
        (pointek, 12.0, "Continue along the ground-floor reference concourse toward Pointek."),
        (healthplus, 13.0, "Continue along the ground-floor reference concourse toward HealthPlus."),
        (ruff, 19.0, "Continue along the ground-floor reference concourse toward Ruff 'n' Tumble."),
        (studio24, 20.0, "Continue along the Entrance 2 reference corridor toward Studio24."),
    ):
        _upsert_reference_edge(
            db,
            start=concourse,
            end=node,
            distance_m=distance,
            instruction=instruction,
        )

    _upsert_reference_edge(
        db,
        start=top_concourse,
        end=ocean,
        distance_m=15.0,
        instruction="Continue along the top-floor reference concourse toward Ocean Basket.",
    )
    _upsert_reference_edge(
        db,
        start=top_concourse,
        end=silverbird,
        distance_m=22.0,
        instruction="Continue along the top-floor reference concourse toward Silverbird Cinemas.",
    )

    db.commit()


router = APIRouter(prefix="/api/v1", tags=["Indoor Navigation"])


@router.get("/map/nodes", response_model=list[MapNodeOut])
def list_map_nodes(db: Session = Depends(get_db)):
    return list(db.scalars(select(MapNode).order_by(MapNode.code)).all())


@router.get("/map/edges", response_model=list[MapEdgeOut])
def list_map_edges(db: Session = Depends(get_db)):
    return list(db.scalars(select(MapEdge).order_by(MapEdge.id)).all())


@router.get("/map/qr/{qr_code}", response_model=MapNodeOut)
def resolve_qr(qr_code: str, db: Session = Depends(get_db)):
    node = db.scalar(select(MapNode).where(MapNode.qr_code == qr_code))
    if not node:
        raise HTTPException(status_code=404, detail="QR location not found")
    return node


@router.get("/navigation/route", response_model=RouteOut)
def route(from_node: str, to_node: str, accessible_only: bool = False, db: Session = Depends(get_db)):
    return calculate_route(db, from_node, to_node, accessible_only)
