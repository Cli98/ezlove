"""保留已发布的迁移版本号，不再修改 users 表。

Revision ID: c7e8f9a0b1c2
Revises: a9f4c7d8e2b1
"""
from typing import Sequence, Union


revision: str = "c7e8f9a0b1c2"
down_revision: Union[str, None] = "a9f4c7d8e2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
