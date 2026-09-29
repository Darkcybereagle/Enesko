from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category, Conversation, Facility, Floor, KnowledgeDocument, Mall, Store, Zone
from app.schemas import (
    ChatRequest, ChatResponse, FacilityOut, FloorOut, KnowledgeCreate,
    KnowledgeOut, MallOut, StoreOut, ZoneOut,
)
from app.services import orchestrate
from app.security import Role, User, require_roles

router = APIRouter(prefix="/api/v1")


@router.get("/malls", response_model=list[MallOut], tags=["Mall Core"])
def list_malls(db: Session = Depends(get_db)):
    return list(db.scalars(select(Mall).order_by(Mall.name)).all())


@router.get("/floors", response_model=list[FloorOut], tags=["Mall Core"])
def list_floors(mall_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Floor).order_by(Floor.level)
    if mall_id is not None:
        stmt = stmt.where(Floor.mall_id == mall_id)
    return list(db.scalars(stmt).all())


@router.get("/zones", response_model=list[ZoneOut], tags=["Mall Core"])
def list_zones(floor_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Zone).order_by(Zone.code)
    if floor_id is not None:
        stmt = stmt.where(Zone.floor_id == floor_id)
    return list(db.scalars(stmt).all())


@router.get("/stores", response_model=list[StoreOut], tags=["Mall Core"])
def list_stores(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    stmt = (
        select(Store)
        .options(selectinload(Store.categories))
        .where(
            Store.active.is_(True),
            or_(Store.expires_at.is_(None), Store.expires_at >= now),
        )
    )
    if q:
        pattern = f"%{q}%"
        stmt = stmt.outerjoin(Store.categories).where(
            or_(
                Store.name.ilike(pattern),
                Store.description.ilike(pattern),
                Category.name.ilike(pattern),
            )
        )
    if category:
        stmt = stmt.join(Store.categories).where(Category.name.ilike(f"%{category}%"))
    return list(db.scalars(stmt.order_by(Store.name)).unique().all())


@router.get("/stores/{store_id}", response_model=StoreOut, tags=["Mall Core"])
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.scalar(
        select(Store).options(selectinload(Store.categories)).where(Store.id == store_id)
    )
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.get("/facilities", response_model=list[FacilityOut], tags=["Mall Core"])
def list_facilities(db: Session = Depends(get_db)):
    return list(db.scalars(select(Facility).order_by(Facility.asset_code)).all())


@router.post("/knowledge", response_model=KnowledgeOut, status_code=201, tags=["Knowledge"])
def create_knowledge(payload: KnowledgeCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.PLATFORM_SUPER_ADMIN, Role.MALL_ADMINISTRATOR))):
    doc = KnowledgeDocument(**payload.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/knowledge", response_model=list[KnowledgeOut], tags=["Knowledge"])
def list_knowledge(db: Session = Depends(get_db)):
    return list(db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc())).all())


@router.post("/assistant/chat", response_model=ChatResponse, tags=["Assistant"])
def assistant_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    result = orchestrate(db, payload.message)
    db.add(Conversation(
        channel=payload.channel,
        user_text=payload.message,
        assistant_text=result["answer"],
        intent=result["intent"],
        needs_human=result["needs_human"],
    ))
    db.commit()
    return result
