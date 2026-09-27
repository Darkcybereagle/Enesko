from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.database import Base, get_db


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    case_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), default="OPEN", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    channel: Mapped[str] = mapped_column(String(30), default="web")
    summary: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    item_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_location: Mapped[str | None] = mapped_column(String(240), nullable=True)
    distinguishing_features: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    events: Mapped[list["CaseEvent"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CaseEvent(Base):
    __tablename__ = "case_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    note: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    case: Mapped[Case] = relationship(back_populates="events")


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(30), default="dashboard")
    recipient: Mapped[str] = mapped_column(String(160), default="customer_service")
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CaseCreate(BaseModel):
    case_type: str = Field(min_length=2, max_length=50)
    summary: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=2, max_length=4000)
    priority: str = "NORMAL"
    channel: str = "web"
    contact: str | None = None
    item_description: str | None = None
    last_seen_location: str | None = None
    distinguishing_features: str | None = None


class CaseStatusUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=30)
    note: str = Field(min_length=2, max_length=2000)
    actor: str = "staff"


class CaseEventCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=50)
    note: str = Field(min_length=2, max_length=2000)
    actor: str = "staff"


class CaseEventOut(BaseModel):
    id: int
    event_type: str
    note: str
    actor: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CaseOut(BaseModel):
    id: int
    reference: str
    case_type: str
    status: str
    priority: str
    channel: str
    summary: str
    description: str
    contact: str | None
    item_description: str | None
    last_seen_location: str | None
    distinguishing_features: str | None
    created_at: datetime
    updated_at: datetime
    events: list[CaseEventOut] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class NotificationOut(BaseModel):
    id: int
    case_id: int | None
    channel: str
    recipient: str
    message: str
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


def create_case_record(db: Session, payload: CaseCreate) -> Case:
    case = Case(reference=f"ENK-{uuid4().hex[:10].upper()}", **payload.model_dump())
    db.add(case)
    db.flush()
    db.add(CaseEvent(case_id=case.id, event_type="CREATED", note="Case created", actor="system"))
    db.add(Notification(
        case_id=case.id, channel="dashboard", recipient="customer_service",
        message=f"New {case.case_type} case {case.reference}: {case.summary}",
    ))
    db.commit()
    db.refresh(case)
    return case


def seed_phase3(db: Session) -> None:
    if db.scalar(select(Case).where(Case.reference == "ENK-DEMO-CASE")):
        return
    case = Case(
        reference="ENK-DEMO-CASE", case_type="COMPLAINT", status="OPEN", priority="NORMAL",
        channel="web", summary="Demo facility complaint",
        description="Development-only case used to verify the Phase 3 case workflow.",
        contact="demo@example.invalid",
    )
    db.add(case)
    db.flush()
    db.add(CaseEvent(case_id=case.id, event_type="CREATED", note="Demo case created", actor="seed"))
    db.add(Notification(
        case_id=case.id, channel="dashboard", recipient="customer_service",
        message="Demo Phase 3 case notification",
    ))
    db.commit()


router = APIRouter(prefix="/api/v1", tags=["Cases"])


@router.post("/cases", response_model=CaseOut, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    return create_case_record(db, payload)


@router.get("/cases", response_model=list[CaseOut])
def list_cases(status: str | None = None, case_type: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Case).order_by(Case.created_at.desc())
    if status:
        stmt = stmt.where(Case.status == status.upper())
    if case_type:
        stmt = stmt.where(Case.case_type == case_type.upper())
    return list(db.scalars(stmt).unique().all())


def _case_or_404(db: Session, reference: str) -> Case:
    case = db.scalar(select(Case).where(Case.reference == reference))
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.get("/cases/{reference}", response_model=CaseOut)
def get_case(reference: str, db: Session = Depends(get_db)):
    return _case_or_404(db, reference)


@router.patch("/cases/{reference}/status", response_model=CaseOut)
def update_case_status(reference: str, payload: CaseStatusUpdate, db: Session = Depends(get_db)):
    case = _case_or_404(db, reference)
    case.status = payload.status.upper()
    case.updated_at = datetime.utcnow()
    db.add(CaseEvent(case_id=case.id, event_type="STATUS_CHANGED", note=payload.note, actor=payload.actor))
    db.commit()
    db.refresh(case)
    return case


@router.post("/cases/{reference}/events", response_model=CaseEventOut, status_code=201)
def add_case_event(reference: str, payload: CaseEventCreate, db: Session = Depends(get_db)):
    case = _case_or_404(db, reference)
    event = CaseEvent(case_id=case.id, **payload.model_dump())
    case.updated_at = datetime.utcnow()
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_db)):
    return list(db.scalars(select(Notification).order_by(Notification.created_at.desc())).all())
