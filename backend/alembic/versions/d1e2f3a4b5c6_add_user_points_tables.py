"""add user points tables

Revision ID: d1e2f3a4b5c6
Revises: c3d4e5f6a7b8
Create Date: 2026-07-26 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_point_accounts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('total_points', sa.Integer(), nullable=False),
    sa.Column('available_points', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('user_point_transactions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('tx_type', sa.String(length=8), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('balance_after', sa.Integer(), nullable=False),
    sa.Column('category', sa.String(length=32), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_point_transactions_user_id', 'user_point_transactions', ['user_id'])
    op.create_index('ix_user_point_transactions_category', 'user_point_transactions', ['category'])
    op.create_index('ix_user_point_transactions_created_at', 'user_point_transactions', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_user_point_transactions_created_at', table_name='user_point_transactions')
    op.drop_index('ix_user_point_transactions_category', table_name='user_point_transactions')
    op.drop_index('ix_user_point_transactions_user_id', table_name='user_point_transactions')
    op.drop_table('user_point_transactions')
    op.drop_table('user_point_accounts')
