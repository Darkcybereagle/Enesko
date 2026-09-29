from datetime import datetime
from fastapi import APIRouter,Depends
from pydantic import BaseModel,ConfigDict
from sqlalchemy import DateTime,Integer,String,select
from sqlalchemy.orm import Mapped,Session,mapped_column
from app.database import Base,get_db
from app.security import Role,User,require_roles
class ParkingObservation(Base):
    __tablename__="parking_observations"
    id:Mapped[int]=mapped_column(primary_key=True)
    area_code:Mapped[str]=mapped_column(String(80),index=True)
    source_type:Mapped[str]=mapped_column(String(40))
    occupied:Mapped[int|None]=mapped_column(Integer,nullable=True)
    available:Mapped[int|None]=mapped_column(Integer,nullable=True)
    confidence:Mapped[int|None]=mapped_column(Integer,nullable=True)
    data_status:Mapped[str]=mapped_column(String(30),default="UNVERIFIED")
    observed_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class ObservationCreate(BaseModel):
    area_code:str;source_type:str;occupied:int|None=None;available:int|None=None;confidence:int|None=None;data_status:str="UNVERIFIED"
class ObservationOut(ObservationCreate):
    id:int;observed_at:datetime
    model_config=ConfigDict(from_attributes=True)
def seed_phase12(db): return
router=APIRouter(prefix="/api/v1",tags=["Smart Parking"])
@router.post("/parking/observations",response_model=ObservationOut,status_code=201)
def observe(payload:ObservationCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR,Role.PARKING))):
    row=ParkingObservation(**payload.model_dump());db.add(row);db.commit();db.refresh(row);return row
@router.get("/parking/observations",response_model=list[ObservationOut])
def observations(db:Session=Depends(get_db)): return list(db.scalars(select(ParkingObservation).order_by(ParkingObservation.id.desc())).all())
