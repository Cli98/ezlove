# autoloop 快速上手

一句话需求驱动的自进化研发闭环：九阶段流水线 × 三模型评分门（95 分准入）× 自进化复盘。本目录当前部署于 EZLove 项目（小程序 + 管理后台 + FastAPI 后端），但技能本身与项目解耦，可整体复制到任何仓库复用。

## 安装与复用

技能已打包为发行包 `autoloop-skill-v1.0.0.zip`，可直接安装到其他项目：

```bash
unzip autoloop-skill-v1.0.0.zip -d <目标项目>/.qoder/skills/
```

解压即得到 `.qoder/skills/autoloop/`，仅依赖 Python 3.9+ 标准库。安装后请把运行时状态目录 `.autoloop/` 加入目标项目 `.gitignore`（含密钥的 `config/models.json` 不在包内）。默认零配置即用（local 模式）；需真实模型评审则按下方「三步配置」走 api 模式。

## 前置条件

- Python 3.9+（引擎脚本运行环境）
- git（run 分支隔离）
- （可选）三个评审模型的 API key——不配则自动走 local 模式

## 三步配置

**第 1 步：配置三模型（可选，推荐）**

```bash
cd .qoder/skills/autoloop/config
cp models.json.example models.json
# 编辑 models.json：为 A（产品专家）/ B（研发专家）/ C（质量仲裁）填 provider、model、api_key_env
```

**第 2 步：注入 API key（环境变量，不落盘）**

```bash
export AUTOLOOP_EVAL_A_KEY="sk-..."   # 评审 A
export AUTOLOOP_EVAL_B_KEY="sk-..."   # 评审 B
export AUTOLOOP_EVAL_C_KEY="sk-..."   # 评审 C
```

**第 3 步（不配 API 的替代路径）：直接用 local 模式**

跳过上面两步即可。gate 时脚本自动检测 `config/models.json` 缺失，生成 3 个评审提示词文件，由 Agent 派遣 3 个 persona 子代理独立评分回填。离线可用，评分独立性弱于真异构模型。

## 发起第一个 run

对 Qoder 说一句话需求，例如：

> 帮我用 autoloop 把这个需求做完到上线：给食堂加一个每周菜单提醒，子女每周日能看到下周菜单。

Agent 将自动执行：`init` → 启动前向你复述需求与分支计划并获一句确认 → 建 `autoloop/<run-id>` 分支 → 九阶段主循环 → 评分门迭代 → 最终报告。全程你只需要在两处介入：**P7 实际部署前的确认**，以及 **blocked 时（若有）的决策**。

## 成本与数据提示

- **成本**：api 模式单个 run 最多约 135-270 次评审调用（3 模型 × ≤5 迭代 × 9 阶段；解析失败重试会更多）。成本敏感或离线场景用 local 模式（零 API 成本）。
- **数据外发**：api 模式会把产物文本（单文件截断 8000 字符）与可选的 diff（`--include-diff`）发送到所配置的第三方模型端点——发起 run 前请确认产物与代码无涉密内容。

## 版本化说明

技能目录已通过 .gitignore 白名单入库（`.qoder/skills/autoloop/`，仅 `config/models.json` 与 `__pycache__` 仍忽略）：团队可共享技能、模板与 rubric，演进有 commit 可审计。运行时状态目录 `<项目根>/.autoloop/` 不入库；含密钥的 `config/models.json` 也不入库（key 只走环境变量）。

## 目录结构

```
.qoder/skills/autoloop/
├── SKILL.md        # 技能主文件：触发条件 + 主循环编排（Agent 的操作手册）
├── DESIGN.md       # 整体设计：架构、评分门设计理由、自进化机制、安全边界
├── reference.md    # 评分与配置详解：维度权重、verdict schema、配置字段、FAQ
├── README.md       # 本文件
├── phases/         # 九阶段执行模板（进入对应阶段时才读取）
└── scripts/ config/  # 引擎脚本与配置（另由引擎侧维护）

<项目根>/.autoloop/          # 运行时状态（建议加入 .gitignore）
├── <run-id>/
│   ├── state.json           # 运行状态（勿手改）
│   ├── artifacts/           # P1-P9 阶段产物
│   ├── gates/               # 评分记录（每 gate 判定追加一行 score-history.jsonl；evolve 幂等聚合到 lessons/）
│   └── reports/             # FINAL_REPORT.md 等
└── lessons/
    ├── lessons.md           # 跨 run 经验（自动沉淀、下轮注入）
    └── score-history.jsonl  # 跨 run 评分聚合（evolve 按 run_id 幂等合并）
```

## 常用命令

| 命令 | 作用 |
|---|---|
| `python3 .qoder/skills/autoloop/scripts/harness.py init "<一句话需求>"` | 创建 run |
| `python3 .qoder/skills/autoloop/scripts/harness.py list` | 列出所有 run |
| `python3 .qoder/skills/autoloop/scripts/harness.py status [--run <id>]` | 查看 run 状态 |
| `python3 .qoder/skills/autoloop/scripts/harness.py phase [--run <id>]` | 取当前阶段与模板 |
| `python3 .qoder/skills/autoloop/scripts/harness.py gate --run <id> [--artifacts f1 f2 ...] [--mode auto\|api\|local] [--include-diff]` | 触发评分门（`--include-diff` 把 `git diff HEAD` + `git status --short` 注入评审提示词，代码类阶段 P4/P5/P6 建议携带，api 模式尤其重要） |
| `python3 .qoder/skills/autoloop/scripts/harness.py gate-status --run <id>` | 查询评分进度与结果 |
| `python3 .qoder/skills/autoloop/scripts/harness.py directives --run <id>` | 获取改进指令（失败后） |
| `python3 .qoder/skills/autoloop/scripts/harness.py continue --run <id>` | blocked 后批准继续迭代（仅 blocked 状态可用；通过时引擎自动推进下一阶段） |
| `python3 .qoder/skills/autoloop/scripts/harness.py report --run <id>` | 生成最终报告 |
| `python3 .qoder/skills/autoloop/scripts/harness.py evolve --run <id>` | 复盘与 rubric 补丁提案 |
| `python3 .qoder/skills/autoloop/scripts/scorer.py ingest --run <id> --evaluator A --file <verdict.json>` | 回填评审 verdict（local 模式） |

## 评分规则速览

- **3 个评审**：A 产品专家 / B 研发专家 / C 质量仲裁，相互独立、互不可见分数。
- **95 分准入**：默认 strategy=all——三个评审全部 ≥95 才放行。
- **证据强制**：无证据支撑的评分被 cap 到 90（等于失败）。
- **veto 一票否决**：编造证据、超范围改动、无回滚方案、未处置 critical 缺陷、未经确认部署等原则性问题直接 fail。
- **迭代上限**：默认每阶段最多 5 轮，超限 blocked 转人工决策。
- **安全红线**：实际部署/推送必须用户确认（safety.auto_deploy=false）；rubric 补丁只提案、不自动应用。

更多细节：评分维度权重与 verdict 格式见 [reference.md](./reference.md)；设计动机见 [DESIGN.md](./DESIGN.md)。
