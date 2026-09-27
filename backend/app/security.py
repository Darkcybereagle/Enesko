from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, DateTime, ForeignKey, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from app.config import settings
from app.database import Base, get_db

class Role(StrEnum):
    PLATFORM_SUPER_ADMIN="PLATFORM_SUPER_ADMIN"
    MALL_ADMINISTRATOR="MALL_ADMINISTRATOR"
    CUSTOMER_SERVICE="CUSTOMER_SERVICE"
    PARKING="PARKING"
    FACILITIES="FACILITIES"
    MARKETING="MARKETING"
    TENANT_MANAGEMENT="TENANT_MANAGEMENT"
    SECURITY="SECURITY"
    TENANT_ADMINISTRATOR="TENANT_ADMINISTRATOR"
    TENANT_STAFF="TENANT_STAFF"

class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(240),unique=True,index=True)
    full_name:Mapped[str]=mapped_column(String(200))
    password_hash:Mapped[str]=mapped_column(String(500))
    role:Mapped[str]=mapped_column(String(60),index=True)
    tenant_id:Mapped[int|None]=mapped_column(ForeignKey("tenants.id",ondelete="SET NULL"),nullable=True,index=True)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class UserOut(BaseModel):
    id:int;email:str;full_name:str;role:str;tenant_id:int|None;active:bool
    model_config=ConfigDict(from_attributes=True)

_hasher=PasswordHasher()
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
def hash_password(password:str)->str: return _hasher.hash(password)
def verify_password(password:str,password_hash:str)->bool:
    try: return _hasher.verify(password_hash,password)
    except VerifyMismatchError: return False
def create_access_token(user:User)->str:
    now=datetime.now(timezone.utc)
    return jwt.encode({"sub":str(user.id),"role":user.role,"iat":now,"exp":now+timedelta(minutes=settings.access_token_expire_minutes)},settings.jwt_secret,algorithm=settings.jwt_algorithm)
def decode_token(token:str)->dict:
    try: return jwt.decode(token,settings.jwt_secret,algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError: raise HTTPException(status_code=401,detail="Invalid or expired access token")
def get_current_user(token:Annotated[str,Depends(oauth2_scheme)],db:Session=Depends(get_db))->User:
    payload=decode_token(token);user=db.get(User,int(payload["sub"]))
    if not user or not user.active: raise HTTPException(status_code=401,detail="Inactive or missing user")
    return user
def require_roles(*roles:Role):
    allowed={r.value for r in roles}
    def dependency(user:User=Depends(get_current_user))->User:
        if user.role not in allowed: raise HTTPException(status_code=403,detail="Insufficient role permission")
        return user
    return dependency
def seed_security(db:Session):
    if not db.scalar(select(User).where(User.email=="admin@enesko.local")):
        db.add(User(email="admin@enesko.local",full_name="ENESKO Demo Administrator",password_hash=hash_password(settings.demo_admin_password),role=Role.PLATFORM_SUPER_ADMIN.value));db.commit()
    from app.phase5 import Tenant
    tenant=db.scalar(select(Tenant).where(Tenant.name=="Demo Sports Tenant"))
    if tenant and not db.scalar(select(User).where(User.email=="tenant@enesko.local")):
        db.add(User(email="tenant@enesko.local",full_name="Demo Tenant Administrator",password_hash=hash_password(settings.demo_tenant_password),role=Role.TENANT_ADMINISTRATOR.value,tenant_id=tenant.id));db.commit()
