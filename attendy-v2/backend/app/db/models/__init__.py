from app.db.models.admin import Admin
from app.db.models.attendance import AttendanceRecord
from app.db.models.book import Book
from app.db.models.book_borrow import BookBorrow
from app.db.models.class_section import ClassSection
from app.db.models.face_embedding import FaceEmbedding
from app.db.models.meal import MealRecord
from app.db.models.student import Student

__all__ = [
    "Admin",
    "AttendanceRecord",
    "Book",
    "BookBorrow",
    "ClassSection",
    "FaceEmbedding",
    "MealRecord",
    "Student",
]
