"""add contributors table

Revision ID: f2b7c9d4e6a8
Revises: c7e8f9a0b1c2
Create Date: 2026-10-16 12:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2b7c9d4e6a8'
down_revision: Union[str, None] = 'c7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contributors',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=True),
        sa.Column('wechat_id', sa.String(length=64), nullable=False),
        sa.Column('note', sa.String(length=200), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('wechat_id')
    )

    # 初始名单：易挂念公益志愿同学（项目方提供的微信号与姓名；寄语后续可补充）
    contributors = sa.table(
        'contributors',
        sa.column('id', sa.Uuid()),
        sa.column('name', sa.String()),
        sa.column('wechat_id', sa.String()),
        sa.column('note', sa.String()),
        sa.column('sort_order', sa.Integer()),
        sa.column('is_active', sa.Boolean()),
    )
    op.bulk_insert(contributors, [
        {'id': uuid.UUID('c0a8f1e2-3b4d-4e5f-8a9b-0c1d2e3f4a51'), 'name': '何宪琳', 'wechat_id': 'likeVisitor', 'note': None, 'sort_order': 1, 'is_active': True},
        {'id': uuid.UUID('c0a8f1e2-3b4d-4e5f-8a9b-0c1d2e3f4a52'), 'name': '郭昱希', 'wechat_id': 'hhh98051422', 'note': None, 'sort_order': 2, 'is_active': True},
        {'id': uuid.UUID('c0a8f1e2-3b4d-4e5f-8a9b-0c1d2e3f4a53'), 'name': '李长霖', 'wechat_id': 'hichanglin', 'note': None, 'sort_order': 3, 'is_active': True},
        {'id': uuid.UUID('c0a8f1e2-3b4d-4e5f-8a9b-0c1d2e3f4a54'), 'name': '黄祈安', 'wechat_id': '18107126654', 'note': None, 'sort_order': 4, 'is_active': True},
    ])


def downgrade() -> None:
    op.drop_table('contributors')
