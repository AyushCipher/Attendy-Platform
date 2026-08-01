import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    serial_number: str = Field(min_length=1, max_length=64)


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    author: str
    serial_number: str
    status: str
    currently_borrowed: bool
    created_at: datetime


class BookListResponse(BaseModel):
    items: list[BookOut]
    total: int


class BookBorrowOut(BaseModel):
    id: uuid.UUID
    book_id: uuid.UUID
    book_name: str
    student_id: uuid.UUID
    student_name: str
    borrowed_at: datetime
    returned_at: datetime | None
    fine_amount: int
    fine_settled: bool
    is_overdue: bool


class BookBorrowListResponse(BaseModel):
    items: list[BookBorrowOut]
    total: int
