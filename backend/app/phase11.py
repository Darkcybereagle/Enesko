from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.integrations import parking_adapter
from app.phase10 import ParkingStatus
from app.security import Role, User, require_roles


router = APIRouter(prefix="/api/v1", tags=["Parking Integration"])


def seed_phase11(db):
    return


class ParkingSyncResult(BaseModel):
    configured: bool
    synced: int
    provider: str
    detail: str | None = None


@router.get("/parking/integration-status")
def status():
    return {
        "adapter": "ParkingAdapter",
        "configured": parking_adapter.configured,
        "health": "READY" if parking_adapter.configured else "NOT_CONFIGURED",
        "fallback": "staff_updated_phase10",
        "live_counts_available": parking_adapter.configured,
    }


@router.post("/parking/integration-sync", response_model=ParkingSyncResult)
def sync_parking(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            Role.PLATFORM_SUPER_ADMIN,
            Role.MALL_ADMINISTRATOR,
            Role.PARKING,
        )
    ),
):
    configured, payload, detail = parking_adapter.fetch()
    if not configured:
        return {
            "configured": False,
            "synced": 0,
            "provider": parking_adapter.provider_name,
            "detail": detail,
        }
    if payload is None:
        return {
            "configured": True,
            "synced": 0,
            "provider": parking_adapter.provider_name,
            "detail": detail or "Parking feed could not be read.",
        }

    items = payload.get("areas", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise HTTPException(status_code=502, detail="Parking feed must provide a list of areas")

    allowed = {"AVAILABLE", "BUSY", "NEAR_CAPACITY", "FULL", "CLOSED", "UNKNOWN"}
    now = datetime.utcnow()
    synced = 0

    for item in items:
        if not isinstance(item, dict):
            continue
        area_code = str(item.get("area_code") or "").strip()
        if not area_code:
            continue
        status_value = str(item.get("occupancy_status") or "UNKNOWN").upper()
        if status_value not in allowed:
            status_value = "UNKNOWN"

        row = db.scalar(select(ParkingStatus).where(ParkingStatus.area_code == area_code))
        if not row:
            row = ParkingStatus(
                area_code=area_code,
                name=str(item.get("name") or area_code),
            )
            db.add(row)

        row.name = str(item.get("name") or row.name)
        if item.get("capacity") is not None:
            row.capacity = int(item["capacity"])
        row.occupancy_status = status_value
        row.source = parking_adapter.provider_name
        row.data_status = "INTEGRATION_VERIFIED"
        row.updated_at = now
        row.expires_at = now + timedelta(minutes=max(int(item.get("expires_minutes") or 10), 1))
        synced += 1

    db.commit()
    return {
        "configured": True,
        "synced": synced,
        "provider": parking_adapter.provider_name,
        "detail": None,
    }
