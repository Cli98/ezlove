#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""autoloop CLI 编排器（唯一入口）。

用法：python3 .qoder/skills/autoloop/scripts/harness.py <command>

命令：init / status / list / phase / gate / gate-status / directives /
      continue / report / evolve

退出码：0=成功/通过；1=gate 判定未通过（业务失败）；2=错误或 blocked。
每个命令的输出包含人类可读中文说明 + 一行 `JSON: {...}` 机器可解析信息。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# 确保同目录模块可导入
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import state as st
import scorer
import report as rp

# 项目根目录（本文件位于 <project>/.qoder/skills/autoloop/scripts/，上溯 5 级）
PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ---------------------------------------------------------------------------
# 通用辅助
# ---------------------------------------------------------------------------

def resolve_run(run_id):
    """无 --run 时取最新 run；无任何 run 则报错。"""
    if run_id:
        return run_id
    rid = st.latest_run_id()
    if not rid:
        raise st.AutoloopError("未找到任何运行，请先执行 init")
    return rid


def fmt_scores(scores):
    return ", ".join("%s=%s" % (k, scores[k]) for k in st.EVALUATOR_IDS if k in scores)


def validate_artifact_paths(rs, artifacts):
    """m7 预检：仅校验 artifacts 路径是否越界（不读取文件）。"""
    run_dir = rs.dir.resolve()
    for a in artifacts:
        p = Path(a)
        if not p.is_absolute():
            p = rs.dir / a
        p = p.resolve()
        try:
            p.relative_to(run_dir)
        except ValueError:
            raise st.AutoloopError(
                "产物路径越界：%s（resolve 后 %s），仅允许 run 目录内文件" % (a, p))


def resolve_artifacts(rs, artifacts):
    """解析 --artifacts 路径（相对 run 目录或绝对路径），读取内容并截断。

    m7：产物 resolve 后必须位于 run 目录内，路径越界直接报错。
    返回 (artifact_texts, 相对路径列表)。
    """
    artifact_texts = {}
    rel_list = []
    run_dir = rs.dir.resolve()
    for a in artifacts:
        p = Path(a)
        if not p.is_absolute():
            p = rs.dir / a
        p = p.resolve()
        if not p.exists():
            raise st.AutoloopError("产物文件不存在: %s（相对 run 目录解析为 %s）" % (a, p))
        # m7：产物路径逃逸校验，仅允许 run 目录内文件参与评分
        try:
            p.relative_to(run_dir)
        except ValueError:
            raise st.AutoloopError(
                "产物路径越界：%s（resolve 后 %s），仅允许 run 目录内文件" % (a, p))
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise st.AutoloopError("读取产物失败 %s: %s" % (a, e))
        if len(text) > scorer.ARTIFACT_CHAR_LIMIT:
            text = text[:scorer.ARTIFACT_CHAR_LIMIT] + "\n...[内容过长，已截断至 %d 字符]" % scorer.ARTIFACT_CHAR_LIMIT
        try:
            rel = str(p.relative_to(run_dir))
        except ValueError:
            rel = str(p)
        artifact_texts[rel] = text
        rel_list.append(rel)
    return artifact_texts, rel_list


def read_gate_file(rs, gate_rel):
    data = st.read_json(rs.dir / gate_rel)
    if data is None:
        raise st.AutoloopError("评分门文件不存在: %s" % gate_rel)
    return data


def pending_gate_label(pending):
    """pending_gate 的显示名；信息缺失时返回“评分门信息缺失”（m10，避免 PNone-iterNone）。"""
    if not pending or pending.get("phase") is None or pending.get("iter") is None:
        return "评分门信息缺失"
    return "P%s-iter%s" % (pending.get("phase"), pending.get("iter"))


