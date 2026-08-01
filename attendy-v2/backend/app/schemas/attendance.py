import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.class_section import ClassSectionOut


class AttendanceRow(BaseModel):
    student_id: uuid.UUID
    name: str
    roll_number: int
    class_section: ClassSectionOut
    status: str  # "present" | "absent"
    event_time: datetime | None
    confidence: float | None
    source: str | None


class AttendanceSheetResponse(BaseModel):
    date: date
    items: list[AttendanceRow]
    total: int
    present_count: int
    absent_count: int


class ManualAttendanceRequest(BaseModel):
    student_id: uuid.UUID
    event_date: date
    status: str  # "present" | "absent"


class DailySummaryPoint(BaseModel):
    date: date
    present_count: int
    absent_count: int
    total: int


class AttendanceSummaryResponse(BaseModel):
    date_from: date
    date_to: date
    points: list[DailySummaryPoint]
    overall_present_rate: float


class ChronicAbsenteeRow(BaseModel):
    student_id: uuid.UUID
    name: str
    roll_number: int
    class_section: ClassSectionOut
    school_days: int
    absent_days: int
    absence_rate: float


class ChronicAbsenteesResponse(BaseModel):
    date_from: date
    date_to: date
    threshold: float
    items: list[ChronicAbsenteeRow]
