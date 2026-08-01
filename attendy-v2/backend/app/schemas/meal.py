import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.class_section import ClassSectionOut


class MealRow(BaseModel):
    student_id: uuid.UUID
    name: str
    roll_number: int
    class_section: ClassSectionOut
    status: str  # "present" | "absent"
    event_time: datetime | None
    source: str | None


class MealSheetResponse(BaseModel):
    date: date
    items: list[MealRow]
    total: int
    present_count: int
    absent_count: int
