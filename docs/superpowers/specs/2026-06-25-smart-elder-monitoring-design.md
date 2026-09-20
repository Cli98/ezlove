# EZLove 智能老人守护系统 — 设计规格

> **状态：** 已批准  
> **日期：** 2026-06-25  
> **范围：** 分级告警自动分派 + AI 风险评分 + 老人事件时间线  

## 1. 背景与目标

### 现状问题

当前系统对老人的状态感知过于单一——主要依赖"子女发内容 → 老人是否查看"这一条信号线，辅以手动录入的食堂就餐数据。具体局限：

- **被动感知**：系统不会主动获取老人状态，完全依赖老人的被动行为
- **信号单一**：仅有 view_events 和 canteen_records 两个数据源
- **事后响应慢**：发现异常后没有自动分派和升级机制，响应链条不完整
- **缺乏综合判断**：各维度数据孤立，无法形成老人的整体风险画像

### 目标

在不引入硬件依赖的前提下，通过纯软件方案实现：

1. **分级告警自动分派**：根据老人 A/B/C 等级自动设定告警阈值、分派网格员、限时升级
2. **AI 风险评分**：综合多维信号计算实时风险分数，提供 AI 趋势分析
3. **事件时间线**：汇聚所有数据源为统一的老人生活轨迹，支持管理后台和子女端查看

---

## 2. 功能一：分级告警 + 自动分派

### 2.1 告警规则引擎

根据老人 care_level 设定不同的超时阈值：

| 检测维度 | A级（高风险） | B级（中风险） | C级（低风险） |
|---------|-------------|-------------|-------------|
| 牵挂未读超时 | 6 小时 | 12 小时 | 24 小时 |
| 食堂连续缺勤 | 1 餐 | 2 餐 | 3 餐 |
| 多维无信号 | 12 小时 | 24 小时 | 48 小时 |

"多维无信号"指所有数据源（view_events + canteen + community_events）均无该老人的活动记录。

告警规则可配置，每个社区可自定义阈值（通过 `alert_rules` 表存储）。

### 2.2 自动分派流程

```
超时触发
  → 创建告警（severity 根据等级自动设定：A=urgent, B=warning, C=info）
  → 分派给该老人的 assigned_worker（网格员）
  → 网格员收到通知（小程序订阅消息/模板消息）
  
── 30 分钟内处理 → 关闭告警，记录处理结果
── 30 分钟未响应 → 升级到 level 1
  → 通知社区主管（role_label="主管" 的 worker）
  
── 再过 1 小时仍未处理 → 升级到 level 2
  → 通知家属（子女端推送告警）
```

### 2.3 数据模型变更

**alerts 表新增字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| assigned_worker_id | UUID, FK → community_workers.id | 分派的网格员 |
| escalation_level | Integer, default 0 | 当前升级级别（0=初始, 1=主管, 2=家属） |
| response_deadline | DateTime | 响应截止时间 |
| responded_at | DateTime, nullable | 实际响应时间 |
| response_note | Text, nullable | 处理说明 |
| trigger_rule | String(32) | 触发规则（unread/canteen_absent/no_signal） |

**新增 alert_rules 表：**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID, PK | |
| community_id | UUID, FK → communities.id | |
| care_level | String(1) | A/B/C |
| rule_type | String(32) | unread_timeout/canteen_absent/no_signal |
| threshold_value | Integer | 阈值（小时或餐数） |
| severity | String(16) | 自动设定的严重级别 |
| escalation_minutes | Integer | 升级超时时间（分钟） |
| is_active | Boolean, default True | |

### 2.4 后端实现

- 改造 `tasks/alert_checker.py`：从简单超时检测升级为多维度规则引擎
  - 每次运行时读取 alert_rules 配置
  - 同时检查 view_events、canteen_records、community_events 三个维度
  - 按老人 care_level 匹配对应规则
- 新增 `services/alert_dispatcher.py`：自动分派 + 升级逻辑
  - `dispatch_alert()`：创建告警时自动关联 assigned_worker，设定 response_deadline
  - `check_escalations()`：APScheduler 每 10 分钟运行，扫描超期未响应告警并升级
