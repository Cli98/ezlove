# P9 自进化复盘（evolve）

## 目标
把本轮 run 的经验转化为可复用资产：可泛化的经验教训（沉淀进 lessons.md 供下一轮注入）、基于评分数据（score-history.jsonl）的流程分析、rubric 补丁提案（供人工审批）。本阶段让流水线"越用越准"——它是 autoloop 与普通流水线的本质区别。

## 输入
- 本 run 全部产物（`artifacts/P1-*.md` 至 `artifacts/P8-*.md`）。
- 评分数据：`<项目根>/.autoloop/<run-id>/gates/score-history.jsonl`（每次 gate 判定完成时立即追加一行，P9 执行期间该文件已存在，是数据分析的权威来源；字段含 ts/run_id/phase/phase_name/iter/passed/scores/avg/min/directives_count）。
- 历史经验：`.autoloop/lessons/lessons.md`（若存在，用于去重——不重复沉淀已有条目）。
- 配置现状：`config/rubrics.json`、`config/harness.json`（只读，**本阶段不得修改任何配置文件**）。

## 执行者
Research 型复盘子代理（分析与写作，不改代码、不改配置）。派遣提示必须包含：本 run 全部产物路径、score-history.jsonl 读取方式、本模板"执行指令"全文、现有 lessons.md 全文、相关 lessons 条目。

## 执行指令
1. 经验教训必须**可泛化**：写成脱离本项目也成立的经验（如"P3 文件清单未到路径级会导致 P4 大量偏差"而非"本次 moment.py 改错了"）。每条经验附"适用场景"与"建议动作"。
2. 数据分析：读取 score-history.jsonl，统计各阶段迭代轮数与三轮评分走势，回答——哪个阶段最常触发重评？哪个评审（A/B/C）给分最严？哪类指令反复出现（说明模板或 rubric 有缺陷）？结论必须引用具体数据。
3. rubric 补丁提案：以 **YAML/JSON diff 形式**给出（`--- 当前` / `+++ 提案`），每个 hunk 附动机（依据本轮哪条数据或经验）。**只提案，不应用**——rubric 补丁默认不自动应用，须用户批准后由编排 Agent 修改 config/rubrics.json。
4. 流程摩擦清单：本轮执行中哪些环节卡壳（模板指令不清、产物模板缺章节、评审指令含糊），逐条给出模板级改进建议。
5. 下一轮建议：给下一个 run 的 3-5 条具体建议（如"P1 阶段先问用户澄清 X 类问题"）。
6. lessons 沉淀：把可泛化经验**追加**到 `.autoloop/lessons/lessons.md`（本阶段唯一允许写入的文件，只追加不修改既有条目，带日期与 run-id 标注）。

## 必须产出物
- `artifacts/P9-retro.md`（复盘），固定章节：

| 章节 | 内容要求 |
|---|---|
| 经验教训 | 可泛化经验 / 适用场景 / 建议动作 |
| 流程摩擦 | 摩擦点 / 根因 / 模板级改进建议 |
| rubric 补丁提案 | diff 形式 + 每个 hunk 的动机 |
| 下一轮建议 | 3-5 条可执行建议 |

（另：`.autoloop/lessons/lessons.md` 的增量追加是本阶段的伴生产出。）

## lessons.md 条目格式

每条经验按以下格式追加（便于下一轮注入时检索）：

```
- [YYYY-MM-DD / <run-id>] <一句话经验> | 适用场景：<...> | 建议动作：<...>
```

- 只追加：既有条目一律不改写；同类经验再次出现时新增条目并标注"（再次验证）"，重复本身就是信号。
- 单条 ≤2 行：lessons 是注入上下文而非文档，控制信息密度；展开分析写进 P9-retro.md。
- 与项目无关的经验优先级高于项目特定经验（前者每个仓库都能受益）。

## 迭代与改进约定

- 本阶段 gate 失败后，用 `python3 .qoder/skills/autoloop/scripts/harness.py directives --run <run-id>` 获取改进指令，据此修订复盘产物，并在文件尾部追加「改进记录」一节（轮次 / 收到的指令 / 修订内容）。
- 指令指向数据分析不实时，必须重新读取 score-history.jsonl 核对后再改，禁止凭印象修正数字。
- 本阶段是最后一个阶段。收尾时序：P9 gate 通过（状态变 done）→ 执行 `python3 .qoder/skills/autoloop/scripts/harness.py report --run <run-id>` → 执行 `python3 .qoder/skills/autoloop/scripts/harness.py evolve --run <run-id>`（仅 status=done 可执行，否则报错）。
- evolve 不会覆盖你的复盘产物：`artifacts/P9-retro.md` 已存在时打印"复盘产物已存在，保留原文"，不存在时才生成骨架；它只负责把本 run 的 `gates/score-history.jsonl` 幂等合并到跨 run 的 `.autoloop/lessons/score-history.jsonl`（按 run_id 去重）并呈报复盘结论与 rubric 补丁提案。重复执行 evolve 幂等。
- 超过迭代上限（默认 5 轮）进入 blocked：停止修订，向用户呈报记分卡与未决指令，等待决策。

## 完成标准
- [ ] 每条经验可泛化（剥离项目细节仍成立），有适用场景与建议动作。
- [ ] 数据分析引用 score-history.jsonl 的具体数字（阶段/轮数/分数）。
- [ ] rubric 补丁提案为标准 diff 形式且每个 hunk 有动机说明。
- [ ] 流程摩擦有模板级改进建议（可落回 phases/*.md 的具体章节）。
- [ ] `.autoloop/lessons/lessons.md` 已追加本轮经验（带日期与 run-id），且无与既有条目重复。
- [ ] 未修改 config/ 下任何文件（提案 ≠ 应用）。
- [ ] 迭代轮次产生的改进记录完整可追溯（若经历过重评）。

## 评分要点（摘要）
- 最看重：经验的可泛化性、数据分析的实证性（引用具体分数与轮数）、补丁提案的可评审性（diff 规范、动机清楚）。
- 常见扣分：经验写成项目流水账；分析无数据引用只凭印象；补丁提案写成一段散文没有 diff；lessons 追加与既有条目重复；下一轮建议空泛（"加强沟通"）。
- veto 触发：**擅自修改 config/rubrics.json 或 harness.json**；lessons.md 既有条目被篡改（只允许追加）；数据分析的数字与 score-history.jsonl 事实不符。
