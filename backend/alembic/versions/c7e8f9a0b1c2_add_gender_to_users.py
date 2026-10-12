"""add gender to users

Revision ID: c7e8f9a0b1c2
Revises: a9f4c7d8e2b1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7e8f9a0b1c2"
down_revision: Union[str, None] = "a9f4c7d8e2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("gender", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "gender")
