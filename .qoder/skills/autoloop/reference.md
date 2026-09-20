# autoloop 评分与配置详解

本文件是 SKILL.md 的第二层披露：评分机制、verdict 数据格式、配置文件字段与常见问题。评审子代理、执行子代理与配置维护者都应以本文档为语义基准。

## 1. 评分标尺（0-100）

| 档位 | 含义 | 判定特征 |
|---|---|---|
| 0-59 | 不可用 | 产物缺失关键章节、存在原则性错误、或大面积未达模板要求；需要推翻重做 |
| 60-79 | 有骨架但缺陷明显 | 结构齐全但多处具体要求未满足（如文件清单不到路径、文案不到字符串）；需要较大返工 |
| 80-94 | 良好但未达门槛 | 整体合格，存在若干可具体指出的缺陷；修完指令清单即可达标 |
| 95-100 | **生产级** | 证据充分、模板要求逐项满足、评审只能提出吹毛求疵级意见；**唯一可放行档位** |

关键提醒：95 不是"优秀"，是"生产级、证据充分、无可挑剔"。评审打分时先假设产物是 80 分，逐项用证据加分——而不是从 100 分往下扣。

## 2. 九阶段评分维度权重表

每阶段 4-5 个维度，权重和为 100。本表为 `config/rubrics.json` 各维度（key）的中文释义，**机器可读的权威源是 rubrics.json**（P9 补丁提案的修改目标）。各阶段 phases/ 模板的"完成标准/评分要点"是这些维度在操作层的展开。

| 阶段 | 维度（key） | 权重 | 评分要点 |
|---|---|---|---|
| P1 intake | 清晰度（clarity） | 30 | 目标、范围、非目标、验收标准清晰无歧义 |
| | 完整性（completeness） | 30 | 关键场景、边界、约束、干系人完整 |
| | 可行性（feasibility） | 20 | 技术与人力的可行性判断有依据 |
| | 风险意识（risk_awareness） | 20 | 识别主要风险与开放问题 |
| P2 product | 用户价值（user_value） | 25 | 核心用户场景与价值主张清晰，兼顾双方视角 |
| | 场景完整性（scenario_completeness） | 25 | 功能范围完整，含边界场景、异常流与降级方案 |
| | 体验适配（ux_fit） | 20 | 交互符合目标用户约束（老人端大字体、零学习成本、高对比度） |
| | 可度量性（measurability） | 15 | 成功指标与验收口径可量化、可验证 |
| | 范围克制（scope_discipline） | 15 | 非目标明确，无需求蔓延 |
| P3 tech-design | 架构适配（architecture_fit） | 30 | 与现有系统结构匹配，模块边界清晰，无过度设计 |
| | 需求覆盖（requirement_coverage） | 25 | 每条需求都有对应技术方案与数据流映射 |
| | 风险与回滚（risk_and_rollback） | 20 | 技术风险识别充分，含回滚与灰度策略 |
| | 数据与接口（data_and_api） | 15 | 数据模型、接口契约、迁移方案完整自洽 |
| | 可运维性（operability） | 10 | 可部署、可观测、可测试，含监控与日志方案 |
| P4 implement | 需求覆盖（requirement_coverage） | 25 | 需求条目逐项落地，无遗漏、无擅自变更 |
| | 正确性（correctness） | 30 | 逻辑正确，边界与异常处理完备，与方案一致 |
| | 安全（security） | 15 | 无注入、越权、明文密钥，配置经环境注入 |
| | 可维护性（maintainability） | 15 | 分层清晰、命名规范、注释得当、易读易改 |
| | 可测试性（testability） | 15 | 关键路径可测且已覆盖，测试独立稳定可复现 |
| P5 verify | 证据真实性（evidence_authenticity） | 30 | 测试证据真实可信，可追溯到具体执行记录 |
| | 覆盖度（coverage） | 30 | 验收标准逐条覆盖，边界与异常场景无遗漏 |
| | 可复现性（reproducibility） | 20 | 测试命令与环境说明完整，结果可一键复现 |
| | 回归风险（regression_risk） | 20 | 回归影响已评估，受影响的既有功能已覆盖 |
| P6 review | 覆盖度（coverage） | 30 | 评审覆盖需求、代码、测试、风险四象限，关键文件无遗漏 |
| | 缺陷质量（defect_quality） | 30 | 发现的问题真实、严重级别判定准确、有证据定位 |
| | 闭环严谨（resolution_rigor） | 25 | 修复有验证，未修复有记录与理由 |
| | 规范对齐（standard_alignment） | 15 | 与项目规范、安全基线、最佳实践对齐 |
| P7 release | 就绪度（readiness） | 30 | 功能冻结、遗留缺陷清零或明确豁免、验收全通过 |
| | 安全性（safety） | 25 | 灰度计划、回滚方案、数据备份就绪 |
| | 可观测性（observability） | 20 | 监控、告警、日志就绪，关键指标有基线 |
| | 流程合规（process_compliance） | 25 | 变更记录、审批、公告等流程完备可追溯 |
| P8 alpha-test | 计划质量（plan_quality） | 25 | 测试计划含对象、场景、通过标准，设计合理可行 |
| | 执行证据（execution_evidence） | 30 | 执行记录可追溯，结果有原始凭证支撑 |
| | 缺陷分诊（defect_triage） | 25 | 缺陷全部分级，处置结论明确且与发布决策联动 |
| | 反馈闭环（feedback_loop） | 20 | 用户反馈已收集、归类并回流到需求或迭代清单 |
| P9 evolve | 复盘深度（retrospection_depth） | 30 | 复盘触及根因而非表象，区分偶发与系统性问题 |
| | 数据驱动（data_driven） | 25 | 结论基于迭代次数、分数曲线、directive 分布等数据 |
| | 可执行性（actionability） | 25 | 改进项有明确动作、责任人与验证方式 |
| | 知识沉淀（knowledge_capture） | 20 | 经验沉淀为可复用资产（教训、模板、规则） |

