from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Category, Facility, Floor, KnowledgeDocument, Mall, Store, Zone
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


PUBLIC_VERIFIED_AT = datetime(2026, 9, 29)
PUBLIC_EXPIRES_AT = PUBLIC_VERIFIED_AT + timedelta(days=90)


def _category(db, name: str) -> Category:
    row = db.scalar(select(Category).where(Category.name == name))
    if not row:
        row = Category(name=name)
        db.add(row)
        db.flush()
    return row


def _knowledge(
    db,
    *,
    title: str,
    source_name: str,
    content: str,
) -> None:
    row = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.title == title))
    if not row:
        row = KnowledgeDocument(
            title=title,
            source_type="official_public_source",
            source_name=source_name,
            content=content,
            verified=True,
            updated_at=PUBLIC_VERIFIED_AT,
            expires_at=PUBLIC_EXPIRES_AT,
        )
        db.add(row)
        return

    row.source_type = "official_public_source"
    row.source_name = source_name
    row.content = content
    row.verified = True
    row.updated_at = PUBLIC_VERIFIED_AT
    row.expires_at = PUBLIC_EXPIRES_AT


def _upsert_public_store(db, mall: Mall, payload: dict) -> None:
    categories = [_category(db, name) for name in payload.pop("category_names")]
    row = db.scalar(select(Store).where(Store.name == payload["name"]))

    if not row:
        row = Store(
            mall_id=mall.id,
            floor_id=None,
            zone_id=None,
            **payload,
        )
        db.add(row)
        db.flush()
    else:
        row.mall_id = mall.id
        row.floor_id = None
        row.zone_id = None
        for key, value in payload.items():
            setattr(row, key, value)

    row.categories = categories


