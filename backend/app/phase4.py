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
    data_status: Mapped[str] = mapped_column(String(30), default="DEMO")


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
        reversed_steps.append({"from_node": by_id[parent].code, "to_node": by_id[cursor].code,
                               "instruction": instruction, "distance_m": distance})
        cursor = parent
    steps = list(reversed(reversed_steps))
    statuses = {by_id[start.id].data_status, by_id[end.id].data_status}
    return {"from_node": start.code, "to_node": end.code, "total_distance_m": round(distances[end.id], 1),
            "accessible_only": accessible_only, "steps": steps,
            "data_status": "VERIFIED" if statuses == {"VERIFIED"} else "DEMO"}


def seed_phase4(db: Session) -> None:
    if db.scalar(select(MapNode).where(MapNode.code == "DEMO-ENTRANCE-1")):
        return
    from app.models import Floor, Mall, Zone
    mall = db.scalar(select(Mall).where(Mall.name == "Ikeja City Mall"))
    if not mall:
        return
    ground = db.scalar(select(Floor).where(Floor.mall_id == mall.id, Floor.level == 0))
    zone_a = db.scalar(select(Zone).where(Zone.floor_id == ground.id).order_by(Zone.id)) if ground else None
    entrance = MapNode(mall_id=mall.id, floor_id=ground.id if ground else None, zone_id=zone_a.id if zone_a else None,
                       code="DEMO-ENTRANCE-1", name="Demo Entrance 1", node_type="ENTRANCE",
                       qr_code="ENESKO-DEMO-ENTRANCE-1", data_status="DEMO")
    junction = MapNode(mall_id=mall.id, floor_id=ground.id if ground else None, zone_id=zone_a.id if zone_a else None,
                       code="DEMO-JUNCTION-A", name="Demo Junction A", node_type="WAYPOINT",
                       qr_code="ENESKO-DEMO-JUNCTION-A", data_status="DEMO")
    sports = MapNode(mall_id=mall.id, floor_id=ground.id if ground else None, zone_id=zone_a.id if zone_a else None,
                     code="DEMO-SPORTS-STORE", name="Demo Sports Store", node_type="STORE",
                     qr_code="ENESKO-DEMO-SPORTS-STORE", data_status="DEMO")
    db.add_all([entrance, junction, sports])
    db.flush()
    db.add_all([
        MapEdge(from_node_id=entrance.id, to_node_id=junction.id, distance_m=25.0,
                instruction="Proceed straight from Demo Entrance 1 to Demo Junction A.",
                accessible=True, bidirectional=True),
        MapEdge(from_node_id=junction.id, to_node_id=sports.id, distance_m=18.0,
                instruction="Continue from Demo Junction A to Demo Sports Store.",
                accessible=True, bidirectional=True),
    ])
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
