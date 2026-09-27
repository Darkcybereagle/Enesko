from datetime import datetime,timedelta
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict
from sqlalchemy import DateTime,Integer,String,select
from sqlalchemy.orm import Mapped,Session,mapped_column
from app.database import Base,get_db
from app.security import Role,User,require_roles
class ParkingStatus(Base):
    __tablename__="parking_status"
    id:Mapped[int]=mapped_column(primary_key=True)
    area_code:Mapped[str]=mapped_column(String(80),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(200))
    capacity:Mapped[int|None]=mapped_column(Integer,nullable=True)
    occupancy_status:Mapped[str]=mapped_column(String(40),default="UNKNOWN")
    source:Mapped[str]=mapped_column(String(80),default="staff")
    data_status:Mapped[str]=mapped_column(String(30),default="DEMO")
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    expires_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
class ParkingUpdate(BaseModel): occupancy_status:str; expires_minutes:int=30
class ParkingOut(BaseModel):
    id:int;area_code:str;name:str;capacity:int|None;occupancy_status:str;source:str;data_status:str;updated_at:datetime;expires_at:datetime|None
    model_config=ConfigDict(from_attributes=True)
def seed_phase10(db:Session):
    if not db.scalar(select(ParkingStatus).where(ParkingStatus.area_code=="DEMO-P1")):
        db.add(ParkingStatus(area_code="DEMO-P1",name="Demo Parking Area",capacity=None,occupancy_status="UNKNOWN",source="development_seed",data_status="DEMO"));db.commit()
router=APIRouter(prefix="/api/v1",tags=["Parking"])
@router.get("/parking",response_model=list[ParkingOut])
def parking(db:Session=Depends(get_db)): return list(db.scalars(select(ParkingStatus)).all())
@router.patch("/parking/{area_code}/status",response_model=ParkingOut)
def update(area_code:str,payload:ParkingUpdate,db:Session=Depends(get_db),user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR,Role.PARKING))):
    row=db.scalar(select(ParkingStatus).where(ParkingStatus.area_code==area_code))
    if not row: raise HTTPException(404,"Parking area not found")
    allowed={"AVAILABLE","BUSY","NEAR_CAPACITY","FULL","CLOSED","UNKNOWN"}
    value=payload.occupancy_status.upper()
    if value not in allowed: raise HTTPException(422,"Invalid parking occupancy status")
    row.occupancy_status=value;row.source="staff";row.data_status="STAFF_VERIFIED";row.updated_at=datetime.utcnow();row.expires_at=datetime.utcnow()+timedelta(minutes=payload.expires_minutes)
    db.commit();db.refresh(row);return row
