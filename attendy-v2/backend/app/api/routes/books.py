import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models.book import Book
from app.db.models.book_borrow import BookBorrow
from app.schemas.book import BookBorrowListResponse, BookBorrowOut, BookCreate, BookListResponse, BookOut
from app.services.library_service import compute_fine
from app.services.qr_service import build_qr_png

router = APIRouter(prefix="/books", tags=["books"], dependencies=[Depends(get_current_admin)])


def _to_book_out(book: Book, currently_borrowed: bool) -> BookOut:
    return BookOut(
        id=book.id,
        name=book.name,
        author=book.author,
        serial_number=book.serial_number,
        status=book.status,
        currently_borrowed=currently_borrowed,
        created_at=book.created_at,
    )


@router.get("", response_model=BookListResponse)
async def list_books(
    search: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    borrowed_expr = exists().where(BookBorrow.book_id == Book.id, BookBorrow.returned_at.is_(None))

    query = select(Book, borrowed_expr.label("currently_borrowed"))
    if status_filter is not None:
        query = query.where(Book.status == status_filter)
    if search:
        like = f"%{search}%"
        query = query.where(or_(Book.name.ilike(like), Book.author.ilike(like), Book.serial_number.ilike(like)))

    total = (await db.execute(select(func.count()).select_from(query.with_only_columns(Book.id).subquery()))).scalar_one()
    rows = (await db.execute(query.order_by(Book.name))).all()

    items = [_to_book_out(book, borrowed) for book, borrowed in rows]
    return BookListResponse(items=items, total=total)


@router.post("", response_model=BookOut, status_code=status.HTTP_201_CREATED)
async def create_book(payload: BookCreate, db: AsyncSession = Depends(get_db)):
    book = Book(name=payload.name, author=payload.author, serial_number=payload.serial_number)
    db.add(book)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A book with this serial number already exists") from exc

    await db.refresh(book)
    return _to_book_out(book, currently_borrowed=False)


@router.get("/{book_id}/qr-code")
async def get_book_qr_code(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    book = await _get_book_or_404(book_id, db)
    png_bytes = build_qr_png(book.id)
    return Response(content=png_bytes, media_type="image/png")


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    book = await _get_book_or_404(book_id, db)
    book.status = "retired"  # soft delete, same convention as Student.status
    await db.commit()


@router.post("/{book_id}/reactivate", response_model=BookOut)
async def reactivate_book(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Undoes a retire. serial_number is unique across all statuses, so a retired
    book still blocks re-registering the same serial -- reactivating the existing
    row is the way back, not creating a new one.
    """
    book = await _get_book_or_404(book_id, db)
    book.status = "active"
    await db.commit()
    await db.refresh(book)

    currently_borrowed = (
        await db.execute(
            select(exists().where(BookBorrow.book_id == book.id, BookBorrow.returned_at.is_(None)))
        )
    ).scalar_one()
    return _to_book_out(book, currently_borrowed=currently_borrowed)


@router.get("/borrows", response_model=BookBorrowListResponse)
async def list_borrows(
    only_open: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """Admin view of borrow history -- `only_open=true` (default) shows just what's
    currently out, for the "who has which book, and who owes a fine" table.
    """
    query = select(BookBorrow).options(
        selectinload(BookBorrow.book), selectinload(BookBorrow.student)
    )
    if only_open:
        query = query.where(BookBorrow.returned_at.is_(None))

    rows = (await db.execute(query.order_by(BookBorrow.borrowed_at.desc()))).scalars().all()

    now = datetime.datetime.now(datetime.timezone.utc)
    items = []
    for borrow in rows:
        # Computed live rather than trusting the stored fine_amount, which is only
        # as fresh as the last time the daily job ran -- this keeps the admin view
        # accurate for a borrow that crossed the 7-day mark minutes ago.
        live_fine = (
            borrow.fine_amount
            if borrow.returned_at is not None
            else max(borrow.fine_amount, compute_fine(borrow.borrowed_at, now))
        )
        items.append(
            BookBorrowOut(
                id=borrow.id,
                book_id=borrow.book_id,
                book_name=borrow.book.name,
                student_id=borrow.student_id,
                student_name=borrow.student.name,
                borrowed_at=borrow.borrowed_at,
                returned_at=borrow.returned_at,
                fine_amount=live_fine,
                fine_settled=borrow.fine_settled,
                is_overdue=live_fine > 0,
            )
        )

    return BookBorrowListResponse(items=items, total=len(items))


@router.post("/borrows/{borrow_id}/settle-fine", response_model=BookBorrowOut)
async def settle_fine(borrow_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    borrow = await db.get(
        BookBorrow, borrow_id, options=[selectinload(BookBorrow.book), selectinload(BookBorrow.student)]
    )
    if borrow is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Borrow record not found")

    borrow.fine_settled = True
    await db.commit()

    return BookBorrowOut(
        id=borrow.id,
        book_id=borrow.book_id,
        book_name=borrow.book.name,
        student_id=borrow.student_id,
        student_name=borrow.student.name,
        borrowed_at=borrow.borrowed_at,
        returned_at=borrow.returned_at,
        fine_amount=borrow.fine_amount,
        fine_settled=borrow.fine_settled,
        is_overdue=borrow.fine_amount > 0,
    )


async def _get_book_or_404(book_id: uuid.UUID, db: AsyncSession) -> Book:
    book = await db.get(Book, book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Book not found")
    return book
