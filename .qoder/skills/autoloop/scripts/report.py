#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""autoloop 报告生成（纯模板聚合，不调模型）。

- generate_report：生成 reports/FINAL_REPORT.md
- generate_evolve：生成 artifacts/P9-retro.md 骨架（已存在时保留原文不覆盖），
  并把本 run 的 gates/score-history.jsonl 全量行按 run_id 幂等合并进
  <state_root>/lessons/score-history.jsonl（FIX-1）
"""

import json
import sys
from pathlib import Path

# 确保同目录模块可导入
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import state as st


def _load_gate_data(rs, gate_file_rel):
    """读取某个 gate 文件的完整数据；不存在返回 None。"""
    return st.read_json(rs.dir / gate_file_rel)


def collect_phase_stats(rs):
    """聚合每阶段统计：评分门次数、最终分数、是否重试、指令数等。"""
    rows = []
    for n in range(1, rs.phase_count + 1):
        entry = rs.data["phases"].get(str(n)) or {}
        gates = entry.get("gates") or []
        final = gates[-1] if gates else None
        final_data = _load_gate_data(rs, final["file"]) if final else None
        directives_count = 0
        sev_count = {"critical": 0, "major": 0, "minor": 0}
        for g in gates:
            gd = _load_gate_data(rs, g["file"])
            if not gd:
                continue
            for d in gd.get("directives") or []:
                directives_count += 1
                sev = d.get("severity", "minor")
                if sev in sev_count:
                    sev_count[sev] += 1
        failed_gates = sum(1 for g in gates if not g.get("passed"))
        rows.append({
            "phase": n,
            "name": entry.get("name", ""),
            "title": rs.phase_meta(n)["title"],
            "gates": len(gates),
            "scores": (final_data or {}).get("scores", {}),
            "avg": final["avg"] if final else None,
            "passed": final["passed"] if final else None,
            "retried": len(gates) > 1,
            "directives": directives_count,
            "severity": sev_count,
            "failed_gates": failed_gates,
        })
    return rows


def last_gate_data(rs):
    """最近一次已判定 gate 的完整数据（无则 None）。"""
    last = rs.data.get("last_gate")
    if not last:
        return None
    return _load_gate_data(rs, last["file"])


def generate_report(run_id, root=None):
    """生成 FINAL_REPORT.md，返回文件路径。"""
    rs = st.RunState.load(run_id, root)
    rows = collect_phase_stats(rs)
    d = rs.data

    lines = []
    lines.append("# autoloop 最终报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append("- **run_id**: %s" % d["run_id"])
    lines.append("- **需求**: %s" % d["requirement"])
    lines.append("- **创建时间**: %s" % d["created_at"])
    lines.append("- **更新时间**: %s" % d["updated_at"])
    lines.append("- **最终状态**: %s" % d["status"])
    lines.append("- **当前进度**: %d/%d（%s）" % (
        d["phase"], rs.phase_count, rs.phase_meta()["title"]))
    lines.append("")
    lines.append("## 阶段评分总览")
    lines.append("")
    lines.append("| 阶段 | 名称 | 评分门次数 | 最终分数 A/B/C | 平均分 | 曾失败重试 |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        if r["gates"]:
            scores = r["scores"]
            score_str = " / ".join(str(scores.get(e, "—")) for e in st.EVALUATOR_IDS)
            avg_str = str(r["avg"])
            retried_str = "是" if r["retried"] else "否"
        else:
            score_str = "—"
            avg_str = "—"
            retried_str = "—"
        lines.append("| %d | %s（%s） | %d | %s | %s | %s |" % (
            r["phase"], r["title"], r["name"], r["gates"], score_str, avg_str, retried_str))
    lines.append("")

    # 改进指令统计（解决情况无法自动判断，只统计生成数）
    total_directives = sum(r["directives"] for r in rows)
    total_failed_gates = sum(r["failed_gates"] for r in rows)
    total_sev = {"critical": 0, "major": 0, "minor": 0}
    for r in rows:
        for k, v in r["severity"].items():
            total_sev[k] += v
    lines.append("## 改进指令统计")
    lines.append("")
    lines.append("- 共生成 %d 条改进指令，来自 %d 个未通过的评分门。" % (
        total_directives, total_failed_gates))
    lines.append("- 按严重级别：critical %d 条 / major %d 条 / minor %d 条。" % (
        total_sev["critical"], total_sev["major"], total_sev["minor"]))
    lines.append("- 说明：指令是否已解决需结合后续产物人工确认，本报告仅统计生成数量。")
    lines.append("")

    # 风险与遗留：最后 gate 的 minor issues
    lines.append("## 风险与遗留")
    lines.append("")
    lg = last_gate_data(rs)
    minor_issues = []
    if lg:
        for ev_id in st.EVALUATOR_IDS:
            ev = (lg.get("evaluators") or {}).get(ev_id) or {}
            for it in ev.get("issues") or []:
                if it.get("severity") == "minor":
                    minor_issues.append((ev_id, it.get("description", "")))
    if minor_issues:
        lines.append("来自最后评分门的 minor 级遗留问题：")
        for ev_id, desc in minor_issues:
            lines.append("- %s（评审: %s）" % (desc, ev_id))
    else:
        lines.append("最后评分门无 minor 级别遗留问题记录。")
    lines.append("")

    # 结论
    lines.append("## 结论")
    lines.append("")
    if d["status"] == "done":
        lines.append("运行已完成：9 个阶段全部通过评分门。")
    elif d["status"] == "blocked":
        lines.append("运行已 blocked：阶段 %d 超过最大迭代次数，需人工评估后 continue。" % d["phase"])
    else:
        lines.append("运行进行中：当前阶段 %d/%d（%s），第 %d 轮迭代。" % (
            d["phase"], rs.phase_count, rs.phase_meta()["title"], d["iteration"]))
    lines.append("")

    out = rs.dir / "reports" / "FINAL_REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _read_jsonl(path):
    """逐行读取 JSONL 文件为 dict 列表；不存在返回 []，损坏行跳过。"""
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _merge_score_history(lessons_path, run_id, run_rows):
    """把本 run 的评分历史行合并进 lessons/score-history.jsonl（FIX-1 幂等）。

    按 run_id 去重整段替换：先移除文件中本 run_id 的旧行，再追加 run_rows。
    其他 run 的行保持原样。重复执行 evolve 不产生重复行。
    """
    existing = [obj for obj in _read_jsonl(lessons_path) if obj.get("run_id") != run_id]
    merged = existing + list(run_rows)
    lessons_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lessons_path, "w", encoding="utf-8") as f:
        for obj in merged:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return len(merged)


def generate_evolve(run_id, root=None):
    """evolve 命令实现：生成 P9 复盘骨架 + 幂等合并评分历史（FIX-1）。

    - 仅 run 状态为 done 时允许执行，否则抛 AutoloopError（CLI 退出码 2）
    - artifacts/P9-retro.md 已存在时绝不覆盖（保留真实复盘产物），
      不存在时才写入骨架
    - 本 run 的 gates/score-history.jsonl 全量行（每轮 gate 一行，判定时写入）
      按 run_id 幂等合并进 <state_root>/lessons/score-history.jsonl

    返回 (retro_path, score_history_path, 本 run 合并行数, 是否新建骨架)。
    """
    rs = st.RunState.load(run_id, root)
    if rs.data.get("status") != "done":
        raise st.AutoloopError(
            "当前运行状态为 %s，仅 done 状态允许执行 evolve 复盘" % rs.data.get("status"))
    rows = collect_phase_stats(rs)

    # 各阶段迭代统计 JSON 块（供 agent 填写复盘内容时引用）
    stats = []
    for r in rows:
        stats.append({
            "phase": r["phase"],
            "name": r["name"],
            "iterations": r["gates"],
            "avg_score": r["avg"],
            "final_passed": r["passed"],
        })

    retro_path = rs.dir / "artifacts" / "P9-retro.md"
    retro_created = False
    if retro_path.exists():
        # FIX-1：复盘产物已存在时绝不覆盖（保留真实复盘内容）
        retro_created = False
    else:
        lines = []
        lines.append("# P9 自进化复盘（%s）" % rs.data["run_id"])
        lines.append("")
        lines.append("> 本文件由 evolve 命令生成，请基于以下数据填写复盘内容。")
        lines.append("")
        lines.append("## 各阶段迭代统计")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(stats, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
        lines.append("## 复盘提纲（请填写）")
        lines.append("")
        lines.append("### 1. 分数曲线分析")
        lines.append("")
        lines.append("（哪些阶段迭代次数最多？哪几轮 avg 分数接近但未过线？为什么？）")
        lines.append("")
        lines.append("### 2. 高频 directive 模式")
        lines.append("")
        lines.append("（跨阶段反复出现的指令类型是什么？指向流程哪一环的系统性问题？）")
        lines.append("")
        lines.append("### 3. 根因归类")
        lines.append("")
        lines.append("（区分偶发问题与系统性问题，给出证据。）")
        lines.append("")
        lines.append("### 4. 流程改进建议（对 autoloop 流程本身）")
        lines.append("")
        lines.append("（逐条列出可执行改进项、责任人、验证方式。）")
        lines.append("")
        lines.append("### 5. rubric 改进建议（对评分细则的校准）")
        lines.append("")
        lines.append("（哪些维度权重或 veto 条款需要调整？依据是什么？）")
        lines.append("")
        retro_path.parent.mkdir(parents=True, exist_ok=True)
        retro_path.write_text("\n".join(lines), encoding="utf-8")
        retro_created = True

    # 把本 run 的 gates/score-history.jsonl 全量行幂等合并进 lessons（FIX-1）
    run_rows = _read_jsonl(rs.dir / "gates" / "score-history.jsonl")
    lessons_dir = rs.root / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    history_path = lessons_dir / "score-history.jsonl"
    _merge_score_history(history_path, rs.data["run_id"], run_rows)
    return retro_path, history_path, len(run_rows), retro_created
