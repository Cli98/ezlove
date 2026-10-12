# EZLove 社区管理看板设计

**日期**: 2026-06-19  
**状态**: Draft  
**作者**: QoderWork + 用户协作  

## 1. 背景与目标

EZLove（易挂念）当前版本是一个完整的子女-老人牵挂系统，核心是"发关怀动态 → 老人查看 → 已读未读追踪 → 超时预警"闭环。技术栈为 uni-app（微信小程序）+ FastAPI + PostgreSQL + Redis。

本设计的目标是在保留现有家庭端功能的基础上，扩展**社区管理**能力，帮助社区工作人员对辖区老人进行分级管理和日常监控。

### 1.1 老人分级标准

- **A 级**: 没有自理能力，可能有一定认知障碍
- **B 级**: 独居，儿女不在身边，但认知正常
- **C 级**: 老两口在一起，岁数较小，有一定照顾 A 级老人的能力

### 1.2 产品初心

帮助社区工作人员管理老人的应急状况、跌倒状况、在不在家等信息，让社区看护人员更好管理。

### 1.3 食堂数据

社区食堂就餐数据是老人活跃度的强信号。工作人员以非结构化方式录入（Excel 或自由文本），系统通过 LLM 解析为结构化数据。A 级老人未就餐自动触发 urgent 预警。

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    用户层（三个角色）                         │
├──────────────────┬──────────────────┬───────────────────────┤
│  子女/亲属端     │  长辈端          │  社区工作人员端        │
│  (微信小程序)    │  (微信小程序)    │  (H5 管理后台)        │
│  - 发关怀动态    │  - 查看动态      │  - 辖区老人看板      │
│  - 查看已读状态  │  - 已读确认      │  - 老人档案+分级     │
│  - 接收预警      │  - 表情回应      │  - 活跃状态监控      │
│                  │                  │  - 食堂数据管理      │
│                  │                  │  - 事件记录          │
└──────────────────┴──────────────────┴───────────────────────┘
                            │
                            │  HTTPS
                            ▼
              ┌─────────────────────────────┐
              │   FastAPI 后端（统一）       │
              │   /api/v1/*  现有家庭端 API  │
              │   /api/v1/community/* 新增   │
              └─────────────┬───────────────┘
                            │
              ┌─────────────┼───────────────┐
              │             │               │
              ▼             ▼               ▼
         PostgreSQL     Redis         APScheduler
         (现有7表       (缓存+         (定时任务：
          +新增5表)      会话)          预警检查)
```

### 2.1 核心设计原则

1. **后端统一，前端分离**: 社区端和家庭端共享同一个 FastAPI 后端，但社区端是独立的 H5 项目（Vue 3 + Element Plus），不混入现有 uni-app 小程序代码
2. **数据打通**: 社区端能读取家庭端的 care_moments 和 view_events，作为判断老人活跃度的数据源
3. **权限隔离**: 社区工作人员只能看到自己辖区的老人，不能看到其他社区的数据
4. **增量迭代**: MVP 只做看板和档案管理，工单系统、应急通知等后续迭代

## 3. 数据模型

在现有 7 张表的基础上，新增以下 5 张表。users 表新增 role='worker'。

### 3.1 communities — 社区/小区

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| name | VARCHAR(128) | 社区名称 |
| address | VARCHAR(256) | 地址 |
| created_at | TIMESTAMP | 创建时间 |

### 3.2 community_workers — 社区工作人员

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| user_id | UUID FK users | 关联 users 表 |
| community_id | UUID FK communities | 所属社区 |
| name | VARCHAR(64) | 姓名 |
| phone | VARCHAR(20) | 手机号（登录凭据） |
| role_label | VARCHAR(32) | 角色标签（网格员/站长/护理员） |
| password_hash | VARCHAR(128) | 密码哈希 |
| created_at | TIMESTAMP | 创建时间 |

### 3.3 community_elders — 社区-老人关联（核心表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| community_id | UUID FK communities | 所属社区 |
| elder_id | UUID FK users | 关联老人用户 |
| care_level | ENUM('A','B','C') | 分级 |
| address | VARCHAR(128) | 楼栋/门牌号 |
| emergency_contact_name | VARCHAR(64) | 紧急联系人姓名 |
| emergency_contact_phone | VARCHAR(20) | 紧急联系人电话 |
| health_notes | TEXT | 健康状况备注 |
| assigned_worker_id | UUID FK community_workers | 负责的网格员（可空） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 3.4 canteen_records — 食堂就餐记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| community_id | UUID FK communities | 所属社区 |
| raw_text | TEXT | 工作人员录入的原始文本 |
| source_format | ENUM('text','excel','other') | 输入源格式 |
| parsed_data | JSONB | LLM 解析后的结构化数据 |
| parsed_at | TIMESTAMP | LLM 解析完成时间 |
| parse_status | ENUM('pending','success','failed') | 解析状态 |
| recorded_by | UUID FK community_workers | 录入人 |
| created_at | TIMESTAMP | 创建时间 |

**parsed_data JSON 格式**:
```json
{
  "date": "2026-06-19",
  "meal_type": "breakfast|lunch|dinner",
  "attendees": [
    {"elder_id": "uuid", "elder_name": "姓名", "present": true, "notes": "备注"},
    {"elder_id": "uuid", "elder_name": "姓名", "present": false, "notes": "未就餐"}
  ],
  "parse_notes": "解析说明"
}
```

### 3.5 community_events — 社区事件

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 主键 |
| community_id | UUID FK communities | 所属社区 |
| elder_id | UUID FK users | 关联老人 |
| event_type | ENUM('fall','absent','emergency','visit','other') | 事件类型 |
| source | ENUM('canteen','alert','manual') | 事件来源 |
| description | TEXT | 事件描述 |
| severity | ENUM('info','warning','urgent') | 严重程度 |
| is_resolved | BOOLEAN | 是否已处理 |
| resolved_by | UUID FK community_workers | 处理人（可空） |
| resolved_at | TIMESTAMP | 处理时间 |
| created_at | TIMESTAMP | 创建时间 |


## 4. API 设计

### 4.1 认证与社区管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/community/auth/login` | 社区工作人员登录（手机号+密码，返回 JWT） |
| GET | `/api/v1/community/dashboard` | 看板数据 |
| GET | `/api/v1/community/elders` | 辖区老人列表（支持 care_level 筛选、搜索） |
| POST | `/api/v1/community/elders` | 录入老人档案 + 分级 |
| PUT | `/api/v1/community/elders/{id}` | 修改档案/调整分级 |
| GET | `/api/v1/community/elders/{id}` | 老人详情 |

### 4.2 食堂数据

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/community/canteen/submit` | 提交食堂数据（文本或 Excel），立即触发 LLM 解析，返回 record id 和 parse_status |
| GET | `/api/v1/community/canteen/records` | 食堂记录列表 |
| GET | `/api/v1/community/canteen/records/{id}` | 单条记录详情（含解析结果，用于轮询 LLM 解析进度） |
| PUT | `/api/v1/community/canteen/records/{id}` | 人工修正 LLM 解析结果 |

### 4.3 事件

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/community/events` | 事件列表（支持 severity、type、is_resolved 筛选） |
| POST | `/api/v1/community/events` | 手动创建事件 |
| PUT | `/api/v1/community/events/{id}/resolve` | 标记事件已处理 |

### 4.4 自动事件生成逻辑

- 食堂记录中 `present=false` 的 **A 级**老人 → 自动创建 `absent` 事件，`severity=urgent`
- 食堂记录中 `present=false` 的 **B 级**老人 → 自动创建 `absent` 事件，`severity=warning`
- 家庭端超时未读预警（已有 alert）→ 同步生成 community_event，severity 根据 care_level 调整

## 5. LLM 解析策略

### 5.1 输入处理流程

```
输入源（两种）：
  ├── Excel 文件 (.xlsx)
  │     ↓ openpyxl 读取 → 提取所有 sheet 的文本内容
  │     ↓ 转为纯文本（保留行列关系）
  │
  └── 自由文本
        ↓ 直接传入

        ↓ 统一进入 LLM 解析层
        ▼
```

### 5.2 System Prompt 策略

给 LLM 的上下文包含：
- 该社区的完整老人名单（含 name、id、care_level）
- 期望的输出 JSON 格式
- 解析规则（如名字模糊匹配、缺勤判断标准）

### 5.3 后处理

1. 验证 `elder_id` 是否在名单中（防止 LLM 编造）
2. 未匹配的名字 → 标记为 pending，等工作人员确认
3. 存入 `canteen_records.parsed_data`
4. 自动触发缺勤事件生成

### 5.4 降级策略

| 场景 | 处理方式 |
|------|---------|
| LLM API 超时/不可用 | 降级为手动表单录入 |
| LLM 返回非法 JSON | 重试一次，仍失败则降级 |
| LLM 识别出名单外的老人 | 标记"待确认"，高亮显示 |
| Excel 格式无法读取 | 返回错误提示 |
| LLM 无法判断是否就餐 | present 设为 null，标记"需人工确认" |

### 5.5 模型配置

- 复用现有 Anthropic Claude API（项目中已集成）
- 使用 claude-haiku-4-5，成本低、速度快
- LLM API key 和 URL 后续提供，代码中留占位符
- 离线降级：API key 未配置时使用手动表单模式

## 6. H5 前端页面设计

### 6.1 技术栈

- Vue 3 (Composition API + Vite)
- Element Plus (组件库)
- Pinia (状态管理)
- Vue Router
- Axios (HTTP 请求)

### 6.2 四个核心页面

**页面 1: 看板页（首页）**
- 顶部统计卡片：辖区总人数 / A级 / B级 / C级 / 今日活跃率
- 今日待处理事件列表（未关闭的 urgent/warning 事件）
- 今日食堂就餐情况概览（到餐人数 / 缺勤名单）
- 老人活跃热力图：按楼栋/片区分组的网格视图，每个老人显示为一个小方块，颜色表示今日状态（绿色=已读或已就餐，灰色=未活跃，红色=A级未活跃），鼠标悬浮显示姓名和分级

**页面 2: 老人档案页**
- 表格列表：姓名、年龄、分级、楼栋、负责网格员、今日状态
- 支持按分级筛选、按姓名搜索
- 点击行进入老人详情页：完整档案 + 家庭端已读日历 + 食堂出勤记录 + 事件时间线

**页面 3: 食堂管理页**
- 文本输入框 + Excel 上传按钮
- "解析"按钮 → 调用 LLM → 展示解析结果表格（可人工修正）
- 历史记录列表，按日期倒序

**页面 4: 事件中心页**
- 事件列表，按 severity 颜色标记（红/黄/蓝）
- 筛选：事件类型、严重程度、是否已处理
- 点击事件可查看详情、标记已处理、添加处理备注

### 6.3 登录方式

社区工作人员用手机号+密码登录（不用微信），在电脑浏览器和手机上都能使用。

## 7. 错误处理

### 7.1 API 统一响应格式

```json
{
  "code": 200,
  "data": {},
  "message": "success"
}
```

### 7.2 HTTP 状态码

- 400: 参数校验失败，返回具体字段错误
- 401: JWT 过期或无效
- 403: 权限不足（如工人查看非辖区老人）
- 404: 资源不存在
- 500: 服务端错误，记录日志，不暴露内部细节

## 8. 实施阶段

### 8.1 阶段一：MVP（本阶段）

包含：
- 数据库新增 5 张表 + users 表 role 字段扩展
- 社区工作人员登录（手机号+密码 JWT）
- 老人档案录入 + A/B/C 分级
- 食堂文本/Excel 上传 + LLM 解析
- 看板页（统计卡片 + 今日待处理事件 + 食堂概览 + 活跃列表 + 热力图）
- 老人详情页（档案 + 家庭端已读数据 + 食堂出勤）
- 事件列表（自动从食堂缺勤 + 家庭端预警生成）
- 权限隔离（工人只看自己辖区）

不包含：
- 社区通知/应急广播功能
- 工单流转完整流程
- 小程序端社区外勤模式
- 多社区管理（MVP 只支持一个社区）
- 语音录入/语音响应

### 8.2 阶段二：增强（MVP 验证通过后）

- 工单系统完整流程（上报→确认→处理→关闭）
- 社区通知功能（按分级定向通知）
- 30 天活动日历 + 趋势分析图表
- 多社区支持 + 区域级管理员角色
- 微信订阅消息推送

### 8.3 阶段三：智能化

- 系统根据行为数据建议分级调整
- 异常模式自动识别（连续缺勤 + 未读 → 自动升级预警）
- C 级老人协助照顾 A 级老人的匹配推荐
- 数据分析报表导出

### 8.4 MVP 技术实施顺序

1. 数据库迁移 — 新增 5 张表 + users 表 role 字段扩展
2. 后端 API — 社区认证 + 档案管理 + 食堂解析 + 事件生成 + 看板数据
3. H5 前端项目搭建 — Vue 3 + Element Plus + 路由 + 状态管理
4. 前端页面开发 — 登录 → 看板 → 老人档案 → 食堂管理 → 事件中心
5. 测试与验证 — 单元/集成测试 + 页面联调
6. 部署 — Docker Compose 扩展，新增 H5 容器

## 9. 部署

### 9.1 Docker Compose 扩展

在现有 docker-compose.yml 中新增：
- `h5-frontend` 容器：Nginx 托管 Vue H5 构建产物
- 共享同一个 backend 网络和数据库

### 9.2 域名与路由

- 现有 API 域名: `yuxilab.cn/ezlove/api/v1`
- 社区 H5 前端: `yuxilab.cn/ezlove-admin/` 或独立子域名
- API 路由前缀: `/api/v1/community/*`

## 10. 后续待确认事项

- LLM API key 和 endpoint（用户后续提供）
- 社区食堂实际数据样本（用于优化 LLM prompt）
- 热力图的分组维度（按楼栋还是按网格员负责区域）
- 是否需要对接社区现有系统（如户籍系统）
