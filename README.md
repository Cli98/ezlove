<h1 align="center">EZLove 易挂念</h1>

<p align="center">让牵挂被看见 —— 连接家庭与社区的独居老人关爱平台</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Vue_3-4FC08D?style=flat-square&logo=vue.js&logoColor=white" alt="Vue 3" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/uni--app-2B9939?style=flat-square&logo=wechat&logoColor=white" alt="uni-app" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=flat-square" alt="MIT License" />
</p>

---

## 项目简介

EZLove（易挂念）是一个面向独居老人家庭的社区关爱平台。子女通过微信小程序向父母发送日常牵挂内容（文字、图片、海报），老人点击即可查看，系统自动追踪已读状态——当老人长时间未查看时，及时提醒子女关注。同时，社区工作人员通过 Web 管理后台掌握辖区老人整体状况，管理食堂、活动、志愿者等社区服务资源。

核心理念：**牵挂而非监控，关心而非追踪**。老人的每一次打开，就是一句"我很好"。

## 核心功能

### 子女端（微信小程序）

- **发送牵挂** — 文字 + 图片组合，一键发送给父母
- **AI 文案建议** — AI 生成暖心文案，子女选择确认后发送
- **海报生成** — 将牵挂内容生成精美海报卡片
- **已读追踪** — 实时查看父母是否已阅读，超时未读自动提醒

### 老人端（微信小程序）

- **查看牵挂** — 点击微信聊天中的小程序卡片即可查看，零学习成本
- **一键报平安** — 简单操作让子女放心
- **大字体无障碍** — 正文 >= 36rpx，按钮触控区 >= 96rpx，高对比度单列布局
- **表情回应** — 用表情表达对子女关心的回应

### 社区管理端（Web 后台）

- **社区看板** — 老人分级统计（A/B/C）、活跃概览、关键指标一目了然
- **老人档案管理** — A/B/C 三级分类管理，支持详细信息维护
- **食堂菜单** — 文本/Excel 录入 + AI 智能解析，管理社区食堂就餐数据
- **事件中心** — 自动预警事件 + 手动记录 + 处理流转闭环
- **志愿者管理** — 志愿者信息登记与服务记录
- **AI 智能助手** — 辅助数据录入与内容解析

### 老人分级标准

