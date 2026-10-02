from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import hmac
import json
import re
import unicodedata
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.config import settings
from app.database import Base, get_db
from app.security import Role, User, require_roles


class LearningInteraction(Base):
    __tablename__ = "learning_interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(30), default="web", index=True)
    intent: Mapped[str] = mapped_column(String(120), default="unknown", index=True)
    language: Mapped[str] = mapped_column(String(20), default="en-NG")
    topics: Mapped[str] = mapped_column(String(500), default="")
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class LearningModel(Base):
    __tablename__ = "learning_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    model_kind: Mapped[str] = mapped_column(String(80), default="ANONYMIZED_PATTERN_V1")
    status: Mapped[str] = mapped_column(String(30), default="TESTED", index=True)
    training_event_count: Mapped[int] = mapped_column(Integer, default=0)
    evaluation_score: Mapped[float] = mapped_column(Float, default=0.0)
    pattern_json: Mapped[str] = mapped_column(Text, default="{}")
    active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    approved_by: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LearningModelOut(BaseModel):
    id: int
    version: str
    model_kind: str
    status: str
    training_event_count: int
    evaluation_score: float
    active: bool
    approved_by: str | None
    created_at: datetime
    tested_at: datetime | None
    approved_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


SAFE_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "shoes": ("shoe", "shoes", "sneaker", "sneakers", "trainer", "trainers", "footwear"),
    "food": ("food", "eat", "meal", "restaurant", "dining", "hungry", "shawarma"),
    "water_drinks": ("water", "drink", "drinks", "beverage"),
    "phones_electronics": ("phone", "phones", "smartphone", "electronics", "laptop"),
    "medicine_health": ("medicine", "medicines", "pharmacy", "health"),
    "beauty_fragrance": ("perfume", "fragrance", "makeup", "cosmetics", "beauty"),
    "fashion": ("clothes", "clothing", "fashion", "shirt", "dress"),
    "gifts": ("gift", "gifts"),
    "cinema": ("cinema", "movie", "movies", "film", "showtime"),
    "parking": ("parking", "park", "car"),
    "navigation": ("navigate", "navigation", "direction", "directions", "route"),
    "lost_found": ("lost", "missing", "misplaced", "found"),
    "human_help": ("human", "agent", "customer service", "help"),
}


def _fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _contains_term(text: str, term: str) -> bool:
    folded = _fold_text(term)
    if " " in folded:
        return folded in text
    return re.search(rf"\b{re.escape(folded)}\b", text) is not None


def _safe_topics(message: str, result: dict) -> list[str]:
    folded = _fold_text(message)
    topics = {
        topic
        for topic, terms in SAFE_TOPIC_KEYWORDS.items()
        if any(_contains_term(folded, term) for term in terms)
    }

    intent = str(result.get("intent") or "unknown")
    if intent in {"parking", "cinema", "navigation", "lost_found", "human_handoff"}:
        topics.add("human_help" if intent == "human_handoff" else intent)

    return sorted(topics)