def collect_git_diff(project_root=None, limit=6000):
    """采集 git diff HEAD 与 git status --short 输出（FIX-5，供 --include-diff 注入提示词）。

    - subprocess 使用 list 参数形式，cwd 为项目根
    - git 不可用（可执行文件不存在）或非 git 仓库（返回码非 0）时打印警告并返回 None
    - 两段输出合计截断至 limit 字符
    """
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    try:
        diff_r = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True,
                                cwd=str(root), timeout=30)
        status_r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True,
                                  cwd=str(root), timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        print("警告: 无法执行 git（%s），跳过代码变更注入" % e, file=sys.stderr)
        return None
    if diff_r.returncode != 0 or status_r.returncode != 0:
        print("警告: git 命令执行失败（非 git 仓库或 git 异常），跳过代码变更注入", file=sys.stderr)
        return None
    text = "$ git status --short\n%s\n\n$ git diff HEAD\n%s" % (
        status_r.stdout.strip(), diff_r.stdout.strip())
    if len(text) > limit:
        text = text[:limit] + "\n...[代码变更过长，已截断至 %d 字符]" % limit
    return text


# ---------------------------------------------------------------------------
# 子命令实现
# ---------------------------------------------------------------------------

def cmd_init(args):
    rs = st.RunState.create(args.requirement)
    pm = rs.phase_meta()
    print("已创建 autoloop 运行 %s" % rs.run_id)
    print("需求: %s" % rs.data["requirement"])
    print("当前阶段: %d/%d %s（%s），第 1 轮" % (rs.phase, rs.phase_count, pm["title"], pm["name"]))
    print("状态: running")
    st.emit_json({
        "run_id": rs.run_id,
        "requirement": rs.data["requirement"],
        "phase": rs.phase,
        "phase_name": pm["name"],
        "iteration": rs.iteration,
        "status": rs.status,
    })
    return 0


def cmd_status(args):
    rid = resolve_run(args.run)
    rs = st.RunState.load(rid)
    pm = rs.phase_meta()
    print("run: %s" % rs.run_id)
    print("需求: %s" % rs.data["requirement"])
    print("阶段: %d/%d %s（%s），第 %d 轮" % (
        rs.phase, rs.phase_count, pm["title"], pm["name"], rs.iteration))
    max_iter = int(st.gate_config().get("max_iterations", 5))
    if rs.status == "awaiting_ingest":
        pending = rs.data.get("pending_gate") or {}
        rec = pending.get("received") or []
        missing = [e for e in st.EVALUATOR_IDS if e not in rec]
        # m10：pending_gate 信息缺失时不打印 PNone-iterNone；无提交时明确“尚无评审提交，等待 …”
        gate_label = pending_gate_label(pending)
        if rec:
            submitted = "已提交 %s，待 %s" % (",".join(rec), ",".join(missing) or "无")
        else:
            submitted = "尚无评审提交，等待 %s" % ("、".join(missing) or "无")
        print("状态: awaiting_ingest（评分门 %s，%s）" % (gate_label, submitted))
    elif rs.status == "blocked":
        # m5：明确区分已完成轮次与待批准轮次
        print("状态: blocked（已完成 %d 轮迭代均未通过，第 %d 轮待批准后开始，执行 continue --run %s 批准后继续）" % (
            rs.iteration - 1, rs.iteration, rs.run_id))
    else:
        print("状态: %s" % rs.status)
    last = rs.data.get("last_gate")
    if last:
        print("最近评分门: %s %s（%s；avg %s / min %s，threshold %s）" % (
            "P%d-iter%d" % (last["phase"], last["iter"]),
            "已通过" if last["passed"] else "未通过",
            fmt_scores(last.get("scores", {})),
            last.get("avg_score"), last.get("min_score"), last.get("threshold")))
        print("  判定理由: %s" % last.get("verdict_reason", ""))
    else:
        print("最近评分门: 尚无")
    st.emit_json({
        "run_id": rs.run_id,
        "phase": rs.phase,
        "phase_name": pm["name"],
        "phase_title": pm["title"],
        "iteration": rs.iteration,
        "status": rs.status,
        "last_gate": last,
    })
    return 0


