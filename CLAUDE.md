# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# EZLove — 易挂念

## 项目概览

微信小程序 + 社区管理后台，让子女通过分享日常来守护独居老人。核心机制：子女发送牵挂内容 → 老人查看 → 系统追踪已读状态 → 未读时提醒子女。社区工作人员通过管理后台查看辖区老人状态、食堂就餐、社区活动。

- 前端（小程序）：uni-app (Vue 3 Composition API + Vite) + Pinia + uview-plus
- 管理后台：Vue 3 + Element Plus + Tailwind CSS + Vue Router + Pinia
- 后端：FastAPI + PostgreSQL (asyncpg) + Redis + Alembic + APScheduler
- 部署：Docker Compose + 阿里云 ECS

## 语言与沟通

- 所有人机交互使用中文
- 代码中的注释如需添加也用中文
- commit message 使用英文

---

## 产品策略（影响所有技术决策）

1. **老人端零学习成本** —— 老人只需点微信聊天中的小程序卡片即可查看内容，不需要学会打开小程序。所有老人端页面必须大字体（≥36rpx）、高对比度、单列布局。
2. **牵挂而非监控** —— 产品传达的是家人关心，不是被监控。界面文案、推送措辞一律从"关心"角度出发，禁止出现"监控"、"追踪"、"报警"等冷冰冰的词汇。
3. **已读即在线** —— 系统通过老人查看内容的行为来判断是否在线，这是核心检测机制。view_events 表是产品骨架。
4. **AI 辅助不替代** —— AI 生成内容建议供子女选择确认，不直接发送给老人。

---

## 开发命令

```bash
# 基础设施（端口避开 ezpr：PG=5433, Redis=6380, Backend=8001）
docker-compose up -d db redis  # 仅启动数据库和缓存
docker-compose up -d           # 启动全部（含 backend + admin-frontend）

# 后端（先确保 backend/.env 存在，参照 backend/.env.example）
cd backend
uvicorn app.main:app --reload  # 开发模式 (localhost:8001)
alembic upgrade head           # 执行数据库迁移
alembic revision --autogenerate -m "desc"  # 生成迁移脚本

# 数据初始化（需 PYTHONPATH=. 且在 backend/ 目录下执行）
PYTHONPATH=. python seed_community.py --password <密码>  # 创建社区 + 管理员（幂等，已存在则跳过）
PYTHONPATH=. python seed_elders.py          # 溪东社区 2101 老人 + 15 工作人员（默认密码 admin123）
PYTHONPATH=. python seed_activity.py        # 30 天历史活动数据（牵挂、已读、食堂、事件、告警）
PYTHONPATH=. python seed_all.py             # 按顺序执行 seed_elders + seed_activity
PYTHONPATH=. python seed_demo.py            # 创建演示用完整数据（社区+老人+活动一步到位）
PYTHONPATH=. python seed_elders.py --clean  # 清空重建老人数据

# 小程序前端
cd frontend
npm run dev:h5                 # H5 开发模式 (localhost:5173)
npm run dev:mp-weixin          # 微信小程序开发模式
npm run build:h5               # H5 生产构建
npm run build:mp-weixin        # 微信小程序生产构建

# 管理后台前端
cd admin-frontend
npm run dev                    # 开发模式 (localhost:5174，API 代理到 localhost:8001)
npm run build                  # 生产构建

# 健康检查
curl http://localhost:8001/health

# Swagger 文档（仅 DEBUG=true 时可用）
# http://localhost:8001/docs
```

**注意：** 项目无测试框架、无 lint/format 配置。

---

## 架构要点

### 三端架构

本项目有三个独立前端，共享一个后端：

| 端 | 目录 | 用户 | 认证方式 |
|---|---|---|---|
| 微信小程序 | `frontend/` | 子女 & 老人 | 微信 openid → JWT（`get_current_user`） |
| 管理后台 | `admin-frontend/` | 社区工作人员 | 账号密码 → JWT（`get_current_worker`，payload 含 `type: "worker"`） |
| 后端 API | `backend/` | — | `/api/v1` 下统一挂载 |