def _session_hash(session_ref: str | None) -> str | None:
    if not session_ref:
        return None
    return hmac.new(
        settings.jwt_secret.encode("utf-8"),
        session_ref.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def record_learning_signal(
    db: Session,
    *,
    session_ref: str | None,
    channel: str,
    message: str,
    result: dict,
) -> LearningInteraction:
    row = LearningInteraction(
        session_hash=_session_hash(session_ref),
        channel=channel.lower(),
        intent=str(result.get("intent") or "unknown"),
        language=str(result.get("language") or "en-NG"),
        topics=",".join(_safe_topics(message, result)),
        needs_human=bool(result.get("needs_human", False)),
    )
    db.add(row)
    return row


def _topic_list(row: LearningInteraction) -> list[str]:
    return [item for item in row.topics.split(",") if item]


def _evaluate_transition_model(
    sessions: dict[str, list[LearningInteraction]],
) -> float:
    eligible = [rows for rows in sessions.values() if len(rows) >= 2]
    if len(eligible) < 2:
        return 0.0

    split = max(1, int(len(eligible) * 0.8))
    train_sessions = eligible[:split]
    test_sessions = eligible[split:]
    if not test_sessions:
        test_sessions = eligible[-1:]
        train_sessions = eligible[:-1]

    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    for rows in train_sessions:
        for previous, current in zip(rows, rows[1:]):
            for source in _topic_list(previous):
                for target in _topic_list(current):
                    transitions[source][target] += 1

    attempts = 0
    hits = 0
    for rows in test_sessions:
        for previous, current in zip(rows, rows[1:]):
            actual = set(_topic_list(current))
            for source in _topic_list(previous):
                if not transitions.get(source):
                    continue
                attempts += 1
                predicted = transitions[source].most_common(1)[0][0]
                if predicted in actual:
                    hits += 1

    return round(hits / attempts, 4) if attempts else 0.0


def train_pattern_model(db: Session) -> LearningModel:
    interactions = list(
        db.scalars(
            select(LearningInteraction).order_by(
                LearningInteraction.created_at,
                LearningInteraction.id,
            )
        ).all()
    )
    if len(interactions) < 10:
        raise HTTPException(
            status_code=422,
            detail="At least 10 anonymized interaction signals are required before training.",
        )

    topic_counts: Counter[str] = Counter()
    cooccurrence: Counter[str] = Counter()
    sessions: dict[str, list[LearningInteraction]] = defaultdict(list)

    for row in interactions:
        topics = _topic_list(row)
        topic_counts.update(topics)
        for index, left in enumerate(topics):
            for right in topics[index + 1:]:
                cooccurrence["|".join(sorted((left, right)))] += 1
        if row.session_hash:
            sessions[row.session_hash].append(row)

    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    for rows in sessions.values():
        for previous, current in zip(rows, rows[1:]):
            for source in _topic_list(previous):
                for target in _topic_list(current):
                    transitions[source][target] += 1

    patterns = {
        "topic_counts": dict(topic_counts),
        "cooccurrence": dict(cooccurrence),
        "next_topic": {
            source: [
                {"topic": target, "count": count}
                for target, count in counts.most_common(5)
            ]
            for source, counts in transitions.items()
        },
        "privacy": {
            "raw_text_stored": False,
            "direct_identity_stored": False,
            "session_identifier": "hmac-sha256",
            "topic_vocabulary": "allowlisted",
        },
    }

    score = _evaluate_transition_model(sessions)
    row = LearningModel(
        version=f"PATTERN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}",
        model_kind="ANONYMIZED_PATTERN_V1",
        status="TESTED",
        training_event_count=len(interactions),
        evaluation_score=score,
        pattern_json=json.dumps(patterns, sort_keys=True),
        active=False,
        tested_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def approved_prediction(db: Session, message: str, result: dict) -> str | None:
    model = db.scalar(
        select(LearningModel)
        .where(LearningModel.active.is_(True), LearningModel.status == "APPROVED")
        .order_by(LearningModel.approved_at.desc())
    )
    if not model:
        return None

    try:
        patterns = json.loads(model.pattern_json or "{}")
    except json.JSONDecodeError:
        return None

    topics = _safe_topics(message, result)
    candidates: Counter[str] = Counter()
    for source in topics:
        for item in patterns.get("next_topic", {}).get(source, []):
            target = str(item.get("topic") or "")
            count = int(item.get("count") or 0)
            if target and target not in topics:
                candidates[target] += count

    if not candidates:
        return None

    topic, support = candidates.most_common(1)[0]
    if support < 2:
        return None
    return topic


def seed_learning(db: Session) -> None:
    # Learning begins from real interaction signals; no synthetic production
    # interactions or pre-approved model are seeded.
    return None


router = APIRouter(prefix="/api/v1/learning", tags=["Learning"])


@router.get("/status")
def learning_status(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(Role.PLATFORM_SUPER_ADMIN, Role.MALL_ADMINISTRATOR)
    ),
):
    events = list(db.scalars(select(LearningInteraction)).all())
    models = list(
        db.scalars(select(LearningModel).order_by(LearningModel.created_at.desc())).all()
    )
    active = next((row for row in models if row.active and row.status == "APPROVED"), None)
    return {
        "pipeline": [
            "ANONYMIZED_INTERACTIONS",
            "PATTERN_ANALYSIS",
            "MODEL_TRAINING",
            "TESTING",
            "HUMAN_APPROVAL",
            "ACTIVE_ENESKO_MODEL",
        ],
        "learning_dataset_raw_customer_text_stored": False,
        "interaction_signals": len(events),
        "models": len(models),
        "active_model": active.version if active else None,
        "minimum_training_signals": 10,
        "approval_rule": "TESTED candidate, >=10 signals and evaluation score >=0.50",
    }


@router.get("/models", response_model=list[LearningModelOut])
def list_models(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(Role.PLATFORM_SUPER_ADMIN, Role.MALL_ADMINISTRATOR)
    ),
):
    return list(
        db.scalars(select(LearningModel).order_by(LearningModel.created_at.desc())).all()
    )


@router.post("/train", response_model=LearningModelOut, status_code=201)
def train(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(Role.PLATFORM_SUPER_ADMIN, Role.MALL_ADMINISTRATOR)
    ),
):
    return train_pattern_model(db)


@router.post("/models/{model_id}/approve", response_model=LearningModelOut)
def approve(
    model_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(Role.PLATFORM_SUPER_ADMIN, Role.MALL_ADMINISTRATOR)
    ),
):
    candidate = db.get(LearningModel, model_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Learning model not found")
    if candidate.status != "TESTED":
        raise HTTPException(status_code=409, detail="Only tested candidates can be approved")
    if candidate.training_event_count < 10 or candidate.evaluation_score < 0.50:
        raise HTTPException(
            status_code=422,
            detail="Candidate has not met the minimum evidence and evaluation gate.",
        )

    for row in db.scalars(select(LearningModel).where(LearningModel.active.is_(True))).all():
        row.active = False
        if row.status == "APPROVED":
            row.status = "RETIRED"

    candidate.status = "APPROVED"
    candidate.active = True
    candidate.approved_by = user.email
    candidate.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(candidate)
    return candidate