def cmd_list(args):
    root = st.state_root()
    run_ids = st.list_run_ids(root)
    runs = []
    for rid in run_ids:
        try:
            rs = st.RunState.load(rid, root)
        except (st.AutoloopError, json.JSONDecodeError):
            continue
        pm = rs.phase_meta()
        req = rs.data["requirement"]
        print("%s  P%d/%d %-12s iter%-2d %-15s %s" % (
            rid, rs.phase, rs.phase_count, pm["name"], rs.iteration, rs.status,
            (req[:40] + "…") if len(req) > 40 else req))
        runs.append({
            "run_id": rid, "phase": rs.phase, "phase_name": pm["name"],
            "iteration": rs.iteration, "status": rs.status,
            "requirement": req,
        })
    if not run_ids:
        print("（暂无运行，请先执行 init）")
    st.emit_json({"runs": runs})
    return 0


def cmd_phase(args):
    rid = resolve_run(args.run)
    rs = st.RunState.load(rid)
    pm = rs.phase_meta()
    template = st.SKILL_DIR / "phases" / ("%02d-%s.md" % (pm["n"], pm["name"]))
    artifacts_dir = rs.dir / "artifacts"
    failed = rs.last_failed_gate_in_phase()
    directives_file = str(rs.dir / failed["file"]) if failed else None
    print("run_id: %s" % rs.run_id)
    print("当前阶段: %d/%d %s（%s），第 %d 轮" % (
        pm["n"], rs.phase_count, pm["title"], pm["name"], rs.iteration))
    print("阶段模板: %s（若文件尚不存在，按模板路径约定参照执行）" % template)
    print("产物目录: %s" % artifacts_dir)
    if directives_file:
        print("改进指令: %s（用 directives 命令查看详情）" % directives_file)
    else:
        print("改进指令: 无（当前阶段尚无失败评分门）")
    st.emit_json({
        "run_id": rs.run_id,
        "phase": pm["n"],
        "phase_name": pm["name"],
        "phase_title": pm["title"],
        "iteration": rs.iteration,
        "status": rs.status,
        "template": str(template),
        "artifacts_dir": str(artifacts_dir),
        "directives_file": directives_file,
    })
    return 0


