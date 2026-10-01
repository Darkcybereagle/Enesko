from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MallOut(BaseModel):
    id: int
    name: str
    city: str
    country: str
    active: bool
    model_config = ConfigDict(from_attributes=True)


class FloorOut(BaseModel):
    id: int
    mall_id: int
    name: str
    level: int
    model_config = ConfigDict(from_attributes=True)


class ZoneOut(BaseModel):
    id: int
    floor_id: int
    code: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class CategoryOut(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class StoreOut(BaseModel):
    id: int
    mall_id: int
    floor_id: int | None
    zone_id: int | None
    name: str
    unit: str | None
    description: str | None
    nearest_landmark: str | None
    opening_hours: str | None
    data_status: str
    source_name: str | None
    source_url: str | None
    verified_at: datetime | None
    expires_at: datetime | None
    map_node_code: str | None
    discovery_priority: int
    verification_confidence: str
    location_confidence: str
    public_rating: float | None
    public_review_count: int | None
    active: bool
    categories: list[CategoryOut] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class FacilityOut(BaseModel):
    id: int
    mall_id: int
    floor_id: int | None
    zone_id: int | None
    asset_code: str
    name: str
    facility_type: str
    status: str
    data_status: str
    model_config = ConfigDict(from_attributes=True)


class KnowledgeCreate(BaseModel):
    title: str
    source_type: str = "manual"
    source_name: str
    content: str
    verified: bool = False
    expires_at: datetime | None = None


class KnowledgeOut(KnowledgeCreate):
    id: int
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    channel: str = "web"


class SourceRef(BaseModel):
    title: str
    source_name: str
    updated_at: datetime
    expires_at: datetime | None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    needs_human: bool = False
    sources: list[SourceRef] = Field(default_factory=list)
    data: dict | None = None
