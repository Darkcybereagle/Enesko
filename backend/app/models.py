from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Table, Text, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


store_categories = Table(
    "store_categories",
    Base.metadata,
    Column("store_id", ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Mall(Base):
    __tablename__ = "malls"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    city: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(120), default="Nigeria")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    floors: Mapped[list["Floor"]] = relationship(back_populates="mall", cascade="all, delete-orphan")


class Floor(Base):
    __tablename__ = "floors"
    id: Mapped[int] = mapped_column(primary_key=True)
    mall_id: Mapped[int] = mapped_column(ForeignKey("malls.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    level: Mapped[int] = mapped_column(Integer)
    mall: Mapped["Mall"] = relationship(back_populates="floors")
    zones: Mapped[list["Zone"]] = relationship(back_populates="floor", cascade="all, delete-orphan")


class Zone(Base):
    __tablename__ = "zones"
    id: Mapped[int] = mapped_column(primary_key=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("floors.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    floor: Mapped["Floor"] = relationship(back_populates="zones")


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    stores: Mapped[list["Store"]] = relationship(secondary=store_categories, back_populates="categories")


class Store(Base):
    __tablename__ = "stores"
    id: Mapped[int] = mapped_column(primary_key=True)
    mall_id: Mapped[int] = mapped_column(ForeignKey("malls.id", ondelete="CASCADE"), index=True)
    floor_id: Mapped[int | None] = mapped_column(ForeignKey("floors.id", ondelete="SET NULL"), nullable=True, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    nearest_landmark: Mapped[str | None] = mapped_column(String(200), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(200), nullable=True)
    data_status: Mapped[str] = mapped_column(String(30), default="UNVERIFIED")
    source_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    map_node_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    categories: Mapped[list["Category"]] = relationship(secondary=store_categories, back_populates="stores")


class Facility(Base):
    __tablename__ = "facilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    mall_id: Mapped[int] = mapped_column(ForeignKey("malls.id", ondelete="CASCADE"), index=True)
    floor_id: Mapped[int | None] = mapped_column(ForeignKey("floors.id", ondelete="SET NULL"), nullable=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"), nullable=True)
    asset_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    facility_type: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    data_status: Mapped[str] = mapped_column(String(30), default="UNVERIFIED")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240), index=True)
    source_type: Mapped[str] = mapped_column(String(80), default="manual")
    source_name: Mapped[str] = mapped_column(String(240))
    content: Mapped[str] = mapped_column(Text)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(50), default="web")
    user_text: Mapped[str] = mapped_column(Text)
    assistant_text: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(String(120), default="unknown")
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
