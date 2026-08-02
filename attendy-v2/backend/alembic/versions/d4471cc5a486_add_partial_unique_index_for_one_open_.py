"""add partial unique index for one open borrow per book

Revision ID: d4471cc5a486
Revises: 71b7a52b471a
Create Date: 2026-08-02 14:26:58.768501

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4471cc5a486'
down_revision: Union[str, Sequence[str], None] = '71b7a52b471a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# NOTE: as with prior migrations, autogenerate's unrelated NOT-NULL tightenings and
# the "removed" pgvector HNSW index were pruned by hand -- only the new index below
# is a real change.


def upgrade() -> None:
    op.create_index(
        'uq_book_borrows_one_open_per_book',
        'book_borrows',
        ['book_id'],
        unique=True,
        postgresql_where=sa.text('returned_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'uq_book_borrows_one_open_per_book',
        table_name='book_borrows',
        postgresql_where=sa.text('returned_at IS NULL'),
    )
