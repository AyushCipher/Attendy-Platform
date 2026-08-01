"""add meal_records

Revision ID: b6d09d052689
Revises: 3250735fe0bb
Create Date: 2026-08-01 22:03:37.460944

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b6d09d052689'
down_revision: Union[str, Sequence[str], None] = '3250735fe0bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# NOTE: `alembic revision --autogenerate` also proposed a pile of unrelated NOT-NULL
# tightenings on existing columns and, alarmingly, *dropping the pgvector HNSW index*
# on face_embeddings (Alembic can't represent that raw-SQL-created index in metadata,
# so it reads as "removed"). All of that noise was pruned by hand -- this migration
# only adds what it says it adds.


def upgrade() -> None:
    op.create_table(
        'meal_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),
        sa.Column('class_section_id', sa.UUID(), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('event_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('marked_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_section_id'], ['class_sections.id']),
        sa.ForeignKeyConstraint(['marked_by'], ['admins.id']),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'event_date', name='uq_meal_student_date'),
    )
    op.create_index('ix_meal_class_section_date', 'meal_records', ['class_section_id', 'event_date'])
    op.create_index(op.f('ix_meal_records_event_date'), 'meal_records', ['event_date'])


def downgrade() -> None:
    op.drop_index(op.f('ix_meal_records_event_date'), table_name='meal_records')
    op.drop_index('ix_meal_class_section_date', table_name='meal_records')
    op.drop_table('meal_records')
