from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import attendance, auth, class_sections, students
from app.core.config import get_settings
from app.ws import feed, recognize

settings = get_settings()

app = FastAPI(title="Attendy API", version="0.1.0")

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
app.include_router(feed.router)
app.include_router(recognize.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
