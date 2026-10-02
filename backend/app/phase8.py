from datetime import datetime
import json
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base, get_db
from app.learning import approved_prediction, record_learning_signal
from app.models import Conversation
from app.phase3 import CaseCreate, create_case_record
from app.services import classify_intent, orchestrate


class VoiceSession(Base):
    __tablename__ = "voice_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_ref: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    direction: Mapped[str] = mapped_column(String(20), default="INBOUND")
    caller: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE")
    provider: Mapped[str] = mapped_column(String(80), default="BROWSER_SPEECH")
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VoiceStart(BaseModel):
    direction: str = "INBOUND"
    caller: str | None = None
    provider: str = "BROWSER_SPEECH"


class VoiceTurn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class VoiceClose(BaseModel):
    transcript: str | None = None
    summary: str | None = None


class VoiceOut(BaseModel):
    id: int
    session_ref: str
    direction: str
    caller: str | None
    status: str
    provider: str
    transcript: str | None
    summary: str | None
    last_activity_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class VoiceTurnOut(BaseModel):
    session: VoiceOut
    answer: str
    intent: str
    language: str = "en-NG"
    needs_human: bool
    sources: list[dict] = Field(default_factory=list)
    data: dict | None = None
    memory: dict | None = None
    learning_suggestion: str | None = None


def seed_phase8(db: Session):
    for row in db.scalars(select(VoiceSession).where(VoiceSession.provider == "NOT_CONFIGURED")).all():
        row.provider = "BROWSER_SPEECH"
    db.commit()


router = APIRouter(prefix="/api/v1", tags=["Voice"])


def _session_or_404(db: Session, ref: str) -> VoiceSession:
    row = db.scalar(select(VoiceSession).where(VoiceSession.session_ref == ref))
    if not row:
        raise HTTPException(status_code=404, detail="Voice session not found")
    return row


def _load_memory(row: VoiceSession) -> dict:
    if not row.memory_json:
        return {}
    try:
        value = json.loads(row.memory_json)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _save_memory(row: VoiceSession, memory: dict) -> None:
    row.memory_json = json.dumps(memory, ensure_ascii=False, default=str)
    row.last_activity_at = datetime.utcnow()


def _public_memory(memory: dict) -> dict:
    output: dict = {
        "last_intent": memory.get("last_intent"),
        "active_workflow": None,
        "shopping_plan_active": bool(memory.get("shopping_plan")),
    }
    workflow = memory.get("workflow")
    if isinstance(workflow, dict):
        output["active_workflow"] = {
            "type": workflow.get("type"),
            "stage": workflow.get("stage"),
            "case_reference": workflow.get("case_reference"),
        }
    return output


def _base_result(
    answer: str,
    *,
    intent: str,
    data: dict | None = None,
    needs_human: bool = False,
    language: str = "en-NG",
) -> dict:
    return {
        "answer": answer,
        "intent": intent,
        "language": language,
        "needs_human": needs_human,
        "sources": [],
        "data": data,
    }


