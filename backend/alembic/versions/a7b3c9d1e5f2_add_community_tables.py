"""add community tables

Revision ID: a7b3c9d1e5f2
Revises: 426ec80efea4
Create Date: 2026-06-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7b3c9d1e5f2'
down_revision: Union[str, None] = '426ec80efea4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # communities
    op.create_table('communities',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('address', sa.String(length=256), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    # community_workers
    op.create_table('community_workers',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('community_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('role_label', sa.String(length=32), nullable=True),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_community_workers_phone'), 'community_workers', ['phone'], unique=True)

    # community_elders
    op.create_table('community_elders',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('community_id', sa.UUID(), nullable=False),
    sa.Column('elder_id', sa.UUID(), nullable=False),
    sa.Column('care_level', sa.String(length=1), nullable=False),
    sa.Column('address', sa.String(length=128), nullable=True),
    sa.Column('emergency_contact_name', sa.String(length=64), nullable=True),
    sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True),
    sa.Column('health_notes', sa.Text(), nullable=True),
    sa.Column('assigned_worker_id', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ),
    sa.ForeignKeyConstraint(['elder_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['assigned_worker_id'], ['community_workers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # canteen_records
    op.create_table('canteen_records',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('community_id', sa.UUID(), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=False),
    sa.Column('source_format', sa.String(length=16), nullable=False),
    sa.Column('parsed_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('parsed_at', sa.DateTime(), nullable=True),
    sa.Column('parse_status', sa.String(length=16), nullable=False),
    sa.Column('recorded_by', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ),
    sa.ForeignKeyConstraint(['recorded_by'], ['community_workers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # community_events
    op.create_table('community_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('community_id', sa.UUID(), nullable=False),
    sa.Column('elder_id', sa.UUID(), nullable=False),
    sa.Column('event_type', sa.String(length=16), nullable=False),
    sa.Column('source', sa.String(length=16), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('severity', sa.String(length=16), nullable=False),
    sa.Column('is_resolved', sa.Boolean(), nullable=False),
    sa.Column('resolved_by', sa.UUID(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ),
    sa.ForeignKeyConstraint(['elder_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['resolved_by'], ['community_workers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('community_events')
    op.drop_table('canteen_records')
    op.drop_table('community_elders')
    op.drop_index(op.f('ix_community_workers_phone'), table_name='community_workers')
    op.drop_table('community_workers')
    op.drop_table('communities')
