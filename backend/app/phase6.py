from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from app.database import Base, get_db
from app.models import Mall
from app.security import Role,User,require_roles

class Activation(Base):
    __tablename__="activations"
    id: Mapped[int]=mapped_column(primary_key=True)
    reference: Mapped[str]=mapped_column(String(32),unique=True,index=True)
    mall_id: Mapped[int]=mapped_column(ForeignKey("malls.id",ondelete="CASCADE"),index=True)
    applicant_name: Mapped[str]=mapped_column(String(200))
    contact: Mapped[str]=mapped_column(String(200))
    title: Mapped[str]=mapped_column(String(240))
    description: Mapped[str]=mapped_column(Text)
    proposed_date: Mapped[str]=mapped_column(String(40))
    status: Mapped[str]=mapped_column(String(40),default="SUBMITTED")
    current_stage: Mapped[str]=mapped_column(String(60),default="INTAKE")
    data_status: Mapped[str]=mapped_column(String(30),default="DEMO")
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class ActivationCreate(BaseModel):
    applicant_name:str; contact:str; title:str; description:str; proposed_date:str

class ActivationOut(BaseModel):
    id:int; reference:str; mall_id:int; applicant_name:str; contact:str; title:str; description:str
    proposed_date:str; status:str; current_stage:str; data_status:str; created_at:datetime
    model_config=ConfigDict(from_attributes=True)

class ActivationStageUpdate(BaseModel):
    current_stage:str=Field(min_length=2,max_length=60)
    status:str=Field(default="IN_REVIEW",min_length=2,max_length=40)

def seed_phase6(db:Session):
    if db.scalar(select(Activation).where(Activation.reference=="ENK-DEMO-ACT")): return
    mall=db.scalar(select(Mall).where(Mall.name=="Ikeja City Mall"))
    if mall:
        db.add(Activation(reference="ENK-DEMO-ACT",mall_id=mall.id,applicant_name="Demo Applicant",
          contact="demo@example.invalid",title="Demo Mall Activation",description="Development-only activation.",
          proposed_date="DEMO",data_status="DEMO")); db.commit()

router=APIRouter(prefix="/api/v1",tags=["Activations & Events"])

@router.post("/activations",response_model=ActivationOut,status_code=201)
def create_activation(payload:ActivationCreate,db:Session=Depends(get_db)):
    mall=db.scalar(select(Mall).order_by(Mall.id))
    if not mall: raise HTTPException(409,"Mall must exist before activation intake")
    row=Activation(reference=f"ENK-ACT-{uuid4().hex[:8].upper()}",mall_id=mall.id,**payload.model_dump(),data_status="DEMO")
    db.add(row); db.commit(); db.refresh(row); return row

@router.get("/activations",response_model=list[ActivationOut])
def list_activations(db:Session=Depends(get_db)):
    return list(db.scalars(select(Activation).order_by(Activation.created_at.desc())).all())

@router.patch("/activations/{reference}/stage",response_model=ActivationOut)
def update_activation(reference:str,payload:ActivationStageUpdate,db:Session=Depends(get_db),user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR,Role.MARKETING))):
    row=db.scalar(select(Activation).where(Activation.reference==reference))
    if not row: raise HTTPException(404,"Activation not found")
    row.current_stage=payload.current_stage.upper(); row.status=payload.status.upper(); db.commit(); db.refresh(row); return row
