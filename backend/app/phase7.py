from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from app.database import Base,get_db
from app.security import Role,User,require_roles

class ChannelMessage(Base):
    __tablename__="channel_messages"
    id:Mapped[int]=mapped_column(primary_key=True)
    channel:Mapped[str]=mapped_column(String(30),index=True)
    direction:Mapped[str]=mapped_column(String(20),default="OUTBOUND")
    recipient:Mapped[str]=mapped_column(String(200))
    subject:Mapped[str|None]=mapped_column(String(240),nullable=True)
    body:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(40),default="QUEUED")
    provider:Mapped[str]=mapped_column(String(80),default="NOT_CONFIGURED")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class MessageCreate(BaseModel):
    recipient:str; body:str; subject:str|None=None
class MessageOut(BaseModel):
    id:int; channel:str; direction:str; recipient:str; subject:str|None; body:str; status:str; provider:str; created_at:datetime
    model_config=ConfigDict(from_attributes=True)

def _queue(db,payload,channel):
    row=ChannelMessage(channel=channel,recipient=payload.recipient,subject=payload.subject,body=payload.body,
        status="QUEUED_DEMO",provider="NOT_CONFIGURED")
    db.add(row);db.commit();db.refresh(row);return row
def seed_phase7(db:Session): return

router=APIRouter(prefix="/api/v1",tags=["WhatsApp & Email"])
@router.post("/channels/whatsapp/messages",response_model=MessageOut,status_code=202)
def whatsapp(payload:MessageCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR,Role.CUSTOMER_SERVICE,Role.TENANT_MANAGEMENT))): return _queue(db,payload,"WHATSAPP")
@router.post("/channels/email/messages",response_model=MessageOut,status_code=202)
def email(payload:MessageCreate,db:Session=Depends(get_db),user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR,Role.CUSTOMER_SERVICE,Role.TENANT_MANAGEMENT))): return _queue(db,payload,"EMAIL")
@router.get("/channels/messages",response_model=list[MessageOut])
def messages(db:Session=Depends(get_db),user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR,Role.CUSTOMER_SERVICE,Role.TENANT_MANAGEMENT))): return list(db.scalars(select(ChannelMessage).order_by(ChannelMessage.id.desc())).all())
