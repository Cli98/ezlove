"""add community_worker_assignments table

Revision ID: b8c4d6e0f1a3
Revises: a7b3c9d1e5f2
Create Date: 2026-06-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8c4d6e0f1a3'
down_revision: Union[str, None] = 'a7b3c9d1e5f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('community_worker_assignments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('worker_id', sa.UUID(), nullable=False),
    sa.Column('community_id', sa.UUID(), nullable=False),
    sa.Column('role_label', sa.String(length=32), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['worker_id'], ['community_workers.id'], ),
    sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('community_worker_assignments')