def _extract_initial_lost_item(text: str) -> str | None:
    match = re.search(
        r"\b(?:lost|misplaced)\s+(?:my|a|an|the)?\s*(.+?)(?:\s+(?:at|around|near)\s+|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    item = " ".join(match.group(1).strip(" .?!").split())
    if item.lower() in {"something", "item", "something of mine"}:
        return None
    return item[:500] or None


def _extract_initial_location(text: str) -> str | None:
    match = re.search(
        r"\b(?:at|around|near)\s+(.+?)(?:\s+(?:at about|around about)\s+|$)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return " ".join(match.group(1).strip(" .?!").split())[:240] or None


def _lost_summary(data: dict) -> str:
    return (
        f"{data.get('item_description') or 'item not stated'}; "
        f"description: {data.get('distinguishing_features') or 'not stated'}; "
        f"last seen: {data.get('last_seen_location') or 'not stated'}; "
        f"time: {data.get('last_seen_time') or 'not stated'}; "
        f"contact: {data.get('contact') or 'not stated'}"
    )


def _lost_prompt(workflow: dict) -> str:
    stage = workflow.get("stage", "item")
    data = workflow.get("data") or {}
    prompts = {
        "item": "What did you lose? Describe the item in your own words.",
        "features": (
            f"I have the item as {data.get('item_description')}. "
            "Please describe its colour, brand, size, marks, contents or any other distinguishing features."
        ),
        "location": "Where do you remember seeing it last?",
        "time": "About what time did you last see it? An approximate time is fine.",
        "contact": "What phone number or email should mall staff use if they find a possible match?",
        "confirm": (
            f"I have this report: {_lost_summary(data)}. "
            "Should I submit it to Ikeja City Mall Lost & Found now?"
        ),
        "correction": (
            "Tell me the correction using one of these labels: item:, description:, location:, time:, or contact:."
        ),
    }
    return prompts.get(stage, "Tell me what you want to add to the Lost & Found report.")


def _lost_found_turn(
    db: Session,
    row: VoiceSession,
    text: str,
    memory: dict,
) -> tuple[dict, dict] | None:
    workflow = memory.get("workflow")
    active = isinstance(workflow, dict) and workflow.get("type") == "lost_found" and workflow.get("stage") != "submitted"
    detected = classify_intent(text)

    if not active and detected != "lost_found":
        return None

    if not active:
        item = _extract_initial_lost_item(text)
        location = _extract_initial_location(text)
        data = {
            "item_description": item,
            "distinguishing_features": None,
            "last_seen_location": location,
            "last_seen_time": None,
            "contact": None,
        }
        if not item:
            stage = "item"
        elif not location:
            stage = "features"
        else:
            stage = "features"
        workflow = {"type": "lost_found", "stage": stage, "data": data}
        memory["workflow"] = workflow
        return _base_result(_lost_prompt(workflow), intent="lost_found"), memory

    assert isinstance(workflow, dict)
    data = workflow.setdefault("data", {})
    normalized = " ".join(text.lower().strip().split())

    if normalized in {
        "back to my lost item",
        "back to the lost item",
        "continue the lost report",
        "continue my lost report",
        "continue",
    }:
        return _base_result(_lost_prompt(workflow), intent="lost_found"), memory

    if detected in {"navigation", "store_search", "shopping_plan", "parking", "cinema", "human_handoff"}:
        interruption = orchestrate(db, text)
        interruption["answer"] = (
            interruption["answer"]
            + " Your Lost & Found report is still open. "
            + _lost_prompt(workflow)
        )
        return interruption, memory

    stage = workflow.get("stage", "item")

    if stage == "item":
        data["item_description"] = text.strip()[:500]
        workflow["stage"] = "features"
    elif stage == "features":
        data["distinguishing_features"] = text.strip()[:2000]
        workflow["stage"] = "time" if data.get("last_seen_location") else "location"
    elif stage == "location":
        data["last_seen_location"] = text.strip()[:240]
        workflow["stage"] = "time"
    elif stage == "time":
        data["last_seen_time"] = text.strip()[:120]
        workflow["stage"] = "contact"
    elif stage == "contact":
        data["contact"] = text.strip()[:200]
        workflow["stage"] = "confirm"
    elif stage == "confirm":
        affirmative = normalized in {"yes", "yes please", "yeah", "correct", "submit", "submit it", "ok", "okay"}
        negative = normalized in {"no", "nope", "not correct", "change it", "change"}
        if affirmative:
            case = create_case_record(
                db,
                CaseCreate(
                    case_type="LOST_FOUND",
                    summary=f"Lost item: {data.get('item_description') or 'Unspecified item'}",
                    description=(
                        "Voice-assisted Lost & Found report. "
                        f"Last-seen time: {data.get('last_seen_time') or 'not stated'}."
                    ),
                    contact=data.get("contact"),
                    item_description=data.get("item_description"),
                    last_seen_location=data.get("last_seen_location"),
                    last_seen_time=data.get("last_seen_time"),
                    distinguishing_features=data.get("distinguishing_features"),
                    channel="voice",
                    priority="NORMAL",
                ),
            )
            workflow["stage"] = "submitted"
            workflow["case_reference"] = case.reference
            return _base_result(
                (
                    f"Your Lost & Found report has been submitted as {case.reference}. "
                    "Mall staff will verify any possible match before an item is released."
                ),
                intent="lost_found",
                needs_human=True,
                data={"case_reference": case.reference},
            ), memory
        if negative:
            workflow["stage"] = "correction"
            return _base_result(_lost_prompt(workflow), intent="lost_found"), memory
        return _base_result(
            "Please say yes to submit, or no if you want to correct something first.",
            intent="lost_found",
        ), memory
    elif stage == "correction":
        match = re.match(r"\s*(item|description|location|time|contact)\s*:\s*(.+)", text, flags=re.IGNORECASE)
        if not match:
            return _base_result(_lost_prompt(workflow), intent="lost_found"), memory
        field, value = match.group(1).lower(), match.group(2).strip()
        target = {
            "item": "item_description",
            "description": "distinguishing_features",
            "location": "last_seen_location",
            "time": "last_seen_time",
            "contact": "contact",
        }[field]
        data[target] = value
        workflow["stage"] = "confirm"

    return _base_result(_lost_prompt(workflow), intent="lost_found"), memory


def _shopping_memory_turn(db: Session, text: str, memory: dict) -> tuple[dict, dict] | None:
    plan = memory.get("shopping_plan")
    if not isinstance(plan, dict):
        return None
    items = list(plan.get("needs") or [])
    if not items:
        return None

    lowered = " ".join(text.lower().strip().split())

    if lowered.startswith("remove ") or lowered.startswith("skip "):
        target = lowered.split(" ", 1)[1].strip()
        alias_groups = {
            "food": {"food", "eat", "meal", "restaurant", "dining"},
            "eat": {"food", "eat", "meal", "restaurant", "dining"},
            "shoe": {"shoe", "shoes", "sneaker", "sneakers", "footwear"},
            "shoes": {"shoe", "shoes", "sneaker", "sneakers", "footwear"},
            "water": {"water", "drink", "drinks", "beverage"},
            "drink": {"water", "drink", "drinks", "beverage"},
        }
        aliases = alias_groups.get(target, {target})
        remaining = [
            item for item in items
            if not any(alias in str(item.get("need") or "").lower() for alias in aliases)
        ]
        if len(remaining) == len(items):
            return _base_result(
                f"I still have your shopping plan, but I could not match '{target}' to one of its current needs.",
                intent="shopping_plan",
                data={"shopping_plan": plan},
            ), memory
        for index, item in enumerate(remaining, start=1):
            item["suggested_order"] = index
        plan["needs"] = remaining
        memory["shopping_plan"] = plan
        names = ", ".join(str(item.get("need")) for item in remaining) or "no remaining stops"
        return _base_result(
            f"Done. I removed {target}. Your current plan is {names}.",
            intent="shopping_plan",
            data={"shopping_plan": plan},
        ), memory

    if any(phrase in lowered for phrase in ("what next", "which one first", "first stop", "which is nearest", "nearest one")):
        ordered = sorted(items, key=lambda item: int(item.get("suggested_order") or 999))
        next_item = ordered[0]
        store = next_item.get("recommended_store") or {}
        return _base_result(
            (
                f"Your next planned stop is {store.get('name') or 'the first recommended store'} "
                f"for {next_item.get('need')}."
            ),
            intent="shopping_plan",
            data={"shopping_plan": plan},
        ), memory

    if any(phrase in lowered for phrase in ("take me there", "guide me there", "navigate there")):
        ordered = sorted(items, key=lambda item: int(item.get("suggested_order") or 999))
        next_item = ordered[0]
        store = next_item.get("recommended_store") or {}
        node = store.get("map_node_code")
        if not node:
            return _base_result(
                (
                    f"The next stop is {store.get('name') or 'your recommended store'}, "
                    "but it does not yet have an approved ENESKO indoor-map node, so I will not invent a route."
                ),
                intent="navigation",
                data={"shopping_plan": plan},
            ), memory
        from app.phase4 import calculate_route

        route = calculate_route(db, "ICM-ENTRANCE-2", node, accessible_only=True)
        steps = " ".join(step["instruction"] for step in route["steps"])
        return _base_result(
            (
                f"I remember the plan. I can guide you to {store.get('name')}. "
                f"Starting from Entrance 2: {steps}"
            ),
            intent="navigation",
            data={"store": store, "route": route, "shopping_plan": plan},
        ), memory

    return None


@router.post("/voice/sessions", response_model=VoiceOut, status_code=201)
def start(payload: VoiceStart, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    row = VoiceSession(
        session_ref=f"VOICE-{uuid4().hex[:10].upper()}",
        direction=payload.direction.upper(),
        caller=payload.caller,
        provider=payload.provider.upper(),
        memory_json="{}",
        last_activity_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/voice/sessions/{ref}/turn", response_model=VoiceTurnOut)
def voice_turn(ref: str, payload: VoiceTurn, db: Session = Depends(get_db)):
    row = _session_or_404(db, ref)
    if row.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Voice session is not active")

    memory = _load_memory(row)

    handled = _lost_found_turn(db, row, payload.text, memory)
    if handled is None:
        handled = _shopping_memory_turn(db, payload.text, memory)

    if handled is not None:
        result, memory = handled
    else:
        result = orchestrate(db, payload.text)

    if result.get("intent") == "shopping_plan":
        plan = (result.get("data") or {}).get("shopping_plan")
        if isinstance(plan, dict):
            memory["shopping_plan"] = plan

    memory["last_intent"] = result.get("intent")
    memory["last_data"] = result.get("data")

    suggestion = approved_prediction(db, payload.text, result)
    if suggestion and result.get("intent") in {"store_search", "shopping_plan", "navigation"}:
        result["answer"] = (
            result["answer"]
            + f" Based on an approved anonymized ENESKO usage pattern, {suggestion.replace('_', ' ')} "
            "is often the next related request. Would you like help with that?"
        )

    line = f"USER: {payload.text}\nENESKO: {result['answer']}"
    row.transcript = f"{row.transcript}\n{line}".strip() if row.transcript else line
    row.summary = result["answer"][:500]
    _save_memory(row, memory)

    db.add(
        Conversation(
            channel="voice",
            user_text=payload.text,
            assistant_text=result["answer"],
            intent=result["intent"],
            needs_human=result["needs_human"],
        )
    )
    record_learning_signal(
        db,
        session_ref=row.session_ref,
        channel="voice",
        message=payload.text,
        result=result,
    )
    db.commit()
    db.refresh(row)

    return {
        "session": row,
        "answer": result["answer"],
        "intent": result["intent"],
        "language": result.get("language", "en-NG"),
        "needs_human": result["needs_human"],
        "sources": result.get("sources", []),
        "data": result.get("data"),
        "memory": _public_memory(memory),
        "learning_suggestion": suggestion,
    }


@router.patch("/voice/sessions/{ref}/complete", response_model=VoiceOut)
def complete(ref: str, payload: VoiceClose, db: Session = Depends(get_db)):
    row = _session_or_404(db, ref)
    if payload.transcript:
        row.transcript = payload.transcript
    if payload.summary:
        row.summary = payload.summary
    row.status = "COMPLETED"
    row.last_activity_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row
