"""add books and book_borrows

Revision ID: 71b7a52b471a
Revises: b6d09d052689
Create Date: 2026-08-01 22:24:49.938129

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '71b7a52b471a'
down_revision: Union[str, Sequence[str], None] = 'b6d09d052689'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# NOTE: as with the meal_records migration, autogenerate's unrelated NOT-NULL
# tightenings and the "removed" pgvector HNSW index were pruned by hand.


def upgrade() -> None:
    op.create_table(
        'books',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=False),
        sa.Column('serial_number', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('serial_number'),
    )
    op.create_table(
        'book_borrows',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('book_id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),
        sa.Column('class_section_id', sa.UUID(), nullable=False),
        sa.Column('borrowed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fine_amount', sa.Integer(), nullable=False),
        sa.Column('fine_settled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['class_section_id'], ['class_sections.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('book_borrows')
    op.drop_table('books')
