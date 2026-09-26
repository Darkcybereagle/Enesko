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


def _tokens(text: str, min_len: int = 3) -> list[str]:
    return [
        token for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) >= min_len and token not in STOP_WORDS
    ]


def search_stores(db: Session, query: str) -> list[Store]:
    stores = list(
        db.scalars(
            select(Store)
            .options(selectinload(Store.categories))
            .where(Store.active.is_(True))
            .order_by(Store.name)
        ).unique().all()
    )
    tokens = _tokens(query)

    def score(store: Store) -> int:
        haystack = " ".join([
            store.name or "",
            store.description or "",
            store.nearest_landmark or "",
            " ".join(category.name for category in store.categories),
        ]).lower()
        return sum(2 if token in (store.name or "").lower() else 1 for token in tokens if token in haystack)

    ranked = sorted(((score(store), store) for store in stores), key=lambda item: (-item[0], item[1].name))
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
    if any(term in text for term in ("parking", "park my car", "parking space")):
        return "parking"
    if any(term in text for term in ("where is", "where can i", "find", "buy", "store", "shop", "restaurant")):
        return "store_search"
    return "knowledge_query"


def orchestrate(db: Session, message: str) -> dict:
    intent = classify_intent(message)

    if intent == "human_handoff":
        return {
            "answer": "This request needs a human support agent. I have marked it for handoff.",
            "intent": intent, "needs_human": True, "sources": [], "data": None,
        }

    if intent == "lost_found":
        return {
            "answer": (
                "I can begin the lost-and-found intake. Please provide the item, colour, last known location, "
                "approximate time, distinguishing features and a contact method. Physical investigation remains with mall staff."
            ),
            "intent": intent, "needs_human": True, "sources": [],
            "data": {"workflow": "lost_found_intake", "phase": "foundation_only"},
        }

    if intent == "parking":
        docs = find_knowledge(db, message)
        if not docs:
            return {
                "answer": (
                    "I cannot confirm live parking availability because no current verified parking source is connected. "
                    "I will not guess. A verified parking feed or staff update is required."
                ),
                "intent": intent, "needs_human": True, "sources": [], "data": None,
            }

    if intent == "store_search":
        stores = search_stores(db, message)
        if stores:
            first = stores[0]
            answer = f"I found {first.name}"
            if first.nearest_landmark:
                answer += f", near {first.nearest_landmark}"
            answer += "."
            if first.data_status != "VERIFIED":
                answer += " This is demo data and must be verified before production use."
            return {
                "answer": answer, "intent": intent, "needs_human": False, "sources": [],
                "data": {"stores": [{
                    "id": store.id, "name": store.name, "unit": store.unit,
                    "floor_id": store.floor_id, "zone_id": store.zone_id,
                    "nearest_landmark": store.nearest_landmark,
                    "categories": [c.name for c in store.categories],
                    "data_status": store.data_status,
                } for store in stores]},
            }

    docs = find_knowledge(db, message)
    if docs:
        doc = docs[0]
        excerpt = " ".join(doc.content.split())
        if len(excerpt) > 700:
            excerpt = excerpt[:697] + "..."
        return {
            "answer": excerpt, "intent": "knowledge_query", "needs_human": False,
            "sources": [{
                "title": item.title, "source_name": item.source_name,
                "updated_at": item.updated_at, "expires_at": item.expires_at,
            } for item in docs],
            "data": None,
        }

    return {
        "answer": (
            "I do not have a current verified source for that information, so I will not guess. "
            "Please use human support or connect an approved data source."
        ),
        "intent": "unknown", "needs_human": True, "sources": [], "data": None,
    }