| 级别 | 描述 |
|------|------|
| **A 级** | 无自理能力，可能有认知障碍，需重点关注 |
| **B 级** | 独居，儿女不在身边，认知正常，需定期关怀 |
| **C 级** | 老两口在一起，可协助照顾 A 级老人 |

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  微信小程序    │  │  微信小程序    │  │   Web 管理后台        │   │
│  │  （子女端）    │  │  （老人端）    │  │   （社区工作人员）     │   │
│  │  uni-app      │  │  uni-app      │  │   Vue 3 + Element    │   │
│  │  Vue 3        │  │  Vue 3        │  │   Tailwind CSS       │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
└─────────┼──────────────────┼─────────────────────┼───────────────┘
          │                  │                     │
          └──────────────────┼─────────────────────┘
                             │ JWT Auth
                    ┌────────▼────────┐
                    │    FastAPI       │
                    │    后端 API      │
                    │   /api/v1/*     │
                    ├─────────────────┤
                    │  SQLAlchemy 2.0 │
                    │  APScheduler    │
                    │  Anthropic AI   │
                    └───┬─────────┬───┘
                        │         │
                 ┌──────▼──┐  ┌──▼──────┐
                 │ Postgres │  │  Redis   │
                 │   16     │  │   7      │
                 └──────────┘  └──────────┘
```

### 技术栈一览

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI + SQLAlchemy 2.0 (async) + asyncpg |
| 数据库 | PostgreSQL 16 + Redis 7 |
| 小程序前端 | uni-app + Vue 3 Composition API + Vite + Pinia + uview-plus |
| 管理后台前端 | Vue 3 + Element Plus + Tailwind CSS + Vue Router + Pinia |
| AI 服务 | Anthropic Claude API |
| 部署 | Docker Compose + 阿里云 ECS |
| 数据库迁移 | Alembic (async) |
| 定时任务 | APScheduler |

## 快速开始

### 前置要求

- Docker & Docker Compose
- Node.js 18+（前端本地开发）
- Python 3.10+（后端本地开发）

### 一键启动（推荐）

```bash
# 克隆项目
git clone https://github.com/your-org/ezlove.git && cd ezlove

# 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env，至少填写 JWT_SECRET（必填）

# 启动全部服务（数据库 + Redis + 后端 + 管理后台）
docker compose up -d

# 运行数据库迁移
docker compose exec backend alembic upgrade head

# 初始化管理员账号（首次运行）
docker compose exec backend python seed_community.py --password YOUR_PASSWORD

# 初始化老人示例数据（可选）
docker compose exec backend python seed_elders.py
```

启动后访问：
- 后端 API：http://localhost:8001
- 管理后台：http://localhost:5174
- Swagger 文档（需 `DEBUG=true`）：http://localhost:8001/docs

### 本地开发模式

```bash
# 1. 启动基础设施
docker compose up -d db redis

# 2. 启动后端
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8001

# 3. 启动管理后台前端
cd admin-frontend
npm install && npm run dev    # localhost:5174

# 4. 启动小程序前端
cd frontend
npm install && npm run dev:h5  # localhost:5173（H5 调试）
```

## 项目结构

```
ezlove/
├── frontend/                  # 微信小程序（uni-app + Vue 3）
│   └── src/
│       ├── api/               # 按域拆分的 HTTP 请求模块
│       ├── components/        # 通用组件
│       ├── composables/       # 可复用组合式函数
│       ├── pages/             # 页面（按功能域分目录）
│       ├── stores/            # Pinia 状态管理
│       └── styles/            # 全局 SCSS
│
├── admin-frontend/            # 社区管理后台（Vue 3 + Element Plus）
│   └── src/
│       ├── api/               # Axios 请求模块（含 token 自动刷新）
│       ├── router/            # Vue Router 路由配置
│       ├── stores/            # Pinia 状态管理
│       ├── views/             # 页面组件
│       └── styles/            # Tailwind + SCSS
│
├── backend/                   # 后端 API（FastAPI）
│   ├── app/
│   │   ├── api/v1/            # 路由层
│   │   ├── models/            # SQLAlchemy ORM 模型
│   │   ├── schemas/           # Pydantic 请求/响应 Schema
│   │   ├── services/          # 业务逻辑层
│   │   ├── tasks/             # APScheduler 定时任务
│   │   └── utils/             # 工具模块（微信 SDK、AI 等）
│   ├── alembic/               # 数据库迁移
│   ├── static/                # 静态文件（上传资源）
│   └── tests/                 # 测试
│
├── docs/                      # 项目文档
├── docker-compose.yml         # 容器编排
├── AGENTS.md                  # AI 编码助手指引
└── DESIGN.md                  # 设计文档
```

## 环境变量

后端配置通过 `backend/.env` 文件管理，参考 `backend/.env.example`：

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | 是 | — | PostgreSQL 连接串，格式：`postgresql+asyncpg://user:pass@host:port/db` |
| `JWT_SECRET` | 是 | — | JWT 签名密钥，生成方式：`python -c "import secrets; print(secrets.token_hex(32))"` |
| `REDIS_URL` | 否 | `redis://localhost:6380/0` | Redis 连接地址 |
| `DEBUG` | 否 | `false` | 调试模式，开启后暴露 Swagger/ReDoc 文档 |
| `WECHAT_APP_ID` | 否 | — | 微信小程序 AppID，家庭端功能需要 |
| `WECHAT_APP_SECRET` | 否 | — | 微信小程序 AppSecret，家庭端功能需要 |
| `ANTHROPIC_API_KEY` | 否 | — | Anthropic API Key，启用 AI 文案建议和食堂数据解析 |

> **注意**：Docker Compose 环境下，数据库端口映射为 5433，Redis 端口映射为 6380，避免与其他项目冲突。

## 开发指南

### 小程序前端

```bash
cd frontend
npm run dev:h5           # H5 开发模式（localhost:5173）
npm run dev:mp-weixin    # 微信小程序开发模式（微信开发者工具）
npm run build:h5         # H5 生产构建
npm run build:mp-weixin  # 微信小程序生产构建
```

- 使用 `<view>/<text>` 而非 `<div>/<span>`（uni-app 跨端要求）
- 使用 `uni.*` API 而非 `wx.*`
- 老人端页面字体 >= 36rpx，按钮触控区域 >= 96rpx

### 管理后台前端

```bash
cd admin-frontend
npm run dev              # 开发模式（localhost:5174，自动代理到后端）
npm run build            # 生产构建
```

- UI 框架为 Element Plus，样式以 Tailwind utility class 为主
- API base URL 通过 `VITE_API_BASE_URL` 环境变量配置

### 后端

```bash
cd backend
uvicorn app.main:app --reload              # 开发模式（localhost:8001）
alembic upgrade head                       # 执行数据库迁移
alembic revision --autogenerate -m "desc"  # 生成迁移脚本
python seed_community.py                   # 初始化社区 + 管理员账号
python seed_elders.py                      # 初始化老人示例数据
```

- API 路由层只做参数校验和 HTTP 处理，业务逻辑在 `services/` 中
- 每个域完整四层：model -> schema -> service -> api
- 新增 model 须在 `models/__init__.py` 中 import
- 新增路由须在 `api/v1/router.py` 中注册

## 截图展示

<!-- TODO: add screenshots -->

| 子女端 | 老人端 | 管理后台 |
|--------|--------|----------|
| 待补充 | 待补充 | 待补充 |

## 参与贡献

我们欢迎各种形式的贡献：

1. **Fork** 本仓库并创建你的特性分支（`git checkout -b feature/amazing-feature`）
2. 提交你的更改（`git commit -m 'feat: add amazing feature'`）
3. 推送到分支（`git push origin feature/amazing-feature`）
4. 发起 **Pull Request**

贡献前请注意：
- 代码风格与现有代码保持一致
- 新功能请附带相应的测试
- commit message 使用英文，遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范
- PR 描述清楚说明改动内容和目的

## License

本项目基于 [MIT License](LICENSE) 开源。