def cmd_gate(args):
    rs = st.RunState.load(args.run)
    # m7：产物路径越界预检先于状态检查（安全校验 fail-fast，任何状态下都立即拒绝）
    validate_artifact_paths(rs, args.artifacts)
    status = rs.data["status"]
    if status == "done":
        raise st.AutoloopError("运行已完成（done），无法再发起评分门")
    if status == "blocked":
        raise st.AutoloopError("运行已 blocked，请先执行 continue --run %s 批准继续" % rs.run_id)
    if status == "awaiting_ingest":
        raise st.AutoloopError("当前状态为 awaiting_ingest，评分门等待评审提交中（请先完成 ingest，可用 gate-status 查看）")

    pm = rs.phase_meta()
    n, k = rs.phase, rs.iteration

    # 解析并记录本阶段产物（含 m7 路径越界校验）
    artifact_texts, rel_list = resolve_artifacts(rs, args.artifacts)
    rs.set_artifacts(rel_list)

    # 重评时引用上一轮改进指令
    prev_directives = rs.current_prev_directives()

    # FIX-5：--include-diff 时采集代码变更注入评审提示词（git 不可用/非仓库时警告跳过）
    diff_text = None
    if args.include_diff:
        diff_text = collect_git_diff()

    # 模式决策：auto → api（配置与密钥齐备时）否则 local；显式 api 不可用时降级并警告
    mode = args.mode
    models_cfg = scorer.load_models_config()
    if mode in ("api", "auto"):
        if scorer.api_ready(models_cfg):
            mode = "api"
        else:
            if mode == "api" or models_cfg:
                print("警告: API 评审不可用（config/models.json 缺失，或 evaluator 的 "
                      "provider/api_key_env 未配置、对应环境变量为空），降级为 local 模式",
                      file=sys.stderr)
            mode = "local"

    if mode == "local":
        prompts, paths = scorer.write_local_prompts(rs, pm, artifact_texts, prev_directives, diff_text)
        rs.open_gate(paths["gate_rel"], n, k)
        print("已发起 local 评分门 %s（阶段 %d/%d %s，第 %d 轮）" % (
            paths["stem"], n, rs.phase_count, pm["title"], k))
        print("提示词文件（每个评审一份，含 persona + 评分细则 + 产物 + 输出 schema）:")
        for ev_id in st.EVALUATOR_IDS:
            print("  %s: %s" % (ev_id, prompts[ev_id]))
        print("状态: awaiting_ingest")
        print("请派遣 3 个评审代理完成评审并 ingest，例如：")
        print("  python3 %s ingest --run %s --evaluator A --file <verdict.json>"
              % (scorer.SCORER_SCRIPT_PATH, rs.run_id))
        st.emit_json({
            "run_id": rs.run_id,
            "gate": paths["stem"],
            "phase": n,
            "iteration": k,
            "mode": "local",
            "status": "awaiting_ingest",
            "prompts": prompts,
            "artifacts": rel_list,
        })
        return 0

    # ---- api 模式：调 3 模型 → 判定 → 推进/迭代/blocked ----
    try:
        evaluators, paths = scorer.run_api_evaluations(
            rs, pm, artifact_texts, prev_directives, diff_text)
    except scorer.InfraError as e:
        # FIX-4：基础设施故障（网络类异常）——本轮不计入迭代，不推进，状态保持不变
        print("基础设施错误：%s，请检查网络/密钥/配置，本轮不计入迭代" % e, file=sys.stderr)
        st.emit_json({
            "run_id": rs.run_id,
            "gate": "P%d-iter%d" % (n, k),
            "phase": n,
            "iteration": k,
            "mode": "api",
            "infra_error": True,
            "passed": None,
            "status": rs.data["status"],
            "iteration_next": rs.data["iteration"],
        })
        return 2
    judged = st.judge(evaluators, st.gate_config())
    gate_data = {
        "phase": n,
        "phase_name": pm["name"],
        "iteration": k,
        "timestamp": st.now_iso(),
        "mode": "api",
        "threshold": judged["threshold"],
        "strategy": judged["strategy"],
        "min_per_model": judged["min_per_model"],
        "evaluators": evaluators,
        "scores": judged["scores"],
        "avg_score": judged["avg_score"],
        "min_score": judged["min_score"],
        "max_score": judged["max_score"],
        "passed": judged["passed"],
        "veto": judged["veto"],
        "directives": judged["directives"],
        "verdict_reason": judged["verdict_reason"],
        "status": "judged",
    }
    st.write_json(paths["gate"], gate_data)
    # FIX-1：判定完成即写入 score-history（P9 复盘权威数据源）
    st.append_score_history(rs, gate_data)
    rs.apply_judged_gate(paths["gate_rel"], judged, n, k)

    print("评分门 %s（api 模式）判定: %s" % (
        paths["stem"], "通过" if judged["passed"] else "未通过"))
    gcfg = st.gate_config()
    cap = float(gcfg.get("no_evidence_cap", 90.0))
    ev_req = bool(gcfg.get("evidence_required", True))
    for ev_id in st.EVALUATOR_IDS:
        ev = evaluators[ev_id]
        note = ""
        if not ev.get("parse_ok"):
            note = "（响应解析失败，按 0 分计）"
        elif (ev_req and not (ev.get("evidence") or [])
              and float(ev.get("score") or 0) > cap):
            # m6：cap 生效时内联标注，避免“高分被压”不可见
            note = "（evidence 空，按 %g 计）" % cap
        print("  %s（%s, %s）: %s 分%s" % (
            ev_id, ev["name"], ev["model"], ev["score"], note))
    print("  avg %s / min %s，threshold %s" % (
        judged["avg_score"], judged["min_score"], judged["threshold"]))
    print("  理由: %s" % judged["verdict_reason"])
    if judged["passed"]:
        if rs.data["status"] == "done":
            print("  最后阶段已通过，运行状态: done")
        else:
            nxt = rs.phase_meta()
            print("  阶段 %d 已通过，进入阶段 %d/%d %s（%s）" % (
                n, nxt["n"], rs.phase_count, nxt["title"], nxt["name"]))
    else:
        if rs.data["status"] == "blocked":
            # m5：明确区分已完成轮次与待批准轮次
            print("  已完成 %d 轮迭代均未通过，第 %d 轮待批准后开始（执行 continue --run %s 批准后继续）。"
                  % (rs.data["iteration"] - 1, rs.data["iteration"], rs.run_id))
        else:
            print("  未通过，进入第 %d 轮迭代（用 directives 命令查看改进指令）。" % rs.data["iteration"])
    st.emit_json({
        "run_id": rs.run_id,
        "gate": paths["stem"],
        "phase": n,
        "iteration": k,
        "mode": "api",
        "passed": judged["passed"],
        "scores": judged["scores"],
        "avg_score": judged["avg_score"],
        "min_score": judged["min_score"],
        "threshold": judged["threshold"],
        "iteration_next": rs.data["iteration"],
        "status": rs.data["status"],
        "directives_count": len(judged["directives"]),
        "verdict_reason": judged["verdict_reason"],
    })
    if rs.data["status"] == "blocked":
        return 2
    return 0 if judged["passed"] else 1


