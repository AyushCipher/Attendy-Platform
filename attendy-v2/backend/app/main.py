from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import attendance, auth, books, class_sections, students
from app.core.config import get_settings
from app.db.base import async_session_factory
from app.services.fine_job import apply_overdue_fines
from app.ws import feed, recognize

settings = get_settings()


async def _run_fine_job() -> None:
    async with async_session_factory() as db:
        await apply_overdue_fines(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(_run_fine_job, "interval", days=1, id="apply_overdue_fines")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Attendy API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(class_sections.router, prefix="/api")
app.include_router(students.router, prefix="/api")
app.include_router(attendance.router, prefix="/api")
app.include_router(books.router, prefix="/api")
app.include_router(feed.router)
app.include_router(recognize.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