三评审（A/B/C）共用同一套维度，但 persona 不同（见 rubrics.json 的 evaluator_personas）：A 从用户价值/需求覆盖/体验完整性评、B 从正确性/安全性/可维护性评、C 从风险/可验证性/上线就绪度评且要求最严。

## 3. 证据规则

1. **证据形式**：产物章节锚点（`artifacts/P3-tech-design.md#数据契约`）、代码定位（`backend/app/services/moment.py:L120-L134`）、命令输出引用（报告中的证据编号）。
2. **证据强制**：verdict 中 `evidence` 为空时，该 verdict 总分被 cap 到 90（`gate.no_evidence_cap`，低于 threshold 即失败）。
3. **证据可核验**：评审给出的引用必须真实存在于产物/代码中——张冠李戴的引用本身就是 veto 级问题（评审造假与产物造假同罪）。
4. **证据时效**：P5/P7 的输出证据必须来自本轮会话的真实运行。

## 4. veto 规则

veto = 原则性问题一票否决（分数再高也 fail，`gate.veto_policy="hard_fail"`）。rubrics.json 内置了每阶段的具体 veto 条款，模板"评分要点"是其操作化表述，两处并集生效：

| 阶段 | rubrics.json 内置 veto |
|---|---|
| P1 | 需求存在致命歧义且未记录默认决策；验收标准不可验证 |
| P2 | 核心用户场景无法闭环（主流程断裂）；违反产品红线（监控式措辞、老人端高学习成本设计） |
| P3 | 存在无法回滚的破坏性数据变更且无迁移方案；方案与验收标准直接冲突 |
| P4 | 存在安全漏洞（明文密钥、注入、越权访问等）；核心流程无法运行或明显偷工减料偏离方案 |
| P5 | 关键路径零测试覆盖；测试证据无法复现或系伪造 |
| P6 | 发现致命缺陷但未给出处置结论；关键变更未经评审即合入 |
| P7 | 无回滚方案的发布；存在未处置的 critical 级缺陷 |
| P8 | 阿尔法测试未真实执行（无执行痕迹）；发现 critical 缺陷但未影响发布决策 |
| P9 | 复盘结论与评分数据明显矛盾；改进项全部不可执行 |