def cmd_gate_status(args):
    rs = st.RunState.load(args.run)
    if rs.data["status"] == "awaiting_ingest":
        pending = rs.data.get("pending_gate") or {}
        gate_rel = pending.get("file") or ""
        gate_data = st.read_json(rs.dir / gate_rel) or {}
        received = sorted((gate_data.get("evaluators") or {}).keys())
        missing = [e for e in st.EVALUATOR_IDS if e not in received]
        # m10：信息缺失时不打印 PNone-iterNone；无提交时明确“尚无评审提交，等待 …”
        gate_label = pending_gate_label(pending)
        print("run: %s" % rs.run_id)
        print("当前评分门 %s: awaiting_ingest" % gate_label)
        if received:
            scores_now = {e: gate_data["evaluators"][e].get("score") for e in received}
            print("已提交: %s（%s）" % (", ".join(received), fmt_scores(scores_now)))
            print("待提交: %s" % (", ".join(missing) or "无"))
        else:
            print("尚无评审提交，等待 %s" % ("、".join(missing) or "无"))
        st.emit_json({
            "run_id": rs.run_id,
            "gate": gate_label,
            "status": "awaiting_ingest",
            "received": received,
            "pending": missing,
        })
        return 0
    last = rs.data.get("last_gate")
    if not last:
        print("run: %s" % rs.run_id)
        print("尚无评分门记录（请先执行 gate 发起）")
        st.emit_json({"run_id": rs.run_id, "gate": None, "status": "none"})
        return 0
    verdict = "passed" if last["passed"] else "failed"
    print("run: %s" % rs.run_id)
    print("最近评分门 P%d-iter%d: %s" % (last["phase"], last["iter"], verdict))
    print("分数: %s（avg %s / min %s，threshold %s）" % (
        fmt_scores(last.get("scores", {})), last.get("avg_score"),
        last.get("min_score"), last.get("threshold")))
    print("判定理由: %s" % last.get("verdict_reason", ""))
    st.emit_json({
        "run_id": rs.run_id,
        "gate": "P%d-iter%d" % (last["phase"], last["iter"]),
        "status": verdict,
        "scores": last.get("scores", {}),
        "avg_score": last.get("avg_score"),
        "min_score": last.get("min_score"),
        "threshold": last.get("threshold"),
        "verdict_reason": last.get("verdict_reason", ""),
    })
    return 0


