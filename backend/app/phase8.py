from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict
from sqlalchemy import DateTime,String,Text,select
from sqlalchemy.orm import Mapped,Session,mapped_column
from app.database import Base,get_db

class VoiceSession(Base):
    __tablename__="voice_sessions"
    id:Mapped[int]=mapped_column(primary_key=True)
    session_ref:Mapped[str]=mapped_column(String(40),unique=True,index=True)
    direction:Mapped[str]=mapped_column(String(20),default="INBOUND")
    caller:Mapped[str|None]=mapped_column(String(120),nullable=True)
    status:Mapped[str]=mapped_column(String(40),default="ACTIVE")
    provider:Mapped[str]=mapped_column(String(80),default="NOT_CONFIGURED")
    transcript:Mapped[str|None]=mapped_column(Text,nullable=True)
    summary:Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class VoiceStart(BaseModel): direction:str="INBOUND"; caller:str|None=None
class VoiceClose(BaseModel): transcript:str; summary:str
class VoiceOut(BaseModel):
    id:int;session_ref:str;direction:str;caller:str|None;status:str;provider:str;transcript:str|None;summary:str|None;created_at:datetime
    model_config=ConfigDict(from_attributes=True)
def seed_phase8(db:Session): return
router=APIRouter(prefix="/api/v1",tags=["Voice"])
@router.post("/voice/sessions",response_model=VoiceOut,status_code=201)
def start(payload:VoiceStart,db:Session=Depends(get_db)):
    row=VoiceSession(session_ref=f"VOICE-{uuid4().hex[:10].upper()}",direction=payload.direction.upper(),caller=payload.caller)
    db.add(row);db.commit();db.refresh(row);return row
@router.patch("/voice/sessions/{ref}/complete",response_model=VoiceOut)
def complete(ref:str,payload:VoiceClose,db:Session=Depends(get_db)):
    row=db.scalar(select(VoiceSession).where(VoiceSession.session_ref==ref))
    if not row: raise HTTPException(404,"Voice session not found")
    row.transcript=payload.transcript;row.summary=payload.summary;row.status="COMPLETED";db.commit();db.refresh(row);return row
