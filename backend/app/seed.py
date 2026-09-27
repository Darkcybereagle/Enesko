from datetime import datetime,timedelta
from sqlalchemy import select
from app.database import Base,SessionLocal,engine
from app.models import Category,Facility,Floor,KnowledgeDocument,Mall,Store,Zone
from app.phase3 import seed_phase3
from app.phase4 import seed_phase4
from app.phase5 import seed_phase5
from app.phase6 import seed_phase6
from app.phase7 import seed_phase7
from app.phase8 import seed_phase8
from app.phase9 import seed_phase9
from app.phase10 import seed_phase10
from app.phase11 import seed_phase11
from app.phase12 import seed_phase12
from app.phase13 import seed_phase13
from app.security import seed_security
def seed_core(db):
    mall=db.scalar(select(Mall).where(Mall.name=="Ikeja City Mall"))
    if mall:return
    mall=Mall(name="Ikeja City Mall",city="Ikeja, Lagos",country="Nigeria");db.add(mall);db.flush()
    ground=Floor(mall_id=mall.id,name="Demo Ground Floor",level=0);first=Floor(mall_id=mall.id,name="Demo First Floor",level=1);db.add_all([ground,first]);db.flush()
    a=Zone(floor_id=ground.id,code="DEMO-GF-A",name="Demo Ground Zone A");b=Zone(floor_id=ground.id,code="DEMO-GF-B",name="Demo Ground Zone B");c=Zone(floor_id=first.id,code="DEMO-FF-A",name="Demo First Floor Zone A");db.add_all([a,b,c]);db.flush()
    fashion=Category(name="Fashion");sports=Category(name="Sports");food=Category(name="Food");electronics=Category(name="Electronics");db.add_all([fashion,sports,food,electronics]);db.flush()
    db.add_all([
      Store(mall_id=mall.id,floor_id=ground.id,zone_id=a.id,name="Demo Sports Store",unit="DEMO-G12",description="Development-only sports, shoes and fashion store.",nearest_landmark="Demo Entrance 1",opening_hours="DEMO — not production information",data_status="DEMO",categories=[sports,fashion]),
      Store(mall_id=mall.id,floor_id=ground.id,zone_id=b.id,name="Demo Food Outlet",unit="DEMO-G30",description="Development-only restaurant and food outlet.",nearest_landmark="Demo Food Court",opening_hours="DEMO — not production information",data_status="DEMO",categories=[food]),
      Store(mall_id=mall.id,floor_id=first.id,zone_id=c.id,name="Demo Electronics Store",unit="DEMO-F08",description="Development-only electronics store.",nearest_landmark="Demo Escalator",opening_hours="DEMO — not production information",data_status="DEMO",categories=[electronics]),
      Facility(mall_id=mall.id,floor_id=ground.id,zone_id=b.id,asset_code="DEMO-ESC-01",name="Demo Escalator",facility_type="ESCALATOR",data_status="DEMO"),
      Facility(mall_id=mall.id,floor_id=ground.id,zone_id=b.id,asset_code="DEMO-WC-01",name="Demo Restroom",facility_type="RESTROOM",data_status="DEMO")])
    now=datetime.utcnow();db.add_all([
      KnowledgeDocument(title="Enesko Data Accuracy Policy",source_type="system_policy",source_name="Enesko",content="Enesko must not invent live operational information. When a current verified source is unavailable or expired, the assistant must clearly say it cannot confirm the information and use human escalation or an approved integration.",verified=True,updated_at=now,expires_at=None),
      KnowledgeDocument(title="Development Data Notice",source_type="demo",source_name="Enesko development seed",content="Development seed records are demonstration records and must be replaced with authorized verified mall data before production deployment.",verified=True,updated_at=now,expires_at=now+timedelta(days=30))]);db.commit()
def seed():
    Base.metadata.create_all(bind=engine);db=SessionLocal()
    try:
        seed_core(db)
        for fn in (seed_phase3,seed_phase4,seed_phase5,seed_phase6,seed_phase7,seed_phase8,seed_phase9,seed_phase10,seed_phase11,seed_phase12,seed_phase13,seed_security):fn(db)
        print("Enesko Category 2 seed complete; Category 1 data preserved and security demo user ready.")
    finally:db.close()
if __name__=="__main__":seed()
