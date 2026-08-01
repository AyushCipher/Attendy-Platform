import uuid

from pydantic import BaseModel, ConfigDict, Field


class ClassSectionCreate(BaseModel):
    grade: int = Field(ge=1, le=12)
    section: str = Field(min_length=1, max_length=4)


class ClassSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    grade: int
    section: str
    label: str
