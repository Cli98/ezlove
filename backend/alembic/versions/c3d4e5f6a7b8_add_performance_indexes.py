"""add_performance_indexes

Revision ID: c3d4e5f6a7b8
Revises: f494f8854e57
Create Date: 2026-07-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'f494f8854e57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # ViewEvent - most queried table
    op.create_index('ix_view_events_viewer_viewed', 'view_events', ['viewer_id', 'viewed_at'])
    op.create_index('ix_view_events_moment', 'view_events', ['moment_id'])

    # CareMoment - timeline, risk scoring
    op.create_index('ix_care_moments_elder_created', 'care_moments', ['elder_id', 'created_at'])
    op.create_index('ix_care_moments_sender', 'care_moments', ['sender_id'])

    # Alert - dashboard, pending alerts
    op.create_index('ix_alerts_community_resolved_created', 'alerts', ['community_id', 'is_resolved', 'created_at'])
    op.create_index('ix_alerts_elder', 'alerts', ['elder_id'])

    # CommunityElder - nearly every community endpoint
    op.create_index('ix_community_elders_community', 'community_elders', ['community_id'])

    # CommunityEvent - dashboard, timeline
    op.create_index('ix_community_events_community_elder_created', 'community_events', ['community_id', 'elder_id', 'created_at'])

    # CanteenRecord - canteen checks
    op.create_index('ix_canteen_records_community_created', 'canteen_records', ['community_id', 'created_at'])


def downgrade():
    op.drop_index('ix_canteen_records_community_created')
    op.drop_index('ix_community_events_community_elder_created')
    op.drop_index('ix_community_elders_community')
    op.drop_index('ix_alerts_elder')
    op.drop_index('ix_alerts_community_resolved_created')
    op.drop_index('ix_care_moments_sender')
    op.drop_index('ix_care_moments_elder_created')
    op.drop_index('ix_view_events_moment')
    op.drop_index('ix_view_events_viewer_viewed')
