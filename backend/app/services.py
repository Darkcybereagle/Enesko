import re
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import KnowledgeDocument, Store


STOP_WORDS = {
    "where", "what", "which", "with", "from", "that", "this", "there",
    "about", "could", "would", "please", "mall", "find", "store", "shop",
    "want", "need", "have", "does", "your", "their", "right", "now",
}

SEARCH_SYNONYMS = {
    "shoe": {"footwear", "sneaker", "trainer"},
    "shoes": {"footwear", "sneakers", "trainers"},
    "sneaker": {"shoe", "footwear", "trainer"},
    "sneakers": {"shoes", "footwear", "trainers"},
    "trainer": {"shoe", "footwear", "sneaker"},
    "trainers": {"shoes", "footwear", "sneakers"},
    "phone": {"phones", "smartphone", "mobile"},
    "phones": {"phone", "smartphones", "mobile"},
    "clothes": {"clothing", "apparel", "fashion"},
    "clothing": {"clothes", "apparel", "fashion"},
}


def _tokens(text: str, min_len: int = 3) -> list[str]:
    return [
        token for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) >= min_len and token not in STOP_WORDS
    ]


def search_stores(db: Session, query: str) -> list[Store]:
    now = datetime.utcnow()
    stores = list(
        db.scalars(
            select(Store)
            .options(selectinload(Store.categories))
            .where(
                Store.active.is_(True),
                or_(Store.expires_at.is_(None), Store.expires_at >= now),
            )
            .order_by(Store.name)
        ).unique().all()
    )
    tokens = _tokens(query)

    expanded_terms: dict[str, set[str]] = {
        token: {token, *SEARCH_SYNONYMS.get(token, set())}
        for token in tokens
    }

    def score(store: Store) -> int:
        name = (store.name or "").lower()
        description = (store.description or "").lower()
        landmark = (store.nearest_landmark or "").lower()
        categories = " ".join(category.name for category in store.categories).lower()
        haystack = " ".join([name, description, landmark, categories])

        points = 0
        for token, terms in expanded_terms.items():
            direct_match = token in haystack
            synonym_match = any(term in haystack for term in terms if term != token)

            if token in name:
                points += 4
            elif direct_match:
                points += 2

            if synonym_match:
                points += 2

        return points

    ranked = sorted(
        ((score(store), store) for store in stores),
        key=lambda item: (-item[0], item[1].name),
    )
    return [store for points, store in ranked if points > 0][:5]


def find_knowledge(db: Session, query: str) -> list[KnowledgeDocument]:
    tokens = _tokens(query, min_len=4)
    if not tokens:
        return []

    clauses = []
    for token in tokens[:8]:
        pattern = f"%{token}%"
        clauses.extend([
            KnowledgeDocument.title.ilike(pattern),
            KnowledgeDocument.content.ilike(pattern),
        ])

    docs = list(
        db.scalars(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.verified.is_(True), or_(*clauses))
            .order_by(KnowledgeDocument.updated_at.desc())
            .limit(5)
        ).all()
    )
    now = datetime.utcnow()
    return [doc for doc in docs if doc.expires_at is None or doc.expires_at >= now]


def classify_intent(message: str) -> str:
    text = message.lower()
    if any(term in text for term in ("human", "customer care", "customer service", "speak to someone", "agent")):
        return "human_handoff"
    if any(term in text for term in ("lost", "missing", "misplaced")):
        return "lost_found"
    if any(term in text for term in ("movie", "cinema", "showtime", "film showing", "films showing")):
        return "cinema"
    if any(term in text for term in ("parking", "park my car", "parking space")):
        return "parking"
    if any(term in text for term in ("where is", "where can i", "find", "buy", "store", "shop", "restaurant")):
        return "store_search"
    return "knowledge_query"


