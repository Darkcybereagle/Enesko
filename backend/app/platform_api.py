from fastapi import APIRouter,Depends
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.audit import AuditLog
from app.database import get_db
from app.phase3 import Case
from app.phase5 import Tenant,TenantRequest
from app.phase6 import Activation
from app.security import Role,User,UserOut,require_roles
router=APIRouter(prefix="/api/v1",tags=["Platform"])
@router.get("/admin/overview")
def admin_overview(user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR,Role.CUSTOMER_SERVICE,Role.TENANT_MANAGEMENT)),db:Session=Depends(get_db)):
    count=lambda model: db.scalar(select(func.count()).select_from(model)) or 0
    return {"viewer":user.full_name,"cases":count(Case),"tenant_requests":count(TenantRequest),"activations":count(Activation),"audit_events":count(AuditLog)}
@router.get("/admin/audit")
def audit_logs(user:User=Depends(require_roles(Role.PLATFORM_SUPER_ADMIN,Role.MALL_ADMINISTRATOR)),db:Session=Depends(get_db)):
    rows=db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(100)).all()
    return [{"id":x.id,"actor_user_id":x.actor_user_id,"actor_role":x.actor_role,"method":x.method,"path":x.path,"status_code":x.status_code,"created_at":x.created_at} for x in rows]
@router.get("/tenant-portal/me")
def tenant_portal(user:User=Depends(require_roles(Role.TENANT_ADMINISTRATOR,Role.TENANT_STAFF)),db:Session=Depends(get_db)):
    tenant=db.get(Tenant,user.tenant_id) if user.tenant_id else None
    return {"user":UserOut.model_validate(user),"tenant_name":tenant.name if tenant else None}
