"""add gender to community elders

Revision ID: e4f5a6b7c8d9
Revises: d1e2f3a4b5c6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("community_elders", sa.Column("gender", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("community_elders", "gender")
