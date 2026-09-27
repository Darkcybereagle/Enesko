from datetime import datetime
from fastapi import Request
from sqlalchemy import DateTime,Integer,String,Text
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base,SessionLocal
from app.security import decode_token
class AuditLog(Base):
    __tablename__="audit_logs"
    id:Mapped[int]=mapped_column(primary_key=True)
    actor_user_id:Mapped[int|None]=mapped_column(Integer,nullable=True,index=True)
    actor_role:Mapped[str|None]=mapped_column(String(60),nullable=True)
    method:Mapped[str]=mapped_column(String(10))
    path:Mapped[str]=mapped_column(String(500))
    status_code:Mapped[int]=mapped_column(Integer)
    detail:Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,index=True)
async def audit_mutations(request:Request,call_next):
    response=await call_next(request)
    if request.url.path.startswith("/api/v1") and request.method in {"POST","PUT","PATCH","DELETE"}:
        uid=None;role=None;auth=request.headers.get("authorization","")
        if auth.lower().startswith("bearer "):
            try:
                payload=decode_token(auth.split(" ",1)[1]);uid=int(payload["sub"]);role=payload.get("role")
            except Exception: pass
        db=SessionLocal()
        try: db.add(AuditLog(actor_user_id=uid,actor_role=role,method=request.method,path=request.url.path,status_code=response.status_code));db.commit()
        finally: db.close()
    return response
