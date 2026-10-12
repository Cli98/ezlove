"""add alert_paused_until to care_relations

Revision ID: e3e660d2b12a
Revises: d1e2f3a4b5c6
Create Date: 2026-09-16 23:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3e660d2b12a'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 背景（P5 验证 DEF-1——模型/迁移链基线不一致修复）：
    # 模型 app/models/care_relation.py L21 定义了 alert_paused_until
    # （DateTime，nullable=True，无 default/server_default），但基线迁移链
    # 从未生成过该列的迁移——按 alembic upgrade head 建立的任何库都缺该列，
    # CareRelation 全列查询将抛 UndefinedColumn（本地 ezlove 库实测复现 500，
    # 证据见 P5 报告 S-1 / S-5a / S-7a）。本迁移补齐该列，与模型逐属性一致：
    #   类型 TIMESTAMP WITHOUT TIME ZONE（= sa.DateTime）、可空（= nullable=True）、无默认值。
    # 幂等安全：使用原生 PG 的 ADD COLUMN IF NOT EXISTS——对"列已存在"的库
    # （create_all 建表的测试库、或已手工补过列的库，如生产库可能已有该列）
    # 执行升级不会报错，两种建库路径均安全。
    op.execute(
        "ALTER TABLE care_relations "
        "ADD COLUMN IF NOT EXISTS alert_paused_until TIMESTAMP WITHOUT TIME ZONE"
    )


def downgrade() -> None:
    # 与 upgrade 对应的幂等写法：DROP COLUMN IF EXISTS
    op.execute(
        "ALTER TABLE care_relations DROP COLUMN IF EXISTS alert_paused_until"
    )
