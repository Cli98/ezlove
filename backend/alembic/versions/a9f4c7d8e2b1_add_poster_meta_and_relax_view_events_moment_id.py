"""add poster_meta to care_moments and relax view_events.moment_id

Revision ID: a9f4c7d8e2b1
Revises: e3e660d2b12a
Create Date: 2026-09-17 05:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f4c7d8e2b1'
down_revision: Union[str, None] = 'e3e660d2b12a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 背景（P8 阿尔法测试 DEF-6/DEF-7——模型/迁移链基线不一致修复，与
    # e3e660d2b12a（DEF-1，alert_paused_until）同族）：
    #
    # DEF-7（critical，部署阻断级）：模型 app/models/care_moment.py L21 定义了
    #   poster_meta（JSONB，nullable=True，无 default/server_default），但基线
    #   迁移链从未生成过该列的迁移（git log -S poster_meta 确认 bfd65e9 于
    #   2026-06-24 引入、无对应迁移；P8 报告 grep 迁移链零引用）——按
    #   alembic upgrade head 建立的任何库都缺该列，POST /api/v1/moments
    #   （发送牵挂，US-01 全产品第一故事）100% 500（asyncpg
    #   UndefinedColumnError，P8 报告 A1 首测实证）。
    #   本迁移补齐该列，与模型逐属性一致：类型 JSONB、可空（= nullable=True）、
    #   无默认值（模型无 default/server_default，故不写 DEFAULT 子句）。
    # DEF-6（major）：迁移 426ec80efea4_init_tables.py L98 定义 view_events.moment_id
    #   为 NOT NULL，但模型 app/models/view_event.py L15 为 nullable=True
    #   （报平安场景 moment_id 无关联牵挂、写 NULL 行）——报平安两端点
    #   （elders.py 家属代报 / users.py 老人自助）在迁移库上插 moment_id=None
    #   必 NotNullViolation 500（P8 报告 B16/B17 实证；测试库 create_all
    #   建表有 nullable 列，单测全绿掩盖漂移）。本迁移放开约束与模型对齐。
    #
    # 幂等安全（沿用 e3e660d2b12a 范式）：ADD COLUMN IF NOT EXISTS——对"列已
    # 存在"的库（create_all 建表的测试库 ezlove_test、或已手工补过列的库，
    # 如本地 ezlove 库 P8 测试基建已手工 ALTER 加列）执行升级不会报错（PG
    # NOTICE already exists, skipping）；DROP NOT NULL 对已可空的列是 no-op、
    # 天然幂等，两种建库路径均安全。
    op.execute(
        "ALTER TABLE care_moments "
        "ADD COLUMN IF NOT EXISTS poster_meta JSONB"
    )
    op.execute(
        "ALTER TABLE view_events ALTER COLUMN moment_id DROP NOT NULL"
    )


def downgrade() -> None:
    # 与 upgrade 对应：DROP COLUMN IF EXISTS 幂等（列不存在时 PG NOTICE 跳过）。
    op.execute(
        "ALTER TABLE care_moments DROP COLUMN IF EXISTS poster_meta"
    )
    # 已知限制（如实写明）：SET NOT NULL 在表内已存在 moment_id IS NULL 的行时
    # 执行失败（PG 报 null value in column "moment_id" violates not-null
    # constraint）。该类行来自报平安写入（模型语义允许 moment_id=NULL）。
    # 处置建议：本 downgrade 与模型定义再次产生漂移（回到 DEF-6 病态），仅当
    # 确认要回到"报平安功能不可用"的旧口径时才执行；执行前须先清理 NULL 行
    # （DELETE FROM view_events WHERE moment_id IS NULL，或回填有效 moment_id），
    # 否则将半途失败——poster_meta 已删、moment_id 仍可空的非对称中间态
    # （本 downgrade 两条语句非事务原子补救口径，清行前置是唯一稳妥顺序）。
    op.execute(
        "ALTER TABLE view_events ALTER COLUMN moment_id SET NOT NULL"
    )
