from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base, get_db
from app.phase3 import CaseCreate, CaseOut, create_case_record


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(primary_key=True)
    mall_id: Mapped[int] = mapped_column(ForeignKey("malls.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    primary_contact_name: Mapped[str] = mapped_column(String(160))
    primary_contact: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    data_status: Mapped[str] = mapped_column(String(30), default="DEMO")


class TenantRequest(Base):
    __tablename__ = "tenant_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), unique=True, index=True)
    request_type: Mapped[str] = mapped_column(String(60), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TenantOut(BaseModel):
    id: int
    mall_id: int
    name: str
    unit: str | None
    primary_contact_name: str
    primary_contact: str
    active: bool
    data_status: str
    model_config = ConfigDict(from_attributes=True)


class TenantRequestCreate(BaseModel):
    request_type: str = Field(min_length=2, max_length=60)
    summary: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=2, max_length=4000)
    priority: str = "NORMAL"
    channel: str = "tenant_portal"


class TenantRequestOut(BaseModel):
    id: int
    tenant_id: int
    case_id: int
    request_type: str
    created_at: datetime
    case: CaseOut


def seed_phase5(db: Session) -> None:
    if db.scalar(select(Tenant).where(Tenant.name == "Demo Sports Tenant")):
        return
    from app.models import Mall
    mall = db.scalar(select(Mall).where(Mall.name == "Ikeja City Mall"))
    if not mall:
        return
    db.add(Tenant(
        mall_id=mall.id, name="Demo Sports Tenant", unit="DEMO-G12",
        primary_contact_name="Demo Tenant Manager",
        primary_contact="demo-tenant@example.invalid", data_status="DEMO",
    ))
    db.commit()


router = APIRouter(prefix="/api/v1", tags=["Tenant Platform"])


def _tenant_or_404(db: Session, tenant_id: int) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if not tenant or not tenant.active:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.get("/tenants", response_model=list[TenantOut])
def list_tenants(db: Session = Depends(get_db)):
    return list(db.scalars(select(Tenant).where(Tenant.active.is_(True)).order_by(Tenant.name)).all())


@router.get("/tenants/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    return _tenant_or_404(db, tenant_id)


@router.post("/tenants/{tenant_id}/requests", response_model=TenantRequestOut, status_code=201)
def create_tenant_request(tenant_id: int, payload: TenantRequestCreate, db: Session = Depends(get_db)):
    tenant = _tenant_or_404(db, tenant_id)
    case = create_case_record(db, CaseCreate(
        case_type=f"TENANT_{payload.request_type.upper()}",
        summary=payload.summary, description=payload.description,
        priority=payload.priority, channel=payload.channel, contact=tenant.primary_contact,
    ))
    link = TenantRequest(tenant_id=tenant.id, case_id=case.id, request_type=payload.request_type.upper())
    db.add(link)
    db.commit()
    db.refresh(link)
    return {"id": link.id, "tenant_id": link.tenant_id, "case_id": link.case_id,
            "request_type": link.request_type, "created_at": link.created_at, "case": case}


@router.get("/tenants/{tenant_id}/requests", response_model=list[TenantRequestOut])
def list_tenant_requests(tenant_id: int, db: Session = Depends(get_db)):
    _tenant_or_404(db, tenant_id)
    links = list(db.scalars(select(TenantRequest).where(TenantRequest.tenant_id == tenant_id)
                            .order_by(TenantRequest.created_at.desc())).all())
    from app.phase3 import Case
    cases = {c.id: c for c in db.scalars(select(Case).where(Case.id.in_([x.case_id for x in links]))).all()} if links else {}
    return [{"id": link.id, "tenant_id": link.tenant_id, "case_id": link.case_id,
             "request_type": link.request_type, "created_at": link.created_at, "case": cases[link.case_id]}
            for link in links]
