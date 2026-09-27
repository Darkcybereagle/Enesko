from datetime import datetime
from fastapi import APIRouter,Depends
from pydantic import BaseModel,ConfigDict
from sqlalchemy import DateTime,String,Text,select
from sqlalchemy.orm import Mapped,Session,mapped_column
from app.database import Base,get_db
class CinemaShow(Base):
    __tablename__="cinema_shows"
    id:Mapped[int]=mapped_column(primary_key=True)
    cinema_name:Mapped[str]=mapped_column(String(200))
    movie_title:Mapped[str]=mapped_column(String(240),index=True)
    show_time:Mapped[str]=mapped_column(String(80))
    booking_reference:Mapped[str|None]=mapped_column(String(400),nullable=True)
    source:Mapped[str]=mapped_column(String(120),default="DEMO")
    data_status:Mapped[str]=mapped_column(String(30),default="DEMO")
    verified_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    expires_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
class CinemaOut(BaseModel):
    id:int;cinema_name:str;movie_title:str;show_time:str;booking_reference:str|None;source:str;data_status:str;verified_at:datetime|None;expires_at:datetime|None
    model_config=ConfigDict(from_attributes=True)
def seed_phase9(db:Session):
    if not db.scalar(select(CinemaShow).where(CinemaShow.movie_title=="Demo Movie")):
        db.add(CinemaShow(cinema_name="Demo Cinema",movie_title="Demo Movie",show_time="DEMO",source="development_seed",data_status="DEMO"));db.commit()
router=APIRouter(prefix="/api/v1",tags=["Cinema"])
@router.get("/cinema/shows",response_model=list[CinemaOut])
def shows(db:Session=Depends(get_db)): return list(db.scalars(select(CinemaShow).order_by(CinemaShow.id)).all())
@router.get("/cinema/integration-status")
def integration_status(): return {"primary":"official_api","secondary":"authorized_sync_import","fallback":"authorized_staff_admin","configured":False,"live_data_available":False}