模板层补充的通用条款：产物缺失必需章节；未声明的超范围改动；评审引用造假；评审间共享结论；**未经用户确认执行部署/推送**（safety.auto_deploy=false）；擅自修改 config/ 或篡改 lessons.md 既有条目。

## 5. verdict JSON schema（全量）

每个评审（local 模式由评审子代理产出、api 模式由脚本调模型产出）的评分文件格式。以 P3 技术方案、评审 B 为例：

```json
{
  "evaluator": "B",
  "score": 92,
  "dimension_scores": {
    "architecture_fit": 95,
    "requirement_coverage": 90,
    "risk_and_rollback": 85,
    "data_and_api": 90,
    "operability": 95
  },
  "strengths": [
    "文件清单全部到路径级，新增/修改/删除三组划分清晰"
  ],
  "issues": [
    {
      "severity": "major",
      "description": "回滚方案缺数据处理说明：迁移产生的数据如何处置未写",
      "directive": "回滚方案补充数据处置步骤（迁移产生的数据保留/清理策略及理由）"
    },
    {
      "severity": "minor",
      "description": "canteen_menu.price 字段缺单位说明",
      "directive": "为 price 字段补充单位（分）与示例值"
    }
  ],
  "evidence": [
    "artifacts/P3-tech-design.md#兼容与回滚：仅写\"可回滚\"三字，无具体步骤",
    "artifacts/P3-tech-design.md#数据契约：price 无单位标注"
  ],
  "veto": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| evaluator | string | 是 | 固定 "A" / "B" / "C"，须与 ingest 的 --evaluator 一致 |
| score | number | 是 | 0-100 总评分（整数优先）；无 verdict pass/fail 字段——通过与否由引擎按 threshold/strategy/veto 判定 |
| dimension_scores | object | 是 | 维度名→分数；维度名取 rubrics.json 该阶段的维度 key（见本文 §2） |
| strengths | array | 否（建议填） | 亮点列表（字符串），供最终报告聚合 |
| issues | array | 是 | 问题清单，每项含 severity（critical/major/minor，必填）/ description（必填非空）/ directive（具体可执行的修复指令） |
| evidence | array | 是 | 证据列表（字符串）：引用产物具体内容/文件/行号/测试名；为空会被 cap 到 90 |
| veto | null/string | 是 | 命中一票否决情形（见 §4）时填理由字符串，否则必须为 null |

要点：

- **无 phase/round 字段**：引擎从 run 上下文关联阶段与轮次，评审不需要自报。
- **改进指令藏在 issues[].directive**：`harness.py directives` 命令汇总去重的就是各 verdict 的 issues[].directive。
- **evidence 为空的双重后果**：无论分数高低，evidence 为空都会被记录原因（reason）并生成 major 级兜底指令；gate 失败时该指令进入 directives 汇总，确保指令非空。avg 聚合策略下任一评审 evidence 为空直接判不通过（证据硬门优先于分数，不经 cap 与 min_per_model 协商）。
- **local 模式的落盘路径**：`gates/<gate-stem>.verdicts/<A|B|C>.json`（评审提示词文件末尾会写明精确路径与提交命令）。
- **解析鲁棒性**：脚本可剥离 ```json 代码栅栏并截取首尾大括号，但字段名与类型必须严格符合上表，否则 ingest 拒绝（见 FAQ Q1）。

## 6. config/models.json 字段说明

从 `config/models.json.example` 复制为 `config/models.json` 后编辑：

```json
{
  "evaluators": {
    "A": {
      "provider": "openai_compatible",
      "base_url": "https://api.deepseek.com/v1",
      "api_key_env": "AUTOLOOP_EVAL_A_KEY",
      "model": "deepseek-chat",
      "temperature": 0.1,
      "max_tokens": 3000,
      "timeout_seconds": 120
    },
    "B": {
      "provider": "anthropic",
      "base_url": "https://api.anthropic.com",
      "api_key_env": "AUTOLOOP_EVAL_B_KEY",
      "model": "claude-sonnet-4-20250514",
      "temperature": 0.1,
      "max_tokens": 3000,
      "timeout_seconds": 120
    },
    "C": {
      "provider": "openai_compatible",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key_env": "AUTOLOOP_EVAL_C_KEY",
      "model": "qwen-plus",
      "temperature": 0.1,
      "max_tokens": 3000,
      "timeout_seconds": 120
    }
  }
}
```