def cmd_directives(args):
    rs = st.RunState.load(args.run)
    failed = rs.last_failed_gate_in_phase()
    if not failed:
        print("当前无待处理改进指令（当前阶段尚无未通过的评分门）。")
        st.emit_json({"run_id": rs.run_id, "count": 0, "directives": []})
        return 0
    gate_data = read_gate_file(rs, failed["file"])
    directives = gate_data.get("directives") or []
    print("run: %s" % rs.run_id)
    print("来自 %s 的改进指令（共 %d 条，按 critical>major>minor 排序）:" % (
        "P%d-iter%d" % (rs.data["phase"], failed["iter"]), len(directives)))
    for d in directives:
        print("%s [%s]（评审: %s）%s" % (
            d["id"], d["severity"], ",".join(d.get("evaluators", [])), d["description"]))
        if d.get("action"):
            print("    行动: %s" % d["action"])
    st.emit_json({
        "run_id": rs.run_id,
        "gate_file": failed["file"],
        "count": len(directives),
        "directives": directives,
    })
    return 0


def cmd_continue(args):
    rs = st.RunState.load(args.run)
    rs.approve_continue()
    print("run: %s" % rs.run_id)
    print("已批准继续: 阶段 %d（%s）iteration=%d（继续累加），状态恢复 running" % (
        rs.phase, rs.phase_meta()["title"], rs.iteration))
    st.emit_json({
        "run_id": rs.run_id,
        "status": rs.status,
        "phase": rs.phase,
        "iteration": rs.iteration,
    })
    return 0


def cmd_report(args):
    path = rp.generate_report(args.run)
    print("已生成最终报告: %s" % path)
    st.emit_json({"run_id": args.run, "report_path": str(path)})
    return 0


def cmd_evolve(args):
    retro_path, history_path, records, retro_created = rp.generate_evolve(args.run)
    if retro_created:
        print("已生成复盘骨架（含各阶段迭代统计 JSON 块，供 agent 填写）: %s" % retro_path)
    else:
        # FIX-1：复盘产物已存在时绝不覆盖
        print("复盘产物已存在，保留原文: %s" % retro_path)
    print("已合并评分历史（本 run 共 %d 行，按 run_id 幂等去重）: %s" % (records, history_path))
    st.emit_json({
        "run_id": args.run,
        "retro_path": str(retro_path),
        "retro_created": retro_created,
        "score_history_path": str(history_path),
        "records": records,
    })
    return 0


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="harness.py", description="autoloop 研发闭环引擎（确定性部分）")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="创建新运行")
    p.add_argument("requirement", help="一句话需求")

    p = sub.add_parser("status", help="查看运行状态（默认最新 run）")
    p.add_argument("--run", default=None)

    sub.add_parser("list", help="列出所有运行")

    p = sub.add_parser("phase", help="查看当前阶段执行上下文（默认最新 run）")
    p.add_argument("--run", default=None)

    p = sub.add_parser("gate", help="发起当前阶段评分门")
    p.add_argument("--run", required=True)
    p.add_argument("--artifacts", nargs="*", default=[], metavar="F",
                   help="参与评分的产物路径（相对 run 目录或绝对路径）")
    p.add_argument("--mode", choices=["auto", "api", "local"], default="auto")
    p.add_argument("--include-diff", action="store_true",
                   help="采集 git diff HEAD / git status --short 注入评审提示词（代码类阶段 P4-P6 推荐）")

    p = sub.add_parser("gate-status", help="查看当前评分门状态")
    p.add_argument("--run", required=True)

    p = sub.add_parser("directives", help="查看待处理改进指令")
    p.add_argument("--run", required=True)

    p = sub.add_parser("continue", help="blocked 状态下批准继续")
    p.add_argument("--run", required=True)

    p = sub.add_parser("report", help="生成最终报告")
    p.add_argument("--run", required=True)

    p = sub.add_parser("evolve", help="生成复盘骨架并追加评分历史")
    p.add_argument("--run", required=True)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "init": cmd_init,
        "status": cmd_status,
        "list": cmd_list,
        "phase": cmd_phase,
        "gate": cmd_gate,
        "gate-status": cmd_gate_status,
        "directives": cmd_directives,
        "continue": cmd_continue,
        "report": cmd_report,
        "evolve": cmd_evolve,
    }
    try:
        return handlers[args.command](args)
    except st.AutoloopError as e:
        print("错误: %s" % e, file=sys.stderr)
        return 2
    except (ValueError, OSError, KeyError) as e:
        print("错误: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
