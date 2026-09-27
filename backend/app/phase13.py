from fastapi import APIRouter,Depends
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import Role,User,require_roles
from app.models import Conversation
from app.phase3 import Case
from app.phase5 import TenantRequest
from app.phase6 import Activation
from app.phase7 import ChannelMessage
from app.phase8 import VoiceSession
router=APIRouter(prefix="/api/v1",tags=["Operational Intelligence"])
def seed_phase13(db): return
@router.get("/analytics/operations")
def operations(db:Session=Depends(get_db),user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR))):
    count=lambda model: db.scalar(select(func.count()).select_from(model)) or 0
    open_cases=db.scalar(select(func.count()).select_from(Case).where(~Case.status.in_(["CLOSED","RESOLVED"]))) or 0
    return {"conversations":count(Conversation),"cases_total":count(Case),"cases_open":open_cases,
      "tenant_requests":count(TenantRequest),"activations":count(Activation),"channel_messages":count(ChannelMessage),
      "voice_sessions":count(VoiceSession),"data_status":"OPERATIONAL_DATABASE"}
@router.get("/analytics/case-types")
def case_types(db:Session=Depends(get_db),user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR))):
    rows=db.execute(select(Case.case_type,func.count(Case.id)).group_by(Case.case_type)).all()
    return [{"case_type":name,"count":count} for name,count in rows]