def orchestrate(db: Session, message: str) -> dict:
    intent = classify_intent(message)

    if intent == "human_handoff":
        return {
            "answer": "I can create a support case for mall operations so a human team member can follow up.",
            "intent": intent,
            "needs_human": True,
            "sources": [],
            "data": {"workflow": "customer_assistance"},
        }

    if intent == "lost_found":
        return {
            "answer": (
                "I can start a lost-and-found case. Tell me the item, colour or identifying features, "
                "where you last saw it, the approximate time and a contact method. Mall staff must verify "
                "any match before an item can be released."
            ),
            "intent": intent,
            "needs_human": True,
            "sources": [],
            "data": {"workflow": "lost_found_intake"},
        }

    if intent == "cinema":
        return {
            "answer": (
                "Silverbird Cinemas operates at Ikeja City Mall. Published box-office hours are "
                "10:00 AM to 10:00 PM daily. Current showtimes change frequently, so ENESKO will not "
                "invent them until the official cinema feed is connected."
            ),
            "intent": intent,
            "needs_human": False,
            "sources": [],
            "data": {
                "cinema_name": "Silverbird Cinemas, Ikeja City Mall",
                "movie_enquiry": "+234 902 606 7603",
                "official_booking_url": "https://silverbirdcinemas.com/cinema/ikeja/",
                "live_showtimes_connected": False,
            },
        }

    if intent == "parking":
        from app.phase10 import ParkingStatus

        row = db.scalar(select(ParkingStatus).order_by(ParkingStatus.id))
        now = datetime.utcnow()
        fresh_staff_status = (
            row is not None
            and row.data_status == "STAFF_VERIFIED"
            and row.expires_at is not None
            and row.expires_at >= now
        )

        if fresh_staff_status:
            readable = row.occupancy_status.replace("_", " ").title()
            return {
                "answer": (
                    f"The current staff-verified parking status is {readable}. "
                    "Ikeja City Mall also publishes that it has more than 700 parking bays."
                ),
                "intent": intent,
                "needs_human": False,
                "sources": [],
                "data": {
                    "area_code": row.area_code,
                    "status": row.occupancy_status,
                    "verified_until": row.expires_at,
                    "published_capacity": "700+ bays",
                },
            }

        return {
            "answer": (
                "Ikeja City Mall publishes that it has more than 700 parking bays, but ENESKO does not "
                "currently have a fresh verified live occupancy status. I will not guess whether spaces "
                "are available right now."
            ),
            "intent": intent,
            "needs_human": False,
            "sources": [],
            "data": {
                "published_capacity": "700+ bays",
                "live_status": "UNAVAILABLE",
            },
        }

    if intent == "store_search":
        stores = search_stores(db, message)
        if stores:
            first = stores[0]
            answer = f"I found {first.name}"
            if first.nearest_landmark:
                answer += f", near {first.nearest_landmark}"
            answer += "."
            if first.data_status == "PUBLIC_VERIFIED":
                answer += " This listing comes from a currently verified public directory source."
            if first.map_node_code:
                answer += " An ENESKO indoor navigation reference route is available for this location."

            return {
                "answer": answer,
                "intent": intent,
                "needs_human": False,
                "sources": [],
                "data": {
                    "stores": [
                        {
                            "id": store.id,
                            "name": store.name,
                            "unit": store.unit,
                            "floor_id": store.floor_id,
                            "zone_id": store.zone_id,
                            "nearest_landmark": store.nearest_landmark,
                            "opening_hours": store.opening_hours,
                            "categories": [c.name for c in store.categories],
                            "data_status": store.data_status,
                            "source_name": store.source_name,
                            "verified_at": store.verified_at,
                            "expires_at": store.expires_at,
                            "map_node_code": store.map_node_code,
                        }
                        for store in stores
                    ]
                },
            }

    docs = find_knowledge(db, message)
    if docs:
        doc = docs[0]
        excerpt = " ".join(doc.content.split())
        if len(excerpt) > 700:
            excerpt = excerpt[:697] + "..."
        return {
            "answer": excerpt,
            "intent": "knowledge_query",
            "needs_human": False,
            "sources": [
                {
                    "title": item.title,
                    "source_name": item.source_name,
                    "updated_at": item.updated_at,
                    "expires_at": item.expires_at,
                }
                for item in docs
            ],
            "data": None,
        }

    return {
        "answer": (
            "I do not have a current verified source for that information, so I will not guess. "
            "You can ask ENESKO to create a support case or connect an approved data source."
        ),
        "intent": "unknown",
        "needs_human": True,
        "sources": [],
        "data": None,
    }