def seed_core(db):
    mall = db.scalar(select(Mall).where(Mall.name == "Ikeja City Mall"))
    if not mall:
        mall = Mall(name="Ikeja City Mall", city="Ikeja, Lagos", country="Nigeria")
        db.add(mall)
        db.flush()

    ground = db.scalar(select(Floor).where(Floor.mall_id == mall.id, Floor.level == 0))
    if not ground:
        ground = Floor(mall_id=mall.id, name="Ground Floor", level=0)
        db.add(ground)
        db.flush()
    else:
        ground.name = "Ground Floor"

    top = db.scalar(select(Floor).where(Floor.mall_id == mall.id, Floor.level == 1))
    if not top:
        top = Floor(mall_id=mall.id, name="Top Floor", level=1)
        db.add(top)
        db.flush()
    else:
        top.name = "Top Floor"

    legacy_zones = list(
        db.scalars(
            select(Zone).where(
                Zone.code.in_(["DEMO-GF-A", "DEMO-GF-B", "DEMO-FF-A"])
            )
        ).all()
    )
    zone_targets = [
        ("ICM-GF-A", "Ground Floor Reference Zone A"),
        ("ICM-GF-B", "Ground Floor Reference Zone B"),
        ("ICM-TF-A", "Top Floor Reference Zone A"),
    ]
    for zone, (code, name) in zip(legacy_zones, zone_targets):
        zone.code = code
        zone.name = name

    for store in list(db.scalars(select(Store)).all()):
        if store.data_status == "DEMO" or store.name.startswith("Demo "):
            db.delete(store)

    for facility in list(db.scalars(select(Facility)).all()):
        if facility.data_status == "DEMO" or facility.name.startswith("Demo "):
            db.delete(facility)

    for doc in list(db.scalars(select(KnowledgeDocument)).all()):
        if doc.title == "Development Data Notice" or doc.source_type == "demo":
            db.delete(doc)

    public_stores = [
        {
            "name": "Adidas",
            "unit": None,
            "description": "Sportswear, footwear and accessories retailer listed in the official Ikeja City Mall directory.",
            "nearest_landmark": None,
            "opening_hours": None,
            "data_status": "PUBLIC_VERIFIED",
            "source_name": "Ikeja City Mall official directory",
            "source_url": "https://newsites.ikejacitymall.com.ng/store/adidas/",
            "verified_at": PUBLIC_VERIFIED_AT,
            "expires_at": PUBLIC_EXPIRES_AT,
            "map_node_code": None,
            "active": True,
            "category_names": ["Sports", "Fashion"],
        },
        {
            "name": "Nike Store Ikeja City Mall",
            "unit": None,
            "description": "Partnered Nike store at Ikeja City Mall offering Nike footwear, clothing and sportswear.",
            "nearest_landmark": None,
            "opening_hours": "Mon-Sat 10:00-20:00; Sun 12:00-20:00",
            "data_status": "PUBLIC_VERIFIED",
            "source_name": "Nike official store directory",
            "source_url": "https://www.nike.com/retail/s/nike-store-ikeja-city-mall",
            "verified_at": PUBLIC_VERIFIED_AT,
            "expires_at": PUBLIC_EXPIRES_AT,
            "map_node_code": None,
            "active": True,
            "category_names": ["Sports", "Fashion"],
        },
        {
            "name": "Sports World",
            "unit": None,
            "description": "Sports equipment, gym equipment, exercise accessories and apparel retailer listed by Ikeja City Mall.",
            "nearest_landmark": None,
            "opening_hours": None,
            "data_status": "PUBLIC_VERIFIED",
            "source_name": "Ikeja City Mall official directory",
            "source_url": "https://newsites.ikejacitymall.com.ng/store/sports-world/",
            "verified_at": PUBLIC_VERIFIED_AT,
            "expires_at": PUBLIC_EXPIRES_AT,
            "map_node_code": None,
            "active": True,
            "category_names": ["Sports"],
        },
        {
            "name": "Samsung Experience Store",
            "unit": None,
            "description": "Samsung Experience Store at Ikeja City Mall for Samsung products and services.",
            "nearest_landmark": "Entrance 2",
            "opening_hours": None,
            "data_status": "PUBLIC_VERIFIED",
            "source_name": "Samsung Experience Stores Nigeria",
            "source_url": "https://sesnigeria.com/store-locator/",
            "verified_at": PUBLIC_VERIFIED_AT,
            "expires_at": PUBLIC_EXPIRES_AT,
            "map_node_code": "ICM-SAMSUNG",
            "active": True,
            "category_names": ["Electronics"],
        },
        {
            "name": "Pointek",
            "unit": None,
            "description": "Phones, computers, televisions, appliances and consumer electronics retailer listed by Ikeja City Mall.",
            "nearest_landmark": None,
            "opening_hours": None,
            "data_status": "PUBLIC_VERIFIED",
            "source_name": "Ikeja City Mall official directory",
            "source_url": "https://newsites.ikejacitymall.com.ng/store/pointek/",
            "verified_at": PUBLIC_VERIFIED_AT,
            "expires_at": PUBLIC_EXPIRES_AT,
            "map_node_code": None,
            "active": True,
            "category_names": ["Electronics"],
        },
    ]

    for payload in public_stores:
        _upsert_public_store(db, mall, payload.copy())

    _knowledge(
        db,
        title="Enesko Data Accuracy Policy",
        source_name="Enesko",
        content=(
            "ENESKO must not invent live operational information. Current operational claims must come from "
            "fresh staff-verified records or approved integrations. Public directory facts must retain source "
            "and verification metadata, while unavailable live data must be described as unavailable."
        ),
    )
    _knowledge(
        db,
        title="Ikeja City Mall Public Overview",
        source_name="Ikeja City Mall official website",
        content=(
            "Ikeja City Mall is located in Alausa, Ikeja, Lagos. The official mall website states that the "
            "shopping centre has over 100 shops, 12 restaurants and more than 700 parking bays."
        ),
    )
    _knowledge(
        db,
        title="Ikeja City Mall Parking Information",
        source_name="Ikeja City Mall official website",
        content=(
            "Ikeja City Mall publicly states that it provides more than 700 parking bays. This is capacity "
            "information, not live availability. Live occupancy must come from a fresh ENESKO staff update "
            "or an authorized parking integration."
        ),
    )
    _knowledge(
        db,
        title="Ikeja City Mall Lost and Found",
        source_name="Ikeja City Mall official website",
        content=(
            "Ikeja City Mall publishes a Lost and Found contact through the mall management line "
            "+234 806 858 2039. ENESKO can create and track a lost-and-found case, while physical verification "
            "and item release remain with authorized mall staff."
        ),
    )
    _knowledge(
        db,
        title="Silverbird Cinemas Ikeja City Mall",
        source_name="Silverbird Cinemas official website",
        content=(
            "Silverbird Cinemas operates at Ikeja City Mall. Its published box-office hours are Monday to "
            "Sunday, 10:00 to 22:00, and its movie enquiry line is +234 902 606 7603. Current showtimes are "
            "subject to change and should come from the official cinema service."
        ),
    )

    db.commit()


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_core(db)
        for fn in (
            seed_phase3,
            seed_phase4,
            seed_phase5,
            seed_phase6,
            seed_phase7,
            seed_phase8,
            seed_phase9,
            seed_phase10,
            seed_phase11,
            seed_phase12,
            seed_phase13,
            seed_security,
        ):
            fn(db)
        print(
            "Enesko product seed complete; public customer reference data, operational foundations and security seed are ready."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
