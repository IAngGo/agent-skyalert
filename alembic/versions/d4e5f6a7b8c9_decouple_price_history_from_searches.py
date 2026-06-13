"""decouple price_history from searches

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-13

Makes price_history.search_id nullable and changes its foreign key from
ON DELETE CASCADE to ON DELETE SET NULL. This lets historical price
observations survive deletion of their parent Search, so they remain
available for global price analytics.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow price_history rows to outlive their parent Search."""
    op.alter_column("price_history", "search_id", nullable=True)
    op.drop_constraint("price_history_search_id_fkey", "price_history", type_="foreignkey")
    op.create_foreign_key(
        "price_history_search_id_fkey",
        "price_history",
        "searches",
        ["search_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Restore CASCADE delete and NOT NULL on price_history.search_id."""
    op.drop_constraint("price_history_search_id_fkey", "price_history", type_="foreignkey")
    op.create_foreign_key(
        "price_history_search_id_fkey",
        "price_history",
        "searches",
        ["search_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("price_history", "search_id", nullable=False)
