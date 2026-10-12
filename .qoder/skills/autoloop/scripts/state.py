#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""autoloop 状态机与持久化模块。

职责：
- run 的创建、加载、保存（state.json 落盘）
- 评分门判定（judge：证据强制 / strategy=all|avg / veto / directives 合并）
- 阶段推进、迭代计数、blocked/done 状态转移

所有操作纯标准库，无第三方依赖。
"""

import json
import os
import random
import string
import tempfile
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量与路径
# ---------------------------------------------------------------------------

# skill 根目录（本文件位于 <skill>/scripts/ 下）
SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = SKILL_DIR / "config"
CONFIG_HARNESS_PATH = CONFIG_DIR / "harness.json"
CONFIG_RUBRICS_PATH = CONFIG_DIR / "rubrics.json"
CONFIG_MODELS_PATH = CONFIG_DIR / "models.json"

# 三个评审的固定编号
EVALUATOR_IDS = ["A", "B", "C"]

# 严重级别排序权重（critical 最优先）
SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2}

# state 允许的顶层状态
STATUS_ALLOWED = ("running", "awaiting_ingest", "blocked", "done")


class AutoloopError(Exception):
    """autoloop 业务错误（CLI 捕获后以退出码 2 结束）。"""


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def now_iso():
    """返回本地时间的 ISO8601 字符串（秒级精度）。"""
    return datetime.now().isoformat(timespec="seconds")


def new_run_id():
    """生成 run_id：YYYYMMDD-HHMMSS-<6位随机小写字母数字>。"""
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + rand


def write_json(path, data):
    """原子写 JSON 文件（mkstemp 唯一临时名 + replace，避免并发写同一目标时临时文件互相覆盖）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # FIX-2：固定 *.tmp 临时名在并发写同一目标时会互相覆盖，改用 mkstemp 生成唯一名
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_name, path)
    except BaseException:
        # 写入或替换失败时清理临时文件，避免残留
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def read_json(path):
    """读 JSON 文件；不存在返回 None。"""
    path = Path(path)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def emit_json(payload):
    """输出机器可解析的 JSON 行（约定前缀 `JSON: `），供上层 agent 解析。"""
    print("JSON: " + json.dumps(payload, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------

def load_harness_config():
    """加载流程与阈值配置（config/harness.json）。"""
    cfg = read_json(CONFIG_HARNESS_PATH)
    if cfg is None:
        raise AutoloopError("缺少配置文件: %s" % CONFIG_HARNESS_PATH)
    return cfg


def load_rubrics():
    """加载 9 阶段评分细则与评审 persona（config/rubrics.json）。"""
    rub = read_json(CONFIG_RUBRICS_PATH)
    if rub is None:
        raise AutoloopError("缺少配置文件: %s" % CONFIG_RUBRICS_PATH)
    return rub


def gate_config():
    """返回评分门配置段。"""
    return load_harness_config().get("gate", {})


def phases_config():
    """返回阶段定义列表。"""
    return load_harness_config().get("phases", [])


def state_root():
    """运行时状态根目录：env AUTOLOOP_STATE_DIR 优先，其次配置，默认 .autoloop（相对 cwd）。"""
    env = os.environ.get("AUTOLOOP_STATE_DIR")
    if env:
        return Path(env)
    cfg = load_harness_config()
    return Path(cfg.get("run", {}).get("state_dir", ".autoloop"))


def list_run_ids(root=None):
    """列出状态根目录下所有 run_id（按 state.json 修改时间升序，末尾即最新）。

    同一秒内创建的 run_id 时间戳前缀相同，字典序不稳定，
    因此以 mtime 为主键、run_id 为次键排序，保证“最新”语义稳定。
    """
    root = Path(root) if root else state_root()
    if not root.exists():
        return []
    out = []
    for child in root.iterdir():
        sf = child / "state.json"
        if child.is_dir() and sf.exists():
            try:
                mtime = sf.stat().st_mtime_ns
            except OSError:
                continue
            out.append((mtime, child.name))
    return [name for _, name in sorted(out)]


def latest_run_id(root=None):
    """返回最新的 run_id；无 run 时返回 None。"""
    ids = list_run_ids(root)
    return ids[-1] if ids else None


# ---------------------------------------------------------------------------
# 判定逻辑（纯函数）
# ---------------------------------------------------------------------------

def normalize_issue_key(description):
    """issue description 规范化去重键：小写并去掉全部空白。"""
    return "".join(str(description).lower().split())


def build_directives(evaluators):
    """合并三个 evaluator 的 issues 为去重后的指令列表。

    - 以 description 规范化（小写去空白）后作为 key 去重
    - 同一问题被多个 evaluator 指出则合并 evaluators 列表
    - severity 冲突时取更严重级别
    - 按 critical > major > minor 排序，编号 D1、D2...
    """
    merged = {}
    order = []
    for ev_id in EVALUATOR_IDS:
        ev = evaluators.get(ev_id)
        if not ev:
            continue
        for issue in ev.get("issues") or []:
            desc = str(issue.get("description", "")).strip()
            if not desc:
                continue
            key = normalize_issue_key(desc)
            sev = issue.get("severity", "minor")
            if sev not in SEVERITY_ORDER:
                sev = "minor"
            action = str(issue.get("directive", "") or "").strip()
            if key in merged:
                m = merged[key]
                if SEVERITY_ORDER[sev] < SEVERITY_ORDER[m["severity"]]:
                    m["severity"] = sev
                if ev_id not in m["evaluators"]:
                    m["evaluators"].append(ev_id)
                if not m["action"] and action:
                    m["action"] = action
            else:
                merged[key] = {
                    "severity": sev,
                    "evaluators": [ev_id],
                    "description": desc,
                    "action": action,
                }
                order.append(key)
    ordered = sorted(merged.values(), key=lambda d: SEVERITY_ORDER[d["severity"]])
    out = []
    for i, d in enumerate(ordered, 1):
        out.append({
            "id": "D%d" % i,
            "severity": d["severity"],
            "evaluators": d["evaluators"],
            "description": d["description"],
            "action": d["action"],
        })
    return out


def _as_num(score):
    """把 score 规整为 int（整值）或 float。"""
    if isinstance(score, bool):
        return 0
    f = float(score)
    return int(f) if f.is_integer() else f


def judge(evaluators, gate_cfg):
    """评分门判定（核心逻辑）。

    输入：
      evaluators: {"A": {..., score, evidence, issues, veto, parse_ok}, ...}（应包含全部 3 个）
      gate_cfg:   harness.json 的 gate 段

    规则：
      1. 证据强制：evidence 为空数组 → score cap 到 no_evidence_cap 后再参与判定；
         证据缺失无论分数高低一律记入 verdict_reason（m11）
      2. strategy=all（默认）：所有 score ≥ threshold 且无 veto 且 3 个全部有效 → passed
      3. strategy=avg：avg ≥ threshold 且 min ≥ min_per_model 且无 veto 且无 evidence 缺失
         （任一 evaluator evidence 为空 → 直接不通过，m2）→ passed
      4. veto：任一 evaluator veto 非 null → 直接 failed
      5. parse_ok=false → 该 evaluator 以 0 分参与判定
      6. 判定失败且合并 issues 为空时，合成兜底 directives（veto → critical；
         evidence 空 → major），保证失败必有可执行指令（FIX-3）

    返回判定结果 dict（含 scores/avg/min/max/passed/veto/directives/verdict_reason/threshold）。
    """
    threshold = float(gate_cfg.get("threshold", 95.0))
    strategy = str(gate_cfg.get("strategy", "all"))
    min_per_model = float(gate_cfg.get("min_per_model", 90.0))
    evidence_required = bool(gate_cfg.get("evidence_required", True))
    cap = float(gate_cfg.get("no_evidence_cap", 90.0))

    reasons = []
    scores = {}
    veto_list = []
    all_valid = all(ev_id in evaluators for ev_id in EVALUATOR_IDS) and all(
        bool(evaluators.get(ev_id, {}).get("parse_ok", False)) for ev_id in EVALUATOR_IDS)

    # 1. 逐个评审计分（含证据 cap 与解析失败处理）
    for ev_id in EVALUATOR_IDS:
        ev = evaluators.get(ev_id)
        if ev is None:
            reasons.append("评审 %s 缺失" % ev_id)
            continue
        if not ev.get("parse_ok", False):
            scores[ev_id] = 0
            reasons.append("评审 %s 响应解析失败，按 0 分计（raw 已存档）" % ev_id)
            continue
        score = float(ev.get("score", 0))
        if evidence_required and not (ev.get("evidence") or []):
            # m11：证据缺失无论分数是否触发 cap 都记入 verdict_reason
            if score > cap:
                reasons.append("评审 %s evidence 为空，分数由 %.1f cap 至 %.1f" % (ev_id, score, cap))
                score = cap
            else:
                reasons.append("评审 %s evidence 为空（分数 %.1f 未超 cap %.1f，分数不变）"
                               % (ev_id, score, cap))
        scores[ev_id] = _as_num(score)

    # 2. veto 检查（任一非空即触发）
    for ev_id in EVALUATOR_IDS:
        ev = evaluators.get(ev_id)
        if not ev:
            continue
        v = ev.get("veto")
        if v is not None and str(v).strip():
            veto_list.append({"evaluator": ev_id, "reason": str(v).strip()})

    vals = [float(scores[e]) for e in EVALUATOR_IDS if e in scores]
    avg_score = round(sum(vals) / len(vals), 1) if vals else 0.0
    min_score = min(vals) if vals else 0.0
    max_score = max(vals) if vals else 0.0

    # 3. 判定
    if veto_list:
        passed = False
        reasons.insert(0, "触发一票否决：" + "；".join(
            "%s（%s）" % (v["evaluator"], v["reason"]) for v in veto_list))
    elif not all_valid:
        passed = False
        reasons.append("评分不完整或存在无效评审，不允许通过")
    elif strategy == "avg":
        # m2：avg 策略下任一 evaluator evidence 为空 → 证据不完整，直接不通过
        empty_evidence = [e for e in EVALUATOR_IDS
                          if e in evaluators and not (evaluators[e].get("evidence") or [])]
        if evidence_required and empty_evidence:
            passed = False
            reasons.append("strategy=avg: 评审 %s evidence 为空，证据不完整，不通过"
                           % "、".join(empty_evidence))
        elif avg_score >= threshold and min_score >= min_per_model:
            passed = True
            reasons.append("strategy=avg: avg %.1f ≥ threshold %.1f 且 min %.1f ≥ min_per_model %.1f"
                           % (avg_score, threshold, min_score, min_per_model))
        elif avg_score < threshold:
            passed = False
            reasons.append("strategy=avg: avg score %.1f < threshold %.1f" % (avg_score, threshold))
        else:
            passed = False
            reasons.append("strategy=avg: min score %.1f < min_per_model %.1f" % (min_score, min_per_model))
    else:  # strategy=all（默认）
        if min_score >= threshold:
            passed = True
            reasons.append("strategy=all: 所有模型分数均 ≥ %.1f（min %.1f）" % (threshold, min_score))
        else:
            passed = False
            reasons.append("strategy=all: min score %.1f < threshold %.1f" % (min_score, threshold))

    directives = build_directives(evaluators)
    if not passed and not directives:
        # FIX-3：判定失败但评审未给出任何 issue 时，合成兜底指令保证失败必有可执行指令
        directives = _fallback_directives(evaluators, veto_list, evidence_required)

    return {
        "scores": scores,
        "avg_score": avg_score,
        "min_score": _as_num(min_score),
        "max_score": _as_num(max_score),
        "passed": passed,
        "veto": veto_list,
        "directives": directives,
        "verdict_reason": "；".join(reasons),
        "threshold": threshold,
        "strategy": strategy,
        "min_per_model": min_per_model,
    }


def _fallback_directives(evaluators, veto_list, evidence_required):
    """判定失败且评审 issues 合并为空时，合成兜底指令（FIX-3）。

    - 每个 veto 的 evaluator 生成一条 critical 指令（针对原则性问题）
    - 每个（解析成功但）evidence 为空的 evaluator 生成一条 major 指令（要求补充证据）
    """
    out = []

    def _add(severity, ev_id, description, action):
        out.append({
            "id": "D%d" % (len(out) + 1),
            "severity": severity,
            "evaluators": [ev_id],
            "description": description,
            "action": action,
        })

    for v in veto_list:
        _add("critical", v["evaluator"],
             "评审 %s 触发一票否决：%s" % (v["evaluator"], v["reason"]),
             "针对该原则性问题修订产物后重新提交")
    if evidence_required:
        for ev_id in EVALUATOR_IDS:
            ev = evaluators.get(ev_id)
            if ev and ev.get("parse_ok", False) and not (ev.get("evidence") or []):
                _add("major", ev_id,
                     "评审 %s 未提供任何评分证据" % ev_id,
                     "在产物中补充可核验的证据（文件/行号/测试输出引用）供评审引用")
    return out


def append_score_history(state, gate_data):
    """评分门判定完成后，向 <run>/gates/score-history.jsonl 追加一行（FIX-1）。

    这是 P9 复盘的权威数据源：每轮 gate 判定时即写入一行，字段：
    {ts, run_id, phase, phase_name, iter, passed, scores, avg, min, directives_count}

    参数：
      state:     RunState 实例（提供 run_id 与 run 目录）
      gate_data: 判定完成后的 gate 文件数据（含 phase/iteration/passed/scores 等）
    """
    path = state.dir / "gates" / "score-history.jsonl"
    record = {
        "ts": now_iso(),
        "run_id": state.run_id,
        "phase": gate_data.get("phase"),
        "phase_name": gate_data.get("phase_name"),
        "iter": gate_data.get("iteration"),
        "passed": bool(gate_data.get("passed")),
        "scores": gate_data.get("scores") or {},
        "avg": gate_data.get("avg_score"),
        "min": gate_data.get("min_score"),
        "directives_count": len(gate_data.get("directives") or []),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# RunState：单个 run 的状态机
# ---------------------------------------------------------------------------

class RunState:
    """一个 autoloop run 的状态封装（state.json 的内存映像 + 状态转移）。"""

    def __init__(self, data, root=None):
        self.data = data
        self.root = Path(root) if root is not None else state_root()
        self.cfg = load_harness_config()
        self.rubrics = load_rubrics()

    # ---- 创建与加载 ----

    @classmethod
    def create(cls, requirement, root=None):
        """创建新 run（init 命令实现）。"""
        root = Path(root) if root is not None else state_root()
        if not str(requirement).strip():
            raise AutoloopError("需求不能为空")
        # m12：run 目录已存在（run_id 碰撞）时重新生成，最多尝试 3 次，仍冲突则报错
        run_id = None
        for _ in range(3):
            candidate = new_run_id()
            if not (root / candidate).exists():
                run_id = candidate
                break
        if run_id is None:
            raise AutoloopError("run_id 连续 3 次碰撞（目录 %s），无法创建运行" % root)
        phases = {}
        for i, p in enumerate(phases_config()):
            phases[str(p["n"])] = {
                "name": p["name"],
                "status": "running" if i == 0 else "pending",
                "iterations": 0,
                "artifacts": [],
                "gates": [],
            }
        data = {
            "run_id": run_id,
            "requirement": str(requirement),
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "phase": 1,
            "iteration": 1,
            "status": "running",
            "phases": phases,
            "notes": [],
        }
        rs = cls(data, root)
        rs._init_dirs()
        rs.save()
        return rs

    @classmethod
    def load(cls, run_id, root=None):
        """按 run_id 加载已有 run。"""
        root = Path(root) if root is not None else state_root()
        path = root / run_id / "state.json"
        if not path.exists():
            raise AutoloopError("run 不存在: %s（目录 %s）" % (run_id, root / run_id))
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(data, root)

    def _init_dirs(self):
        """创建 run 目录骨架。"""
        d = self.dir
        (d / "artifacts").mkdir(parents=True, exist_ok=True)
        (d / "gates").mkdir(parents=True, exist_ok=True)
        (d / "reports").mkdir(parents=True, exist_ok=True)

    # ---- 属性 ----

    @property
    def dir(self):
        return self.root / self.data["run_id"]

    @property
    def run_id(self):
        return self.data["run_id"]

    @property
    def phase(self):
        return self.data["phase"]

    @property
    def iteration(self):
        return self.data["iteration"]

    @property
    def status(self):
        return self.data["status"]

    @property
    def phase_count(self):
        return len(self.cfg.get("phases", []))

    def phase_meta(self, n=None):
        """返回 harness.json 中某阶段的定义 {"n","name","title"}。"""
        n = self.data["phase"] if n is None else n
        for p in self.cfg.get("phases", []):
            if p.get("n") == n:
                return p
        raise AutoloopError("配置中不存在阶段 %s" % n)

    def current_phase_entry(self):
        """state.phases 中当前阶段的条目。"""
        return self.data["phases"][str(self.data["phase"])]

    # ---- 持久化 ----

    def save(self):
        self.data["updated_at"] = now_iso()
        write_json(self.dir / "state.json", self.data)

    # ---- 状态转移 ----

    def set_artifacts(self, artifacts):
        """记录当前阶段参与评分的产物路径列表（gate 命令调用）。"""
        entry = self.current_phase_entry()
        entry["artifacts"] = list(artifacts)
        self.save()

    def open_gate(self, gate_relpath, phase, iteration):
        """发起 local 评分门：status → awaiting_ingest，登记 pending_gate。"""
        self.data["status"] = "awaiting_ingest"
        self.data["pending_gate"] = {
            "file": gate_relpath,
            "phase": phase,
            "iter": iteration,
            "received": [],
        }
        self.save()

    def apply_judged_gate(self, gate_relpath, judged, phase, iteration):
        """评分门判定完成后的状态转移。

        - 通过：当前阶段 status=passed；顶层 phase+1、iteration=1；
                若为最后阶段则 status=done
        - 失败：iteration+1；超过 max_iterations 则 status=blocked，否则 running
        """
        entry = self.data["phases"][str(phase)]
        entry["gates"].append({
            "iter": iteration,
            "file": gate_relpath,
            "avg": judged["avg_score"],
            "min": judged["min_score"],
            "passed": bool(judged["passed"]),
        })
        entry["iterations"] = len(entry["gates"])
        self.data["last_gate"] = {
            "file": gate_relpath,
            "phase": phase,
            "iter": iteration,
            "passed": bool(judged["passed"]),
            "scores": judged["scores"],
            "avg_score": judged["avg_score"],
            "min_score": judged["min_score"],
            "max_score": judged["max_score"],
            "threshold": judged.get("threshold"),
            "verdict_reason": judged.get("verdict_reason", ""),
        }
        self.data["pending_gate"] = None
        if judged["passed"]:
            entry["status"] = "passed"
            if phase >= self.phase_count:
                self.data["status"] = "done"
            else:
                nxt = phase + 1
                self.data["phase"] = nxt
                self.data["iteration"] = 1
                self.data["phases"][str(nxt)]["status"] = "running"
                self.data["status"] = "running"
        else:
            max_iter = int(self.cfg.get("gate", {}).get("max_iterations", 5))
            new_iter = iteration + 1
            self.data["iteration"] = new_iter
            if new_iter > max_iter:
                self.data["status"] = "blocked"
            else:
                self.data["status"] = "running"
        self.save()

    def approve_continue(self):
        """continue 命令：blocked → running（iteration 继续累加，不重置）。"""
        if self.data["status"] != "blocked":
            raise AutoloopError("当前状态为 %s，无需 continue（仅 blocked 状态可用）" % self.data["status"])
        self.data["status"] = "running"
        self.save()

    # ---- 查询辅助 ----

    def last_failed_gate_in_phase(self):
        """当前阶段最近一次未通过的 gate 摘要（无则 None）。"""
        entry = self.data["phases"].get(str(self.data["phase"])) or {}
        for g in reversed(entry.get("gates") or []):
            if not g.get("passed"):
                return g
        return None

    def current_prev_directives(self):
        """当前阶段上一轮失败 gate 的 directives（iteration>1 时供重评提示词引用）。"""
        g = self.last_failed_gate_in_phase()
        if not g:
            return []
        gd = read_json(self.dir / g["file"])
        return (gd or {}).get("directives") or []
