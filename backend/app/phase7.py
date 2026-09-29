from datetime import datetime
import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.config import settings
from app.database import Base, get_db
from app.integrations import email_adapter, whatsapp_adapter
from app.models import Conversation
from app.security import Role, User, require_roles
from app.services import orchestrate


class ChannelMessage(Base):
    __tablename__ = "channel_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(30), index=True)
    direction: Mapped[str] = mapped_column(String(20), default="OUTBOUND")
    recipient: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str | None] = mapped_column(String(240), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="PENDING")
    provider: Mapped[str] = mapped_column(String(80), default="NOT_CONFIGURED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MessageCreate(BaseModel):
    recipient: str
    body: str
    subject: str | None = None


class InboundMessage(BaseModel):
    sender: str
    body: str
    subject: str | None = None


class MessageOut(BaseModel):
    id: int
    channel: str
    direction: str
    recipient: str
    subject: str | None
    body: str
    status: str
    provider: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


def seed_phase7(db: Session):
    for row in db.scalars(select(ChannelMessage).where(ChannelMessage.status == "QUEUED_DEMO")).all():
        row.status = "NOT_CONFIGURED"
        row.provider = "NOT_CONFIGURED"
    db.commit()


def _record_message(
    db: Session,
    *,
    channel: str,
    direction: str,
    recipient: str,
    body: str,
    subject: str | None = None,
    status: str,
    provider: str,
) -> ChannelMessage:
    row = ChannelMessage(
        channel=channel,
        direction=direction,
        recipient=recipient,
        subject=subject,
        body=body,
        status=status,
        provider=provider,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _process_inbound(db: Session, *, channel: str, sender: str, body: str) -> dict:
    inbound = _record_message(
        db,
        channel=channel,
        direction="INBOUND",
        recipient=sender,
        body=body,
        status="RECEIVED",
        provider="META_WHATSAPP_CLOUD" if channel == "WHATSAPP" else "INBOUND_WEBHOOK",
    )
    result = orchestrate(db, body)
    db.add(
        Conversation(
            channel=channel.lower(),
            user_text=body,
            assistant_text=result["answer"],
            intent=result["intent"],
            needs_human=result["needs_human"],
        )
    )
    db.commit()
    return {
        "message": MessageOut.model_validate(inbound).model_dump(mode="json"),
        "assistant": result,
    }


router = APIRouter(prefix="/api/v1", tags=["WhatsApp & Email"])


@router.post("/channels/whatsapp/messages", response_model=MessageOut, status_code=202)
def whatsapp(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            Role.PLATFORM_SUPER_ADMIN,
            Role.MALL_ADMINISTRATOR,
            Role.CUSTOMER_SERVICE,
            Role.TENANT_MANAGEMENT,
        )
    ),
):
    result = whatsapp_adapter.send_text(payload.recipient, payload.body)
    return _record_message(
        db,
        channel="WHATSAPP",
        direction="OUTBOUND",
        recipient=payload.recipient,
        body=payload.body,
        subject=payload.subject,
        status=result.status,
        provider=result.provider,
    )


@router.post("/channels/email/messages", response_model=MessageOut, status_code=202)
def email(
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            Role.PLATFORM_SUPER_ADMIN,
            Role.MALL_ADMINISTRATOR,
            Role.CUSTOMER_SERVICE,
            Role.TENANT_MANAGEMENT,
        )
    ),
):
    result = email_adapter.send(payload.recipient, payload.subject, payload.body)
    return _record_message(
        db,
        channel="EMAIL",
        direction="OUTBOUND",
        recipient=payload.recipient,
        body=payload.body,
        subject=payload.subject,
        status=result.status,
        provider=result.provider,
    )


@router.get("/channels/messages", response_model=list[MessageOut])
def messages(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            Role.PLATFORM_SUPER_ADMIN,
            Role.MALL_ADMINISTRATOR,
            Role.CUSTOMER_SERVICE,
            Role.TENANT_MANAGEMENT,
        )
    ),
):
    return list(db.scalars(select(ChannelMessage).order_by(ChannelMessage.id.desc())).all())


@router.get("/channels/whatsapp/webhook")
def verify_whatsapp_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    if mode == "subscribe" and verify_token == settings.whatsapp_verify_token and challenge:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="WhatsApp webhook verification failed")


def _verify_whatsapp_signature(raw_body: bytes, signature: str | None) -> None:
    if not settings.whatsapp_app_secret:
        if settings.app_env == "production":
            raise HTTPException(status_code=503, detail="WhatsApp app secret is not configured")
        return

    if not signature or not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing WhatsApp webhook signature")

    expected = hmac.new(
        settings.whatsapp_app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    supplied = signature.removeprefix("sha256=")
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Invalid WhatsApp webhook signature")


@router.post("/channels/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    raw = await request.body()
    _verify_whatsapp_signature(raw, x_hub_signature_256)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid WhatsApp webhook payload")

    processed = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                sender = message.get("from")
                text = (message.get("text") or {}).get("body")
                if sender and text:
                    processed.append(
                        _process_inbound(
                            db,
                            channel="WHATSAPP",
                            sender=sender,
                            body=text,
                        )
                    )

    return {"received": True, "processed": len(processed)}


@router.post("/channels/email/inbound")
def email_inbound(
    payload: InboundMessage,
    x_enesko_webhook_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if x_enesko_webhook_secret != settings.inbound_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid inbound webhook secret")
    return _process_inbound(
        db,
        channel="EMAIL",
        sender=payload.sender,
        body=payload.body,
    )