两套认证互不相通：小程序用 `get_current_user`（`deps.py`），管理后台用 `get_current_worker`（验证 `type=worker`）。

### 认证流程

- **微信登录**：`uni.login` → 前端拿 code → `POST /api/v1/auth/wx-login` → 后端 code 换 openid → 返回 JWT
- **开发登录**：`POST /api/v1/auth/dev-login`（仅 `DEBUG=true`）
- **管理后台登录**：`POST /api/v1/community/auth/login` → 账号密码验证 → JWT（含 access + refresh token 轮换）
- **老人端静默授权**：老人打开小程序卡片时自动获取 openid，无需手动登录

### 核心业务流

```
子女发送牵挂 → care_moments 表
                  ↓
老人打开查看 → view_events 表（自动记录 openid + 时间 + 时长）
                  ↓
定时检测（APScheduler） → 未读超时 → alerts 表 → 通知子女
```

### 定时任务（APScheduler）

调度器在 FastAPI lifespan 中启动/停止，定义在 `tasks/alert_checker.py`：

| 任务 | 频率 | 说明 |
|---|---|---|
| `run_alert_rules` | 每 5 分钟 | 社区侧规则引擎：按 AlertRule 配置检测 unread_timeout / canteen_absence / no_signal |
| `check_unread_alerts` | 每 5 分钟 | 家属侧：检测今日牵挂未读是否超过关系设定的告警阈值 |
| `sync_all_communities` | 每 30 分钟 | 将家属侧告警同步为社区事件 |
| `check_escalations` | 每 15 分钟 | 超时未处理告警自动升级（最多 2 级） |
| `recalculate_risk_scores` | 每 1 小时 | 全量重算所有老人风险评分 |
| `morning_silence_check` | 每天 8:00 | 晨间静默检测：A 级 18h / B 级 24h 无活动信号则告警 |

### AI 集成（双 LLM 配置）

后端有两套 LLM 配置：
- `ANTHROPIC_API_KEY` — 直接调用 Anthropic Claude API（`claude-haiku-4-5-20251001`）
- `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL`（默认 `qwen-plus`）— 通用 LLM 接口，用于通义千问等国内模型

四处调用点：

1. **`services/ai_content.py`** — 牵挂文案建议（3 条，时段感知）+ 照片分析生成标题
2. **`utils/llm_parser.py`** — 食堂签到文本解析为结构化 JSON
3. **`services/risk_scoring.py`** — 风险评分 AI 分析（趋势判断 + 关注点 + 建议）
4. **`api/v1/agent.py` + `services/agent.py`** — "小溪" 智能助手，SSE 流式响应，7 个工具函数（查询不活跃老人、楼栋统计、老人状态、今日告警、未确认名单、确认活跃、周趋势），其中 `confirm_elder_active` 是唯一有写入的工具

所有 AI 调用在 API Key 未配置时自动降级为预设回复，系统不依赖 AI 也能正常运行。

### API 路由前缀映射

所有路由挂在 `/api/v1` 下，新增路由需在 `backend/app/api/v1/router.py` 注册：

