"""close short stillness rule (12h no-activity becomes the only device activity alert)

Revision ID: 8f2c1d4e5a90
Revises: c7e8f9a0b1c2
Create Date: 2026-11-11 15:30:00.000000

2026-11-11 森滔确认口径：无活动满 12 小时提醒一次（最低级 info），仍未活动则每 12 小时
再提醒一次。原「1 小时短时静止」提醒并入该口径，存量社区统一关闭（规则保留，可手动再开）。
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8f2c1d4e5a90'
down_revision: Union[str, None] = 'c7e8f9a0b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 关闭短时静止规则，并把阈值/重复间隔对齐 12 小时口径（重新开启时不会退回 1 小时密集提醒）
    op.execute(
        """
        UPDATE alert_rules
           SET enabled = false,
               threshold_hours = 12,
               config = CASE
                   WHEN config IS NULL THEN NULL
                   ELSE config::jsonb || '{"dedupe_hours": 12}'::jsonb
               END
         WHERE rule_type = 'stillness'
        """
    )


def downgrade() -> None:
    # 迁移前的启用状态无法还原，回滚时恢复旧默认阈值；规则保持关闭由后台手动开启
    op.execute(
        """
        UPDATE alert_rules
           SET threshold_hours = 1,
               config = CASE
                   WHEN config IS NULL THEN NULL
                   ELSE config::jsonb || '{"dedupe_hours": 6}'::jsonb
               END
         WHERE rule_type = 'stillness'
        """
    )