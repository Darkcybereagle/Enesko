from datetime import datetime, timedelta
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Category, Facility, Floor, KnowledgeDocument, Mall, Store, Zone


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(Mall).where(Mall.name == "Ikeja City Mall")):
            print("Seed already exists; nothing duplicated.")
            return

        mall = Mall(name="Ikeja City Mall", city="Ikeja, Lagos", country="Nigeria")
        db.add(mall)
        db.flush()

        ground = Floor(mall_id=mall.id, name="Demo Ground Floor", level=0)
        first = Floor(mall_id=mall.id, name="Demo First Floor", level=1)
        db.add_all([ground, first])
        db.flush()

        zone_a = Zone(floor_id=ground.id, code="DEMO-GF-A", name="Demo Ground Zone A")
        zone_b = Zone(floor_id=ground.id, code="DEMO-GF-B", name="Demo Ground Zone B")
        zone_c = Zone(floor_id=first.id, code="DEMO-FF-A", name="Demo First Floor Zone A")
        db.add_all([zone_a, zone_b, zone_c])
        db.flush()

        fashion = Category(name="Fashion")
        sports = Category(name="Sports")
        food = Category(name="Food")
        electronics = Category(name="Electronics")
        db.add_all([fashion, sports, food, electronics])
        db.flush()

        db.add_all([
            Store(
                mall_id=mall.id, floor_id=ground.id, zone_id=zone_a.id,
                name="Demo Sports Store", unit="DEMO-G12",
                description="Development-only sports, shoes and fashion store.",
                nearest_landmark="Demo Entrance 1",
                opening_hours="DEMO — not production information",
                data_status="DEMO", categories=[sports, fashion],
            ),
            Store(
                mall_id=mall.id, floor_id=ground.id, zone_id=zone_b.id,
                name="Demo Food Outlet", unit="DEMO-G30",
                description="Development-only restaurant and food outlet.",
                nearest_landmark="Demo Food Court",
                opening_hours="DEMO — not production information",
                data_status="DEMO", categories=[food],
            ),
            Store(
                mall_id=mall.id, floor_id=first.id, zone_id=zone_c.id,
                name="Demo Electronics Store", unit="DEMO-F08",
                description="Development-only electronics store.",
                nearest_landmark="Demo Escalator",
                opening_hours="DEMO — not production information",
                data_status="DEMO", categories=[electronics],
            ),
        ])

        db.add_all([
            Facility(
                mall_id=mall.id, floor_id=ground.id, zone_id=zone_b.id,
                asset_code="DEMO-ESC-01", name="Demo Escalator",
                facility_type="ESCALATOR", data_status="DEMO",
            ),
            Facility(
                mall_id=mall.id, floor_id=ground.id, zone_id=zone_b.id,
                asset_code="DEMO-WC-01", name="Demo Restroom",
                facility_type="RESTROOM", data_status="DEMO",
            ),
        ])

        now = datetime.utcnow()
        db.add_all([
            KnowledgeDocument(
                title="Enesko Data Accuracy Policy",
                source_type="system_policy",
                source_name="Enesko",
                content=(
                    "Enesko must not invent live operational information. When a current verified source is unavailable "
                    "or expired, the assistant must clearly say it cannot confirm the information and use human escalation "
                    "or an approved integration."
                ),
                verified=True, updated_at=now, expires_at=None,
            ),
            KnowledgeDocument(
                title="Development Data Notice",
                source_type="demo",
                source_name="Enesko development seed",
                content=(
                    "Store, floor, zone and facility records installed by the development seed are demonstration records. "
                    "They must be replaced with authorized verified mall data before production deployment."
                ),
                verified=True, updated_at=now, expires_at=now + timedelta(days=30),
            ),
        ])

        db.commit()
        print("Enesko Phase 1/2 demo seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