| 字段 | 说明 |
|---|---|
| evaluators.A/B/C | 三个评审的模型定义（A 产品专家 / B 研发专家 / C 质量仲裁）；文件存在且可解析即 api 模式，不存在则 gate 自动落 local 模式。persona 由 evaluator ID（A/B/C）绑定 rubrics.json 的 evaluator_personas，无需额外配置字段 |
| provider | 协议类型：`openai_compatible`（任意 OpenAI Chat Completions 兼容端点，DeepSeek/Qwen/GLM 等）、`anthropic` |
| base_url | API 端点 |
| model | 模型名（按 provider 的命名规范） |
| api_key_env | 读 key 的环境变量名；A/B/C 默认 `AUTOLOOP_EVAL_A_KEY` / `AUTOLOOP_EVAL_B_KEY` / `AUTOLOOP_EVAL_C_KEY` |
| temperature / max_tokens | 采样参数（低 temperature 保证评分稳定） |
| timeout_seconds | 单次评分调用超时 |

**建议异构配置**：A/B/C 用三个不同厂商的模型（如 DeepSeek/Claude/Qwen），异构性是评分独立性的物理基础（见 DESIGN.md §5.4）。api key 只走环境变量，严禁写进 models.json。

**数据流向提示**：api 模式会把产物文本（单文件截断 8000 字符）与可选的 diff（携带 `--include-diff` 时）发送到所配置的第三方模型端点——发起 run 前请确认产物与代码无涉密内容。

## 7. config/harness.json 字段说明

| 字段 | 默认值 | 说明 |
|---|---|---|
| gate.threshold | 95 | 评审放行阈值（三评审均须 ≥ 此值） |
| gate.strategy | "all" | 门禁聚合策略：all=三评审全部 ≥threshold 才通过 |
| gate.max_iterations | 5 | 每阶段迭代上限，超限转 blocked |
| gate.evidence_required | true | 评审必须提供证据 |
| gate.no_evidence_cap | 90 | 无证据 verdict 的分数上限（低于 threshold 即自动失败） |
| gate.min_per_model | 90 | 单评审最低可接受分（低于此值即使策略放行也视为异常信号；avg 策略下任一评审 evidence 为空直接不通过，不经此字段协商） |
| gate.veto_policy | "hard_fail" | veto 语义：硬失败，一票否决（语义声明字段：由技能规范与文档约束行为，引擎不读取该值） |
| run.state_dir | ".autoloop" | 状态目录根（相对项目根） |
| safety.auto_deploy | false | **保持 false**：实际部署/推送必须用户确认（语义声明字段：由技能规范与文档约束行为，引擎不读取该值） |
| evolve.auto_apply_rubric_patch | false | **保持 false**：rubric 补丁必须人工批准后应用（语义声明字段：由技能规范与文档约束行为，引擎不读取该值） |
| phases | （9 阶段数组：n/name/title） | 阶段定义，驱动 phase 命令输出与阶段流转 |

gate 的 auto 模式选择规则：不传 `--mode` 时，脚本按 `config/models.json` 是否存在且可解析自动选 api/local（见 SKILL.md 主循环步骤 3）。`config/rubrics.json` 存放各阶段维度与权重的机器可读版（语义见本文 §2），P9 补丁提案的修改目标即此文件。

## 8. 常见问题

**Q1：评审 verdict 解析/校验失败怎么办？**
local 模式下评审子代理产出的 JSON 不合法时，`python3 .qoder/skills/autoloop/scripts/scorer.py ingest` 会拒绝并报具体错误，常见原因：evaluator 字段与 --evaluator 不一致或缺失、score 非数字或越界（0-100）、issues 项缺 severity/description、dimension_scores 不是对象、veto 不是 null 或理由字符串。处置：重新派遣该评审（同一轮、同一提示词），修正 JSON 后重新 ingest 同一 evaluator。已成功 ingest 的其他评审不受影响。