| 域 | 后端前缀 | 前端页面目录 |
|---|---|---|
| 认证 | `/auth` | `frontend: pages/login/` |
| 用户 | `/users` | `frontend: pages/profile/` |
| 绑定关系 | `/relations` | `frontend: pages/bind/` |
| 牵挂内容 | `/moments` | `frontend: pages/send/`, `pages/view/` |
| 老人信息 | `/elders` | `frontend: pages/elder/` |
| 告警 | `/alerts` | `frontend: pages/alerts/` |
| 告警规则 | `/community/alert-rules` | `admin-frontend: views/elders/` |
| AI生成 | `/ai` | `frontend: pages/send/ai-suggest` |
| 海报 | `/poster` | `frontend: pages/send/poster-preview` |
| 文件上传 | `/upload` | — |
| 社区认证 | `/community/auth` | `admin-frontend: views/login/` |
| 社区管理 | `/community` | `admin-frontend: views/dashboard/`, `views/elders/` |
| 食堂 | `/community/canteen` | `admin-frontend: views/canteen/` |
| 社区活动 | `/community/events` | `admin-frontend: views/events/` |
| 智能助手 | `/community/agent/chat` | `admin-frontend: views/agent/` |
| 数据导出 | `/community/export` | `admin-frontend` |
| 邻里帮 | `/volunteer` | `frontend: pages/volunteer/`, `admin-frontend: views/volunteers/` |

---

## 目录结构约束

### 小程序前端 `frontend/src/`

- `api/` — 按域拆分的 HTTP 请求模块，所有请求通过 `request.js` 封装
- `components/` — 通用组件
- `composables/` — 可复用组合式函数
- `pages/` — 按功能域分目录（新增页面需同步更新 `frontend/pages.json`）
- `stores/` — Pinia stores，按域拆分
- `styles/` — 全局 SCSS（`variables.scss` 定义设计 token，`base.scss` 定义全局样式）

**规则：**
1. 每新增一个 `pages/xxx/` 必须同步创建对应的 `api/xxx.js` 和 `stores/xxx.js`
2. 页面文件单文件不超过 300 行
3. 老人端页面（`pages/view/`）字体 ≥ 36rpx，按钮触控区域 ≥ 96rpx

### 管理后台 `admin-frontend/src/`

- `api/` — Axios 请求模块（`request.js` 封装，含 access/refresh token 自动刷新）
- `views/` — 页面组件（路由在 `router/index.js` 定义，含 JWT auth guard）
- `stores/` — Pinia stores
- `styles/` — Tailwind 为主，少量 SCSS 覆盖
- 设计 token 在 `tailwind.config.js` 中定义（terracotta 主色系，与小程序暖橙不同）

### 后端 `backend/app/`

- `api/v1/` — 路由层（`router.py` 汇总所有子路由）
- `models/` — SQLAlchemy ORM，一文件一表
- `schemas/` — Pydantic 请求/响应 schema
- `services/` — 业务逻辑层
- `tasks/` — APScheduler 定时任务（`alert_checker.py`）
- `utils/` — 工具模块（`wechat.py` 微信 SDK、`llm_parser.py` AI 调用）
- `config.py` — 全局配置（`Settings` 类），从 `.env` 读取所有配置项

**规则：**
1. API 路由层只做参数校验和 HTTP 处理，业务逻辑下沉到 `services/`
2. 每个域完整四层：model → schema → service → api
3. 新增 model 必须在 `models/__init__.py` 中 import（Alembic 依赖此文件发现模型）
4. 新增路由必须在 `api/v1/router.py` 中 include

---

## 数据库

- 使用 SQLAlchemy 2.0 async（`Mapped`/`mapped_column` 风格） + asyncpg 驱动
- Alembic 异步迁移，`env.py` 从 `settings.DATABASE_URL` 读取连接串（`alembic.ini` 中 `sqlalchemy.url` 留空）
- 迁移文件在 `backend/alembic/versions/`（当前 8 个版本）
- 静态文件上传到 `backend/static/`，通过 `/static` 路径访问
- 19 个模型类（含 Volunteer 相关 3 个），`User` 表三角色共用（老人/子女/工作人员），`CommunityWorker` 单独存密码哈希

---

## 开发规范

### 小程序前端

- 使用 `<view>/<text>` 而非 `<div>/<span>`（uni-app 跨端要求）
- 使用 `uni.*` API 而非 `wx.*`
- 颜色和间距使用 SCSS 变量（`variables.scss`），禁止硬编码
- 状态管理通过 Pinia store，页面不直接调 api

