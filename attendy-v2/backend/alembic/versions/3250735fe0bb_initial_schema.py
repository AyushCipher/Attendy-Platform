"""initial schema

Revision ID: 3250735fe0bb
Revises:
Create Date: 2026-07-31 22:25:19.194547

"""
from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3250735fe0bb'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 512


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="admin"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admins_email", "admins", ["email"])

    op.create_table(
        "class_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grade", sa.SmallInteger, nullable=False),
        sa.Column("section", sa.String(4), nullable=False),
        sa.UniqueConstraint("grade", "section", name="uq_class_sections_grade_section"),
    )

    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("roll_number", sa.Integer, nullable=False),
        sa.Column(
            "class_section_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("class_sections.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("photo_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "roll_number", "class_section_id", name="uq_students_roll_class_section"
        ),
    )

    op.create_table(
        "face_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="enrollment"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute(
        "CREATE INDEX ix_face_embeddings_embedding_hnsw ON face_embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "attendance_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "class_section_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("class_sections.id"),
            nullable=False,
        ),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("source", sa.String(16), nullable=False, server_default="face"),
        sa.Column(
            "marked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("admins.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "event_date", name="uq_attendance_student_date"),
    )
    op.create_index("ix_attendance_records_event_date", "attendance_records", ["event_date"])
    op.create_index(
        "ix_attendance_class_section_date",
        "attendance_records",
        ["class_section_id", "event_date"],
    )


def downgrade() -> None:
    op.drop_table("attendance_records")
    op.drop_index("ix_face_embeddings_embedding_hnsw", table_name="face_embeddings")
    op.drop_table("face_embeddings")
    op.drop_table("students")
    op.drop_table("class_sections")
    op.drop_table("admins")
    op.execute("DROP EXTENSION IF EXISTS vector")
