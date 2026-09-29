from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, String, or_, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base, get_db


class CinemaShow(Base):
    __tablename__ = "cinema_shows"
    id: Mapped[int] = mapped_column(primary_key=True)
    cinema_name: Mapped[str] = mapped_column(String(200))
    movie_title: Mapped[str] = mapped_column(String(240), index=True)
    show_time: Mapped[str] = mapped_column(String(80))
    booking_reference: Mapped[str | None] = mapped_column(String(400), nullable=True)
    source: Mapped[str] = mapped_column(String(120), default="UNVERIFIED")
    data_status: Mapped[str] = mapped_column(String(30), default="UNVERIFIED")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CinemaOut(BaseModel):
    id: int
    cinema_name: str
    movie_title: str
    show_time: str
    booking_reference: str | None
    source: str
    data_status: str
    verified_at: datetime | None
    expires_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


def seed_phase9(db: Session):
    for row in list(db.scalars(select(CinemaShow)).all()):
        if row.data_status == "DEMO" or row.movie_title == "Demo Movie":
            db.delete(row)
    db.commit()


router = APIRouter(prefix="/api/v1", tags=["Cinema"])


@router.get("/cinema/shows", response_model=list[CinemaOut])
def shows(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    stmt = select(CinemaShow).where(
        or_(CinemaShow.expires_at.is_(None), CinemaShow.expires_at >= now)
    ).order_by(CinemaShow.id)
    return list(db.scalars(stmt).all())


@router.get("/cinema/integration-status")
def integration_status():
    return {
        "primary": "official_api",
        "secondary": "authorized_sync_import",
        "fallback": "authorized_staff_admin",
        "configured": False,
        "live_data_available": False,
        "cinema_name": "Silverbird Cinemas, Ikeja City Mall",
        "box_office_hours": "Mon-Sun 10:00-22:00",
        "movie_enquiry": "+234 902 606 7603",
        "official_booking_url": "https://silverbirdcinemas.com/cinema/ikeja/",
        "public_reference_verified_at": "2026-09-29",
    }
