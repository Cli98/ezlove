"""add_alert_rules_and_extend_alerts_elders

Revision ID: 4de149b8127f
Revises: b8c4d6e0f1a3
Create Date: 2026-06-25 14:02:27.229019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4de149b8127f'
down_revision: Union[str, None] = 'b8c4d6e0f1a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 新建 alert_rules 表
    op.create_table('alert_rules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('community_id', sa.UUID(), nullable=False),
    sa.Column('care_level', sa.String(length=1), nullable=False),
    sa.Column('rule_type', sa.String(length=32), nullable=False),
    sa.Column('threshold_hours', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['community_id'], ['communities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # alerts 表：新增 8 个字段 + care_relation_id 改为 nullable
    op.add_column('alerts', sa.Column('elder_id', sa.UUID(), nullable=True))
    op.add_column('alerts', sa.Column('community_id', sa.UUID(), nullable=True))
    op.add_column('alerts', sa.Column('assigned_worker_id', sa.UUID(), nullable=True))
    op.add_column('alerts', sa.Column('escalation_level', sa.Integer(), server_default='0', nullable=False))
    op.add_column('alerts', sa.Column('response_deadline', sa.DateTime(), nullable=True))
    op.add_column('alerts', sa.Column('responded_at', sa.DateTime(), nullable=True))
    op.add_column('alerts', sa.Column('response_note', sa.Text(), nullable=True))
    op.add_column('alerts', sa.Column('trigger_rule', sa.String(length=32), nullable=True))
    op.alter_column('alerts', 'care_relation_id',
               existing_type=sa.UUID(),
               nullable=True)
    op.create_foreign_key('fk_alerts_assigned_worker', 'alerts', 'community_workers', ['assigned_worker_id'], ['id'])
    op.create_foreign_key('fk_alerts_community', 'alerts', 'communities', ['community_id'], ['id'])
    op.create_foreign_key('fk_alerts_elder', 'alerts', 'users', ['elder_id'], ['id'])

    # community_elders 表：新增 4 个风险字段
    op.add_column('community_elders', sa.Column('risk_score', sa.Integer(), nullable=True))
    op.add_column('community_elders', sa.Column('risk_level', sa.String(length=16), nullable=True))
    op.add_column('community_elders', sa.Column('risk_calculated_at', sa.DateTime(), nullable=True))
    op.add_column('community_elders', sa.Column('risk_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('community_elders', 'risk_details')
    op.drop_column('community_elders', 'risk_calculated_at')
    op.drop_column('community_elders', 'risk_level')
    op.drop_column('community_elders', 'risk_score')

    op.drop_constraint('fk_alerts_elder', 'alerts', type_='foreignkey')
    op.drop_constraint('fk_alerts_community', 'alerts', type_='foreignkey')
    op.drop_constraint('fk_alerts_assigned_worker', 'alerts', type_='foreignkey')
    op.alter_column('alerts', 'care_relation_id',
               existing_type=sa.UUID(),
               nullable=False)
    op.drop_column('alerts', 'trigger_rule')
    op.drop_column('alerts', 'response_note')
    op.drop_column('alerts', 'responded_at')
    op.drop_column('alerts', 'response_deadline')
    op.drop_column('alerts', 'escalation_level')
    op.drop_column('alerts', 'assigned_worker_id')
    op.drop_column('alerts', 'community_id')
    op.drop_column('alerts', 'elder_id')

    op.drop_table('alert_rules')