**Q2：blocked 之后怎么办？**
blocked 表示该阶段 5 轮迭代未过门。Agent 会向你呈报记分卡（三评审历轮分数+指令）与三个选项：① 继续（可临时提高 max_iterations 再 continue）；② 调整（按你的意见修订产物方向后重新 gate）；③ 终止（保留状态目录，run 不再推进）。没有你的明确选择，Agent 不得自行 continue。

**Q3：如何换评审模型？**
编辑 `config/models.json` 对应 evaluator 的 provider/model/base_url，export 新的 key 环境变量即可，下一轮 gate 生效。已 ingest 的历史评分不重算（保持历史原貌），换模型的影响从下一次评分开始。建议在换模型后的第一个 run 的 P9 里记录换型动机，供 score-history 趋势分析对照。

**Q4：三个评审分数相差很大（如 96/88/75）说明什么？**
这是有价值信号而非故障。先看三者 evidence 的分歧点：常见原因是产物对不同读者呈现不一致（对产品视角写得细、对工程视角写得粗），或某个评审发现了别人没发现的问题。C（质量仲裁）最低分通常指向证据链缺口——优先处理低分评审的 directives。

**Q5：api 模式调用失败（网络/配额/key 无效）？**
网络、HTTP、超时、密钥等错误属于基础设施错误，与产物质量无关：gate 以退出码 2 结束，不计入迭代轮数、run 状态不变，并提示检查配置（网络异常引擎会自动重试一次，重试携带失败原因）。处置：检查环境变量与网络后重新执行同一 gate。仅当"模型有返回但解析失败"时按 0 分计入判定（质量信号，走正常失败分支）。若想临时降级，用 `--mode local` 手动指定本地评审模式完成本轮。

**Q6：可以只重评某一个评审吗？**
不可以。gate 是阶段级操作，重新 gate 会对三个评审整体重评——保证同一轮的三个 verdict 评的是同一份产物（半新半旧的评分组合没有意义）。某单个评审失败时（Q1）单独重新 ingest 该评审属于同一轮内的补录，不算重评。

**Q7：95 分是不是太严了？**
设计动机见 DESIGN.md §5.2（宁严勿滥：通过门禁的产物应可直接使用）。若团队有自己的质量基线，可调 `gate.threshold`，但不建议低于 90——低于 90 后"无证据 cap 90"的约束就失去梯度意义了。

**Q8：lessons.md 会不会无限膨胀？**
P9 只追加可泛化经验且单条 ≤2 行，增速可控。当膨胀影响注入质量时，P9 复盘应提出治理提案（如按主题归档、合并同类项）——与 rubric 补丁一样走人工批准。

**Q9：gate --include-diff 是什么？何时用？**
该 flag 会把 `git diff HEAD` 与 `git status --short`（合计截断 6000 字符）注入三个评审的提示词，使评审能直接引用代码证据而非仅凭报告文字。代码类阶段（P4 研发实现 / P5 验证 / P6 评审）建议携带，api 模式尤其重要（评审默认只能看到产物文本）；文档类阶段（P1-P3）通常不需要。注意携带后 diff 会被发送到所配置的第三方端点（见 §6 数据流向提示）。

**Q10：三个评审并行提交 verdict 会冲突吗？**
不会。ingest 全程持有文件锁（`<run>/.ingest.lock`），A/B/C 三个 verdict 并行回填安全；判定只在第三个 ingest 落地时触发，不存在部分提交导致的误判。

**Q11：blocked 状态显示"已完成 N 轮迭代均未通过，第 N+1 轮待批准后开始"是什么意思？**
表示该阶段已用满迭代上限（默认 5 轮）仍未过门，引擎停止自动循环等待人工决策：继续加迭代 / 调整产物方向 / 终止 run。你批准"继续"并执行 continue 命令后，从第 N+1 轮开始恢复迭代。没有你的明确选择，Agent 不得自行 continue（见 Q2）。
