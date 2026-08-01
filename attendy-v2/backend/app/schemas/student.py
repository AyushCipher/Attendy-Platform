import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.class_section import ClassSectionOut

Section = Literal["A", "B", "C", "D", "E", "F"]


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    roll_number: int = Field(ge=1)
    grade: int = Field(ge=1, le=12)
    section: Section


class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    roll_number: int | None = Field(default=None, ge=1)
    class_section_id: uuid.UUID | None = None
    status: str | None = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    roll_number: int
    status: str
    photo_url: str | None
    class_section: ClassSectionOut
    face_enrolled: bool
    created_at: datetime


class StudentListResponse(BaseModel):
    items: list[StudentOut]
    total: int
    page: int
    page_size: int


class FaceEnrollResult(BaseModel):
    images_received: int
    images_usable: int
    average_quality: float | None
    rejected_reasons: list[str]
    total_embeddings_stored: int
