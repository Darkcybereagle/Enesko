from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base, get_db
from app.models import Conversation
from app.services import orchestrate


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


@router.post("/voice/sessions", response_model=VoiceOut, status_code=201)
def start(payload: VoiceStart, db: Session = Depends(get_db)):
    row = VoiceSession(
        session_ref=f"VOICE-{uuid4().hex[:10].upper()}",
        direction=payload.direction.upper(),
        caller=payload.caller,
        provider=payload.provider.upper(),
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

    result = orchestrate(db, payload.text)
    line = f"USER: {payload.text}\nENESKO: {result['answer']}"
    row.transcript = f"{row.transcript}\n{line}".strip() if row.transcript else line
    row.summary = result["answer"][:500]

    db.add(
        Conversation(
            channel="voice",
            user_text=payload.text,
            assistant_text=result["answer"],
            intent=result["intent"],
            needs_human=result["needs_human"],
        )
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
    }


@router.patch("/voice/sessions/{ref}/complete", response_model=VoiceOut)
def complete(ref: str, payload: VoiceClose, db: Session = Depends(get_db)):
    row = _session_or_404(db, ref)
    if payload.transcript:
        row.transcript = payload.transcript
    if payload.summary:
        row.summary = payload.summary
    row.status = "COMPLETED"
    db.commit()
    db.refresh(row)
    return row