- 新增 API：
  - `POST /api/v1/community/alerts/{id}/respond`：网格员响应告警
  - `GET /api/v1/community/alerts/pending`：获取当前待处理告警列表
  - `GET /api/v1/community/alert-rules`：获取告警规则配置
  - `PUT /api/v1/community/alert-rules`：更新告警规则

---

## 3. 功能二：AI 风险评分系统

### 3.1 评分模型

综合多维信号计算 0-100 的风险分数：

| 维度 | 权重 | 得分逻辑 |
|------|------|---------|
| 牵挂查看频率 | 25% | 最近 7 天查看率：100%→0分, 0%→100分，线性插值 |
| 食堂出勤频率 | 20% | 最近 7 天出勤率：100%→0分, 0%→100分，线性插值 |
| 最后活跃距今 | 25% | 0-6h→0分, 6-12h→30分, 12-24h→60分, >24h→100分 |
| 近期告警密度 | 15% | 过去 30 天告警次数：0→0分, 1-2→30分, 3-5→60分, >5→100分 |
| 基础风险等级 | 15% | A→60分, B→30分, C→10分 |

### 3.2 风险等级映射

| 分数范围 | 等级 | 颜色 | 建议行动 |
|---------|------|------|---------|
| 0-30 | 正常 | 绿色 | 常规关注 |
| 31-60 | 关注 | 黄色 | 建议近期走访 |
| 61-80 | 预警 | 橙色 | 需要在 24 小时内确认状况 |
| 81-100 | 高危 | 红色 | 立即处理 |

### 3.3 AI 趋势分析

除规则引擎评分外，接入 Claude API 做风险趋势分析：

**输入：** 某老人最近 7 天的全部数据（查看记录、食堂出勤、事件记录、告警历史）

**输出：** JSON 格式
```json
{
  "summary": "张大爷近 3 天未查看任何牵挂内容，且连续 2 天未到食堂就餐。",
  "trend": "deteriorating",  // improving / stable / deteriorating
  "concern_points": ["连续未读牵挂", "食堂缺勤"],
  "suggested_action": "建议立即安排网格员上门走访，优先确认老人身体状况。",
  "confidence": 0.85
}
```

AI 分析在以下时机触发：
- 风险分数从一个等级跳到更高等级时
- 网格员打开老人详情页时（按需调用）
- 每日定时为所有 A 级老人生成分析报告

### 3.4 数据模型

**community_elders 表新增字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| risk_score | Integer, default 0 | 当前风险分数（0-100） |
| risk_level | String(16), default "normal" | 风险等级（normal/attention/warning/critical） |
| risk_calculated_at | DateTime, nullable | 最后计算时间 |
| risk_details | JSONB, nullable | 各维度子分详情 |

### 3.5 后端实现

- 新增 `services/risk_scoring.py`：
  - `calculate_risk_score(elder_id)`：计算单个老人风险分数
  - `batch_calculate_risk_scores(community_id)`：批量计算整个社区
  - `get_ai_risk_analysis(elder_id)`：调用 Claude API 生成趋势分析
- APScheduler 新增任务：每小时运行 `batch_calculate_risk_scores`
- 新增 API：
  - `GET /api/v1/community/elders/{id}/risk`：获取风险详情 + AI 分析
  - `GET /api/v1/community/risk-ranking`：风险排行榜（按分数降序）

---

## 4. 功能三：老人事件时间线

### 4.1 时间线事件类型