### 管理后台

- 使用标准 HTML 元素（`<div>` 等），不受 uni-app 约束
- UI 框架为 Element Plus，样式用 Tailwind utility class
- API base URL 通过 `VITE_API_BASE_URL` 环境变量注入

### 后端

- 所有数据库操作使用 async/await
- 敏感配置通过 `.env` 注入（参照 `backend/.env.example`）
- 错误处理使用 FastAPI HTTPException
- Swagger/ReDoc 仅在 `DEBUG=true` 时暴露

---

## 设计系统

### 小程序（"温暖信笺"系）

色值定义在 `frontend/src/styles/variables.scss`，变量名以 `$c-` 前缀：

- 主色：`$c-primary: #C4745C`（赤陶暖棕）
- 强调色：`$c-accent: #D4A574`（暖沙金）
- 安全色：`$c-safe: #7BAE8E`（鼠尾草绿，已读/在线）
- 警告色：`$c-warn: #C97B6B`（柔玫瑰，未读/告警）
- 文字主色：`$c-text: #2D2016`（深棕）
- 边框：`$c-border: #EDE5DB`
- 圆角：卡片 24rpx，按钮 48rpx
- 老人端字体：正文 ≥ 36rpx，标题 ≥ 44rpx

### 管理后台（陶赤系）

- 主色：`#C44D3E`（terracotta 陶赤）
- 辅助色：`#6B8F71`（sage 灰绿）
- 强调色：`#D4A853`（amber 琥珀）
- 使用 Tailwind 配置中的 `terracotta`/`sage`/`amber`/`warm` 色阶

---

## 需要注意的非显而易见行为

1. **`get_current_worker` 会在内存中修改 ORM 对象** — 如果 JWT 包含 `current_community_id`，依赖注入会将 worker 的 `community_id` 改为该值（支持多社区切换），但不写入数据库。同一请求中如果 session flush 可能造成意外。
2. **风险评分对有无家属绑定使用不同权重** — 无家属时 `view_frequency` 权重降为 0，`canteen_attendance` 和 `last_active` 权重显著提高（见 `services/risk_scoring.py`）。
3. **`AccessLogMiddleware` 用 `verify_exp: False` 解码 JWT** — 仅为日志提取 uid，不做鉴权。
4. **Redis 已在 docker-compose 和 settings 中声明但代码中无任何使用**。
5. **生产 API 地址未配置** — 小程序 `api/config.js` 的 `PROD_API_BASE` 和管理后台 `.env.production` 的 `VITE_API_BASE_URL` 均为空，部署前必须设置。
6. **小程序 HTTP 客户端无自动 token 刷新** — 401 时直接跳转登录页；管理后台有 refresh token 轮换机制。
7. **海报生成依赖系统 CJK 字体** — `services/poster_generator.py` 按 macOS → Linux 顺序查找字体，服务器上需确保 CJK 字体可用。
8. **JWT_SECRET 生产必填** — `DEBUG=False` 时若 `JWT_SECRET` 未设置，`main.py` lifespan 阶段抛 `RuntimeError` 启动失败。
9. **CORS 在开发/生产环境行为不同** — `DEBUG=True` 允许所有来源和请求头；生产环境仅放行 `settings.CORS_ORIGINS`（默认 `localhost:5173, 5174`）且请求头限制为 `Authorization` 和 `Content-Type`。
10. **SecurityHeadersMiddleware** — 所有响应自动附加 `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy: strict-origin-when-cross-origin`。
11. **健康检查含功能探测** — `/health` 返回 `features.ai`（AI Key 是否配置）和 `features.wechat`（微信凭据是否配置）布尔值。
12. **老人 ABC 分级** — A 级（独居/高龄/健康风险高）每日关注、B 级（基本独居/有一定自理能力）每周关注、C 级（有同住家人/相对健康）每月关注。分级影响告警阈值和静默检测频率。
