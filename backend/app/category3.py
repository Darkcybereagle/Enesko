from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.integrations import cinema_adapter, email_adapter, parking_adapter, whatsapp_adapter
from app.learning import LearningInteraction, LearningModel
from app.models import Conversation, KnowledgeDocument
from app.phase7 import ChannelMessage
from app.phase8 import VoiceSession
from app.security import Role, User, require_roles


router = APIRouter(prefix="/api/v1", tags=["Category 3"])


CATEGORY3_PHASES = [
    {"phase": "3.1", "name": "AI tool orchestration", "status": "IMPLEMENTED"},
    {"phase": "3.2", "name": "Grounded knowledge retrieval", "status": "IMPLEMENTED"},
    {"phase": "3.3", "name": "Voice concierge", "status": "IMPLEMENTED"},
    {"phase": "3.4", "name": "WhatsApp channel", "status": "IMPLEMENTED"},
    {"phase": "3.5", "name": "Email channel", "status": "IMPLEMENTED"},
    {"phase": "3.6", "name": "Cinema integration", "status": "IMPLEMENTED"},
    {"phase": "3.7", "name": "Parking integration", "status": "IMPLEMENTED"},
    {"phase": "3.8", "name": "Integration health and release gate", "status": "IMPLEMENTED"},
]


@router.get("/category3/status")
def category3_status():
    return {
        "category": 3,
        "implementation_status": "COMPLETE",
        "external_activation_status": "CONFIGURATION_DEPENDENT",
        "phases": CATEGORY3_PHASES,
    }


@router.get("/assistant/capabilities")
def assistant_capabilities():
    return {
        "assistant": "ENESKO",
        "channels": ["web", "voice", "whatsapp", "email"],
        "tools": [
            "store_search",
            "multi_need_shopping_planner",
            "knowledge_retrieval",
            "cinema_lookup",
            "parking_lookup",
            "indoor_navigation",
            "lost_and_found_conversation",
            "session_memory",
            "approved_pattern_learning",
            "human_handoff",
            "tenant_operations",
        ],
        "grounding_policy": "verified_records_and_fresh_operational_sources",
    }


@router.get("/integrations/status")
def integrations_status():
    return {
        "whatsapp": {
            "configured": whatsapp_adapter.configured,
            "provider": whatsapp_adapter.provider_name,
        },
        "email": {
            "configured": email_adapter.configured,
            "provider": email_adapter.provider_name,
        },
        "cinema": {
            "configured": cinema_adapter.configured,
            "provider": cinema_adapter.provider_name,
        },
        "parking": {
            "configured": parking_adapter.configured,
            "provider": parking_adapter.provider_name,
        },
        "voice": {
            "configured": True,
            "provider": "BROWSER_SPEECH",
            "note": "Browser speech recognition/synthesis availability depends on the client browser.",
        },
    }


@router.get("/integrations/health")
def integrations_health(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            Role.PLATFORM_SUPER_ADMIN,
            Role.MALL_ADMINISTRATOR,
        )
    ),
):
    count = lambda model: db.scalar(select(func.count()).select_from(model)) or 0
    verified_knowledge = db.scalar(
        select(func.count())
        .select_from(KnowledgeDocument)
        .where(KnowledgeDocument.verified.is_(True))
    ) or 0

    return {
        "status": "ok",
        "environment": settings.app_env,
        "conversations": count(Conversation),
        "verified_knowledge_documents": verified_knowledge,
        "channel_messages": count(ChannelMessage),
        "voice_sessions": count(VoiceSession),
        "learning_signals": count(LearningInteraction),
        "learning_models": count(LearningModel),
        "providers": {
            "whatsapp": "READY" if whatsapp_adapter.configured else "NOT_CONFIGURED",
            "email": "READY" if email_adapter.configured else "NOT_CONFIGURED",
            "cinema": "READY" if cinema_adapter.configured else "NOT_CONFIGURED",
            "parking": "READY" if parking_adapter.configured else "NOT_CONFIGURED",
            "voice_web": "READY",
        },
    }