| 事件类型 | 标签 | 数据来源 | 描述 |
|---------|------|---------|------|
| care_viewed | 查看牵挂 | view_events | 老人查看了子女发来的牵挂内容 |
| care_sent | 收到牵挂 | care_moments | 子女发送了新的牵挂内容 |
| canteen_present | 食堂就餐 | canteen_records.parsed_data | 老人在食堂就餐 |
| canteen_absent | 食堂缺勤 | canteen_records.parsed_data | 老人未到食堂 |
| alert_created | 告警触发 | alerts | 系统生成告警 |
| alert_resolved | 告警处理 | alerts | 告警被处理 |
| event_manual | 人工上报 | community_events | 工作人员手动上报事件 |
| risk_change | 风险变化 | community_elders.risk_score | 风险等级发生变化 |
| worker_visit | 上门走访 | community_events (type=visit) | 网格员上门走访记录 |

### 4.2 统一时间线接口

```
GET /api/v1/community/elders/{elder_id}/timeline
  ?days=7          // 查询天数，默认 7
  &types=all       // 事件类型过滤，逗号分隔或 all
  &page=1          // 分页
  &page_size=50    // 每页条数
```

响应格式：
```json
{
  "elder_id": "uuid",
  "elder_name": "张大爷",
  "period": {"start": "2026-06-18", "end": "2026-06-25"},
  "summary": {
    "total_events": 23,
    "view_count": 8,
    "canteen_present": 5,
    "canteen_absent": 2,
    "alerts": 1
  },
  "events": [
    {
      "id": "uuid",
      "type": "canteen_absent",
      "time": "2026-06-25T12:30:00+08:00",
      "label": "食堂缺勤",
      "description": "午餐未到食堂就餐",
      "severity": "warning",
      "source_id": "uuid",
      "metadata": {}
    }
  ]
}
```

### 4.3 后端实现

- 新增 `services/timeline.py`：
  - `get_elder_timeline(elder_id, days, types)`：从多张表聚合数据，统一格式和排序
  - 各数据源独立查询函数，避免 JOIN 过于复杂
- 新增 `api/v1/timeline.py`：
  - `GET /api/v1/community/elders/{elder_id}/timeline`

### 4.4 前端展示

**管理后台 — 老人详情页增强：**
- 顶部：风险仪表盘（各维度子分雷达图/条形图）
- 中部：时间线列表（按日期分组，每个事件展示图标+时间+描述）
- 底部：历史统计图表（过去 30 天活跃度趋势）

**小程序 — 子女端 elder/status 页面增强：**
- 增加简化版时间线（仅展示最近 3 天的查看记录和重要事件）
- 让子女直观感受到"系统在守护老人"

---

## 5. 整体架构变化

### 5.1 新增后端模块

```
backend/app/
  services/
    risk_scoring.py       # 风险评分计算
    alert_dispatcher.py   # 告警分派+升级
    timeline.py           # 事件时间线聚合
  api/v1/
    timeline.py           # 时间线 API
  tasks/
    alert_checker.py      # 改造：多维度规则引擎
    risk_calculator.py    # 新增：定时风险评分
```

### 5.2 数据库迁移

- alerts 表：新增 6 个字段
- community_elders 表：新增 4 个字段
- 新增 alert_rules 表

### 5.3 定时任务

| 任务 | 周期 | 功能 |
|------|------|------|
| alert_checker | 每 5 分钟 | 多维度告警检测 + 自动分派 |
| escalation_checker | 每 10 分钟 | 检查未响应告警并升级 |
| risk_calculator | 每小时 | 批量重算所有老人风险分数 |
| daily_risk_report | 每日 8:00 | 为 A 级老人生成 AI 风险分析报告 |

---

## 6. 竞赛叙事线

这三个功能形成一个完整的智能守护故事：

1. **实时感知**（风险评分）：系统实时综合多维数据，为每个老人计算风险分数
2. **智能预警**（分级告警）：风险超过阈值自动触发告警，按老人等级精准分派
3. **闭环响应**（自动分派+升级）：告警分派给网格员，限时未响应自动升级
4. **全景追溯**（事件时间线）：所有事件形成时间线，可追溯、可分析、可改进
5. **AI 赋能**（趋势分析）：AI 不仅打分，还能给出自然语言的风险判断和行动建议

一句话卖点：**"从发现异常到处理闭环，全程 AI 驱动，让每一位独居老人都在社区的守护网中。"**
