from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models.admin import Admin
from app.db.models.class_section import ClassSection
from app.schemas.class_section import ClassSectionCreate, ClassSectionOut

router = APIRouter(prefix="/class-sections", tags=["class-sections"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=list[ClassSectionOut])
async def list_class_sections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ClassSection).order_by(ClassSection.grade, ClassSection.section))
    return [ClassSectionOut.model_validate(cs) for cs in result.scalars().all()]


@router.post("", response_model=ClassSectionOut, status_code=status.HTTP_201_CREATED)
async def create_class_section(
    payload: ClassSectionCreate,
    db: AsyncSession = Depends(get_db),
    _admin: Admin = Depends(get_current_admin),
):
    class_section = ClassSection(grade=payload.grade, section=payload.section.upper())
    db.add(class_section)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This class/section already exists") from exc
    await db.refresh(class_section)
    return ClassSectionOut.model_validate(class_section)


@router.delete("/{class_section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class_section(class_section_id: str, db: AsyncSession = Depends(get_db)):
    class_section = await db.get(ClassSection, class_section_id)
    if class_section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class/section not found")
    await db.delete(class_section)
    await db.commit()
