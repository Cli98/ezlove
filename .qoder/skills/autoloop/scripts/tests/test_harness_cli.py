#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_harness_cli：CLI 端到端测试（subprocess 隔离 AUTOLOOP_STATE_DIR，全部离线）。"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
HARNESS = SCRIPTS_DIR / "harness.py"
SCORER = SCRIPTS_DIR / "scorer.py"
PROJECT_ROOT = SCRIPTS_DIR.parents[3]  # .qoder/skills/autoloop/scripts → 项目根

# 进程内测试需要直接调用 harness/scorer/state 模块
sys.path.insert(0, str(SCRIPTS_DIR))
import harness  # noqa: E402
import scorer  # noqa: E402
import state as st  # noqa: E402

REQUIREMENT = "让子女通过分享日常守护独居老人"


def parse_json_line(stdout):
    """从 CLI 输出中提取 `JSON: {...}` 行。"""
    for line in stdout.splitlines():
        if line.startswith("JSON: "):
            return json.loads(line[len("JSON: "):])
    raise AssertionError("输出中未找到 JSON 行:\n%s" % stdout)


def run_cli(script, args, state_dir):
    """以隔离的环境运行 CLI 子进程。"""
    env = os.environ.copy()
    env["AUTOLOOP_STATE_DIR"] = state_dir
    # 清除可能存在的评审密钥，确保 auto 模式降级为 local
    for k in ("AUTOLOOP_EVAL_A_KEY", "AUTOLOOP_EVAL_B_KEY", "AUTOLOOP_EVAL_C_KEY"):
        env.pop(k, None)
    return subprocess.run(
        [sys.executable, str(script)] + args,
        capture_output=True, text=True, env=env, cwd=str(PROJECT_ROOT))


def verdict_obj(ev, score, issues=None, evidence=("证据：产物第 1 行",), veto=None):
    return {
        "evaluator": ev,
        "score": score,
        "dimension_scores": {"clarity": score},
        "strengths": ["结构清晰"],
        "issues": issues or [],
        "evidence": list(evidence),
        "veto": veto,
    }


class TestEndToEnd(unittest.TestCase):
    """端到端：init → phase → gate(local) → ingest 低分失败 → 再评高分通过 → 9 阶段 → done → report → evolve。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="autoloop-cli-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- 辅助 ----

    def harness(self, *args):
        return run_cli(HARNESS, list(args), self.tmp)

    def scorer_cli(self, *args):
        return run_cli(SCORER, list(args), self.tmp)

    def write_verdict(self, obj):
        p = Path(self.tmp) / ("verdict-%s-%s.json" % (obj["evaluator"], obj["score"]))
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return str(p)

    def ingest_high(self, run_id):
        """三个高分评审提交（带证据），期望通过。"""
        last = None
        for ev in ("A", "B", "C"):
            obj = verdict_obj(ev, 96 + "ABC".index(ev))
            last = self.scorer_cli("ingest", "--run", run_id, "--evaluator", ev,
                                   "--file", self.write_verdict(obj))
        return last

    # ---- 测试 ----

    def test_full_lifecycle(self):
        # 1. init
        r = self.harness("init", REQUIREMENT)
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        run_id = payload["run_id"]
        self.assertEqual(payload["phase"], 1)
        self.assertEqual(payload["status"], "running")
        run_dir = Path(self.tmp) / run_id
        self.assertTrue((run_dir / "state.json").exists())

        # 2. status（无 --run，默认最新）
        r = self.harness("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        self.assertEqual(payload["run_id"], run_id)
        self.assertEqual(payload["phase"], 1)
        self.assertEqual(payload["iteration"], 1)
        self.assertIn("需求澄清", r.stdout)

        # 3. phase
        r = self.harness("phase")
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        self.assertTrue(payload["template"].endswith("phases/01-intake.md"), payload["template"])
        self.assertTrue(payload["artifacts_dir"].endswith("artifacts"))
        self.assertIsNone(payload["directives_file"])

        # 4. 写产物
        art = run_dir / "artifacts" / "P1-requirement-card.md"
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text("# 需求卡\n\n目标：守护独居老人。验收：已读回执率 95%%。\n", encoding="utf-8")

        # 5. gate local：生成 3 个 prompts，status=awaiting_ingest
        r = self.harness("gate", "--run", run_id, "--mode", "local",
                         "--artifacts", "artifacts/P1-requirement-card.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        self.assertEqual(payload["status"], "awaiting_ingest")
        self.assertEqual(payload["mode"], "local")
        self.assertIn("请派遣 3 个评审代理", r.stdout)
        prompts_dir = run_dir / "gates" / "P1-iter1.prompts"
        for ev in ("A", "B", "C"):
            p = prompts_dir / (ev + ".md")
            self.assertTrue(p.exists(), "缺少提示词文件 %s" % p)
            content = p.read_text(encoding="utf-8")
            # persona
            self.assertIn("资深产品专家" if ev == "A" else ("资深研发专家" if ev == "B" else "质量仲裁"), content)
            # 该阶段 rubric 维度
            self.assertIn("clarity", content)
            self.assertIn("一票否决", content)
            # 需求原文与产物内容
            self.assertIn(REQUIREMENT, content)
            self.assertIn("守护独居老人", content)
            # 输出 schema 与提交方式
            self.assertIn("dimension_scores", content)
            self.assertIn("ingest", content)
        # state.json 更新为 awaiting_ingest，且 artifacts 记录进当前 phase 条目
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "awaiting_ingest")
        self.assertEqual(state["phases"]["1"]["artifacts"],
                         ["artifacts/P1-requirement-card.md"])

        # 6. gate-status：awaiting_ingest，缺 A/B/C
        r = self.harness("gate-status", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        self.assertEqual(payload["status"], "awaiting_ingest")
        self.assertEqual(payload["pending"], ["A", "B", "C"])

        # 7. ingest A/B/C 低分 → failed（iteration=2，directives 正确）
        v_a = verdict_obj("A", 90, issues=[
            {"severity": "major", "description": "非目标未列出", "directive": "补充非目标清单"}])
        v_b = verdict_obj("B", 88, issues=[
            {"severity": "major", "description": "非目标未列出", "directive": ""}])
        v_c = verdict_obj("C", 85, issues=[
            {"severity": "critical", "description": "验收标准不可量化", "directive": "给出可量化指标"}])
        r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", "A",
                            "--file", self.write_verdict(v_a))
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        self.assertEqual(payload["pending"], ["B", "C"])
        r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", "B",
                            "--file", self.write_verdict(v_b))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(parse_json_line(r.stdout)["pending"], ["C"])
        r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", "C",
                            "--file", self.write_verdict(v_c))
        self.assertEqual(r.returncode, 1, r.stderr)  # gate 判定未通过 → 1
        self.assertIn("GATE_RESULT: failed", r.stdout)
        payload = parse_json_line(r.stdout)
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["iteration_next"], 2)

        # state：iteration=2，running；gate 文件含 directives
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["iteration"], 2)
        self.assertEqual(state["status"], "running")
        gate = json.loads((run_dir / "gates" / "P1-iter1.json").read_text(encoding="utf-8"))
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["mode"], "local")
        self.assertEqual(gate["threshold"], 95.0)
        self.assertIn("min score 85.0 < threshold 95.0", gate["verdict_reason"])
        # directives 合并：两个 major“非目标未列出”合并为 1 条 + 1 条 critical，critical 排最前
        self.assertEqual(len(gate["directives"]), 2)
        self.assertEqual(gate["directives"][0]["severity"], "critical")
        self.assertEqual(gate["directives"][1]["severity"], "major")
        self.assertEqual(set(gate["directives"][1]["evaluators"]), {"A", "B"})

        # 8. status：显示最近 gate 未通过
        r = self.harness("status", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("未通过", r.stdout)
        payload = parse_json_line(r.stdout)
        self.assertEqual(payload["iteration"], 2)

        # 9. directives：输出改进指令
        r = self.harness("directives", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("D1 [critical]", r.stdout)
        self.assertIn("D2 [major]", r.stdout)
        payload = parse_json_line(r.stdout)
        self.assertEqual(payload["count"], 2)

        # 10. gate-status：failed 摘要 + 分数 + threshold + verdict_reason
        r = self.harness("gate-status", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(payload["threshold"], 95.0)
        self.assertIn("verdict_reason", payload)

        # 11. 再 gate → P1-iter2 提示词（含上轮 directives）
        r = self.harness("gate", "--run", run_id, "--mode", "local",
                         "--artifacts", "artifacts/P1-requirement-card.md")
        self.assertEqual(r.returncode, 0, r.stderr)
        p2 = (run_dir / "gates" / "P1-iter2.prompts" / "A.md").read_text(encoding="utf-8")
        self.assertIn("上一轮改进指令", p2)
        self.assertIn("D1", p2)

        # 12. ingest 高分 ×3 → passed，推进到阶段 2
        r = self.ingest_high(run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("GATE_RESULT: passed", r.stdout)
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], 2)
        self.assertEqual(state["iteration"], 1)
        self.assertEqual(state["phases"]["1"]["status"], "passed")
        self.assertEqual(state["phases"]["1"]["iterations"], 2)
        # phase 命令现在指向阶段 2 模板
        r = self.harness("phase", "--run", run_id)
        payload = parse_json_line(r.stdout)
        self.assertTrue(payload["template"].endswith("phases/02-product.md"))

        # 13. 快速走完阶段 2-9（每阶段 gate local + 高分 ingest）
        for phase in range(2, 10):
            r = self.harness("gate", "--run", run_id, "--mode", "local")
            self.assertEqual(r.returncode, 0,
                             "阶段 %d gate 失败: %s" % (phase, r.stderr))
            r = self.ingest_high(run_id)
            self.assertEqual(r.returncode, 0,
                             "阶段 %d ingest 失败: %s\n%s" % (phase, r.stderr, r.stdout))
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "done")
        self.assertEqual(state["phase"], 9)
        self.assertEqual(state["phases"]["9"]["status"], "passed")

        # 14. report 生成
        r = self.harness("report", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        report_path = Path(payload["report_path"])
        self.assertTrue(report_path.exists())
        content = report_path.read_text(encoding="utf-8")
        self.assertIn(REQUIREMENT, content)
        self.assertIn("阶段评分总览", content)
        self.assertIn("需求澄清（intake）", content)
        self.assertIn("是", content)  # 阶段 1 曾失败重试
        self.assertIn("改进指令统计", content)

        # 15. evolve 生成 retro 骨架 + score-history.jsonl 幂等合并（FIX-1：每轮 gate 一行）
        r = self.harness("evolve", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        retro = Path(payload["retro_path"])
        self.assertTrue(retro.exists())
        retro_content = retro.read_text(encoding="utf-8")
        self.assertIn("```json", retro_content)
        stats = json.loads(retro_content.split("```json")[1].split("```")[0])
        self.assertEqual(len(stats), 9)
        self.assertEqual(stats[0]["iterations"], 2)
        history = Path(payload["score_history_path"])
        self.assertTrue(history.exists())
        lines = history.read_text(encoding="utf-8").strip().splitlines()
        # 阶段 1 两轮（iter1 失败 + iter2 通过）+ 阶段 2-9 各一轮 = 10 行
        self.assertEqual(len(lines), 10)
        rec = json.loads(lines[0])
        self.assertEqual(rec["run_id"], run_id)
        self.assertEqual(rec["phase"], 1)
        self.assertEqual(rec["phase_name"], "intake")
        self.assertEqual(rec["iter"], 1)
        self.assertFalse(rec["passed"])
        self.assertIn("avg", rec)
        self.assertIn("directives_count", rec)
        # run 内的权威数据源同样存在且行数一致
        run_sh = (run_dir / "gates" / "score-history.jsonl")
        self.assertEqual(len(run_sh.read_text(encoding="utf-8").strip().splitlines()), 10)
        # 再次 evolve 幂等：不产生重复行
        r = self.harness("evolve", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("复盘产物已存在，保留原文", r.stdout)
        self.assertEqual(
            len(history.read_text(encoding="utf-8").strip().splitlines()), 10)

        # 16. list 命令
        r = self.harness("list")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(run_id, r.stdout)
        payload = parse_json_line(r.stdout)
        self.assertEqual(len(payload["runs"]), 1)

    def test_gate_rejects_wrong_states(self):
        r = self.harness("init", "状态机测试需求")
        run_id = parse_json_line(r.stdout)["run_id"]
        # awaiting_ingest 状态下重复 gate → 错误（退出码 2）
        r = self.harness("gate", "--run", run_id, "--mode", "local")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.harness("gate", "--run", run_id, "--mode", "local")
        self.assertEqual(r.returncode, 2)
        self.assertIn("awaiting_ingest", r.stderr)
        # 不存在的 run → 错误
        r = self.harness("status", "--run", "no-such-run")
        self.assertEqual(r.returncode, 2)
        # 空 state 目录下 status（无 --run）→ 错误
        empty = tempfile.mkdtemp(prefix="autoloop-empty-")
        try:
            r = run_cli(HARNESS, ["status"], empty)
            self.assertEqual(r.returncode, 2)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    def test_ingest_validates_verdict_schema(self):
        self.harness("init", "verdict 校验测试")
        run_id = parse_json_line(run_cli(HARNESS, ["status"], self.tmp).stdout)["run_id"]
        self.harness("gate", "--run", run_id, "--mode", "local")
        # 非法 severity → 拒绝
        bad = verdict_obj("A", 90, issues=[
            {"severity": "blocker", "description": "x", "directive": "y"}])
        r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", "A",
                            "--file", self.write_verdict(bad))
        self.assertEqual(r.returncode, 2)
        self.assertIn("校验失败", r.stderr)
        # evaluator 不匹配 → 拒绝
        r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", "B",
                            "--file", self.write_verdict(verdict_obj("A", 90)))
        self.assertEqual(r.returncode, 2)
        # evidence 为空的高分 → cap 90 → 失败路径（用于验证 cap 生效）
        for ev in ("A", "B"):
            obj = verdict_obj(ev, 99, evidence=())
            r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", ev,
                                "--file", self.write_verdict(obj))
            self.assertEqual(r.returncode, 0, r.stderr)
        obj = verdict_obj("C", 99, evidence=())
        r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", "C",
                            "--file", self.write_verdict(obj))
        self.assertEqual(r.returncode, 1)  # 全部被 cap 至 90 → 未通过
        gate = json.loads((Path(self.tmp) / run_id / "gates" / "P1-iter1.json")
                          .read_text(encoding="utf-8"))
        self.assertEqual(gate["scores"]["A"], 90)
        self.assertIn("cap", gate["verdict_reason"])

    def test_blocked_and_continue_cli(self):
        """CLI 层验证 blocked → continue 恢复（跑满 5 次失败）。"""
        self.harness("init", "blocked 流程测试")
        run_id = parse_json_line(run_cli(HARNESS, ["status"], self.tmp).stdout)["run_id"]
        run_dir = Path(self.tmp) / run_id
        for i in range(1, 6):  # max_iterations = 5
            r = self.harness("gate", "--run", run_id, "--mode", "local")
            self.assertEqual(r.returncode, 0, r.stderr)
            gate_rel = "gates/P1-iter%d.json" % i
            self.assertTrue((run_dir / gate_rel).exists())
            for ev in ("A", "B", "C"):
                obj = verdict_obj(ev, 80, issues=[
                    {"severity": "major", "description": "问题%d" % i, "directive": "修"}])
                r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", ev,
                                    "--file", self.write_verdict(obj))
            # 第 5 次失败后 blocked → ingest 退出码 2
            if i < 5:
                self.assertEqual(r.returncode, 1, r.stderr)
            else:
                self.assertEqual(r.returncode, 2, r.stderr)
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["iteration"], 6)
        # blocked 后继续 gate → 错误
        r = self.harness("gate", "--run", run_id, "--mode", "local")
        self.assertEqual(r.returncode, 2)
        # continue 恢复 running，iteration 继续累加
        r = self.harness("continue", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = parse_json_line(r.stdout)
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["iteration"], 6)
        # 恢复后可继续 gate（P1-iter6）
        r = self.harness("gate", "--run", run_id, "--mode", "local")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((run_dir / "gates" / "P1-iter6.json").exists())


class TestIngestAndGateGuards(unittest.TestCase):
    """FIX-8：重复 ingest 拒绝、score-history 落盘、artifacts 越界、并发 ingest。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="autoloop-cli-guard-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def harness(self, *args):
        return run_cli(HARNESS, list(args), self.tmp)

    def scorer_cli(self, *args):
        return run_cli(SCORER, list(args), self.tmp)

    def write_verdict(self, obj):
        p = Path(self.tmp) / ("verdict-%s-%s.json" % (obj["evaluator"], obj["score"]))
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return str(p)

    def _init_and_open_gate(self):
        r = self.harness("init", "守卫测试需求")
        run_id = parse_json_line(r.stdout)["run_id"]
        self.harness("gate", "--run", run_id, "--mode", "local")
        return run_id, Path(self.tmp) / run_id

    def test_ingest_duplicate_rejected(self):
        """重复 ingest 同一 evaluator → 拒绝（退出码非 0）。"""
        run_id, _ = self._init_and_open_gate()
        f = self.write_verdict(verdict_obj("A", 90))
        r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", "A", "--file", f)
        self.assertEqual(r.returncode, 0, r.stderr)
        # 同一 evaluator 重复提交 → 拒绝（exit 非 0）
        r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", "A", "--file", f)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("重复提交", r.stderr)
        # gate 文件仍只有 A
        gate = json.loads((Path(self.tmp) / run_id / "gates" / "P1-iter1.json")
                          .read_text(encoding="utf-8"))
        self.assertEqual(set(gate["evaluators"].keys()), {"A"})

    def test_score_history_appended_on_judge(self):
        """每次 gate 判定完成后，<run>/gates/score-history.jsonl 追加一行（FIX-1）。"""
        run_id, run_dir = self._init_and_open_gate()
        r = None
        for ev in ("A", "B", "C"):
            obj = verdict_obj(ev, 80, issues=[
                {"severity": "major", "description": "覆盖不足", "directive": "补场景"}])
            r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", ev,
                                "--file", self.write_verdict(obj))
        self.assertEqual(r.returncode, 1, r.stderr)
        sh = run_dir / "gates" / "score-history.jsonl"
        self.assertTrue(sh.exists(), "缺少 gates/score-history.jsonl")
        lines = sh.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertEqual(rec["run_id"], run_id)
        self.assertEqual(rec["phase"], 1)
        self.assertEqual(rec["phase_name"], "intake")
        self.assertEqual(rec["iter"], 1)
        self.assertFalse(rec["passed"])
        self.assertEqual(rec["scores"], {"A": 80, "B": 80, "C": 80})
        self.assertEqual(rec["avg"], 80.0)
        self.assertEqual(rec["min"], 80)
        self.assertEqual(rec["directives_count"], 1)  # 同描述 issue 去重合并为 1 条
        self.assertIn("ts", rec)

    def test_gate_artifacts_path_escape_rejected(self):
        """m7：artifacts 路径越界（run 目录外）→ 报错退出 2。"""
        # 故意先开一个评分门（awaiting_ingest 状态）：验证越界预检 fail-fast，
        # 无论状态如何都先拒绝非法路径，而不是报状态错误
        run_id, _ = self._init_and_open_gate()
        outside = Path(self.tmp) / "outside.md"
        outside.write_text("外部文件", encoding="utf-8")
        # run 目录外绝对路径 → 拒绝
        r = self.harness("gate", "--run", run_id, "--mode", "local",
                         "--artifacts", str(outside))
        self.assertEqual(r.returncode, 2)
        self.assertIn("越界", r.stderr)
        self.assertIn("仅允许 run 目录内文件", r.stderr)

    def test_concurrent_ingest_serialized(self):
        """FIX-2：两进程同时 ingest A/B，文件锁串行化，两个 verdict 均保留且状态一致。"""
        run_id, run_dir = self._init_and_open_gate()
        files = {}
        for ev in ("A", "B", "C"):
            obj = verdict_obj(ev, 80, issues=[
                {"severity": "major", "description": "问题", "directive": "修"}])
            files[ev] = self.write_verdict(obj)
        # 并行启动 A、B 两个 ingest 进程（同一 run、不同 evaluator）
        env = os.environ.copy()
        env["AUTOLOOP_STATE_DIR"] = self.tmp
        for k in ("AUTOLOOP_EVAL_A_KEY", "AUTOLOOP_EVAL_B_KEY", "AUTOLOOP_EVAL_C_KEY"):
            env.pop(k, None)
        procs = []
        for ev in ("A", "B"):
            cmd = [sys.executable, str(SCORER), "ingest", "--run", run_id,
                   "--evaluator", ev, "--file", files[ev]]
            procs.append((ev, subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env=env, cwd=str(PROJECT_ROOT))))
        for ev, p in procs:
            _, err = p.communicate()
            self.assertEqual(p.returncode, 0, "评审 %s 并发 ingest 失败: %s" % (ev, err))
        # 两个 verdict 都保留，无状态矛盾
        gate = json.loads((run_dir / "gates" / "P1-iter1.json").read_text(encoding="utf-8"))
        self.assertEqual(set(gate["evaluators"].keys()), {"A", "B"})
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(state["pending_gate"]["received"]), ["A", "B"])
        self.assertEqual(state["status"], "awaiting_ingest")
        # C 提交触发判定（80 分 → 失败，iteration=2）
        r = self.scorer_cli("ingest", "--run", run_id, "--evaluator", "C",
                            "--file", files["C"])
        self.assertEqual(r.returncode, 1, r.stderr)
        state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["iteration"], 2)
        self.assertEqual(state["status"], "running")


class TestEvolveGuards(unittest.TestCase):
    """FIX-8：evolve 非 done 拒绝、P9-retro 不覆盖、score-history 幂等。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="autoloop-cli-evolve-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def harness(self, *args):
        return run_cli(HARNESS, list(args), self.tmp)

    def scorer_cli(self, *args):
        return run_cli(SCORER, list(args), self.tmp)

    def write_verdict(self, obj):
        p = Path(self.tmp) / ("verdict-%s-%s.json" % (obj["evaluator"], obj["score"]))
        p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        return str(p)

    def ingest_high(self, run_id):
        last = None
        for ev in ("A", "B", "C"):
            obj = verdict_obj(ev, 96 + "ABC".index(ev))
            last = self.scorer_cli("ingest", "--run", run_id, "--evaluator", ev,
                                   "--file", self.write_verdict(obj))
        return last

    def test_evolve_guards_and_idempotency(self):
        # 非 done 状态 → exit 2
        r = self.harness("init", "evolve 守卫测试")
        run_id = parse_json_line(r.stdout)["run_id"]
        run_dir = Path(self.tmp) / run_id
        r = self.harness("evolve", "--run", run_id)
        self.assertEqual(r.returncode, 2)
        self.assertIn("done", r.stderr)
        # 快进 9 个阶段至 done（每阶段 1 轮通过）
        for _ in range(1, 10):
            self.harness("gate", "--run", run_id, "--mode", "local")
            r = self.ingest_high(run_id)
            self.assertEqual(r.returncode, 0, r.stderr)
        # evolve：生成骨架 + 合并本 run 9 行
        r = self.harness("evolve", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("已生成复盘骨架", r.stdout)
        history = Path(self.tmp) / "lessons" / "score-history.jsonl"
        lines = history.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 9)
        # P9-retro.md 已存在 → 绝不覆盖，保留原文
        retro = run_dir / "artifacts" / "P9-retro.md"
        self.assertIn("自进化复盘", retro.read_text(encoding="utf-8"))
        retro.write_text("# 人工复盘（不可覆盖）\n", encoding="utf-8")
        r = self.harness("evolve", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("复盘产物已存在，保留原文", r.stdout)
        self.assertEqual(retro.read_text(encoding="utf-8"), "# 人工复盘（不可覆盖）\n")
        # 再次 evolve：score-history 不重复（幂等）
        r = self.harness("evolve", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(history.read_text(encoding="utf-8").strip().splitlines()), 9)
        # 其他 run 的历史行保留（按 run_id 整段替换，不误伤）
        other = {"run_id": "other-run", "phase": 1, "avg": 88.0}
        history.write_text(json.dumps(other, ensure_ascii=False) + "\n"
                           + history.read_text(encoding="utf-8"), encoding="utf-8")
        r = self.harness("evolve", "--run", run_id)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = history.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 10)
        self.assertEqual(json.loads(lines[0])["run_id"], "other-run")
        self.assertTrue(all(json.loads(x)["run_id"] == run_id for x in lines[1:]))


class InProcessTestBase(unittest.TestCase):
    """进程内调用 harness.main 的测试基类（隔离 AUTOLOOP_STATE_DIR 并捕获输出）。"""

    def setUp(self):
        self._old_env = os.environ.get("AUTOLOOP_STATE_DIR")
        self.tmp = tempfile.mkdtemp(prefix="autoloop-ip-test-")
        os.environ["AUTOLOOP_STATE_DIR"] = self.tmp

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("AUTOLOOP_STATE_DIR", None)
        else:
            os.environ["AUTOLOOP_STATE_DIR"] = self._old_env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, argv):
        """运行 harness.main 并捕获输出，返回 (returncode, stdout, stderr)。"""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = harness.main(argv)
        return rc, out.getvalue(), err.getvalue()


class TestGateInfraFailure(InProcessTestBase):
    """FIX-4：api 模式网络类异常 → gate 退出码 2，iteration 不变，状态保持。"""

    def setUp(self):
        super().setUp()
        os.environ["AUTOLOOP_TEST_KEY"] = "k"

    def tearDown(self):
        os.environ.pop("AUTOLOOP_TEST_KEY", None)
        super().tearDown()

    @staticmethod
    def _models_cfg():
        return {"evaluators": {e: {
            "provider": "openai_compatible",
            "base_url": "http://127.0.0.1:1",
            "api_key_env": "AUTOLOOP_TEST_KEY",
            "model": "test-model",
            "timeout_seconds": 5,
        } for e in st.EVALUATOR_IDS}}

    def test_gate_api_network_error_exit2_iteration_unchanged(self):
        rs = st.RunState.create("api infra 测试")
        with mock.patch.object(scorer, "load_models_config",
                               return_value=self._models_cfg()), \
             mock.patch.object(urllib.request, "urlopen",
                               side_effect=urllib.error.URLError("connection refused")):
            rc, out, err = self.run_main(["gate", "--run", rs.run_id, "--mode", "api"])
        self.assertEqual(rc, 2)
        self.assertIn("基础设施错误", err)
        self.assertIn("评审 A 调用失败", err)
        self.assertIn("请检查网络/密钥/配置", err)
        self.assertIn("本轮不计入迭代", err)
        # iteration 不变、不推进、状态回 running
        rs2 = st.RunState.load(rs.run_id)
        self.assertEqual(rs2.data["iteration"], 1)
        self.assertEqual(rs2.data["status"], "running")
        self.assertEqual(rs2.data["phase"], 1)
        self.assertIsNone(rs2.data.get("last_gate"))
        # 已完成 evaluator 的 raw 保留在 gates/P1-iter1.raw/
        raw_dir = rs2.dir / "gates" / "P1-iter1.raw"
        for ev in st.EVALUATOR_IDS:
            p = raw_dir / (ev + ".md")
            self.assertTrue(p.exists(), "缺少 raw 存档 %s.md" % ev)
            self.assertIn("基础设施错误", p.read_text(encoding="utf-8"))


class TestGateApiEvidenceCapNote(InProcessTestBase):
    """m6：api 模式分数展示在 cap 生效时内联标注“（evidence 空，按 90 计）”。"""

    def test_gate_api_prints_cap_note(self):
        os.environ["AUTOLOOP_TEST_KEY"] = "k"
        try:
            rs = st.RunState.create("cap 标注测试")
            content = json.dumps({
                "evaluator": "X", "score": 99, "dimension_scores": {},
                "strengths": [], "issues": [], "evidence": [], "veto": None,
            }, ensure_ascii=False)
            payload = json.dumps({"choices": [{"message": {"content": content}}]})
            models_cfg = {"evaluators": {e: {
                "provider": "openai_compatible",
                "base_url": "http://x", "api_key_env": "AUTOLOOP_TEST_KEY",
                "model": "m",
            } for e in st.EVALUATOR_IDS}}
            with mock.patch.object(scorer, "load_models_config",
                                   return_value=models_cfg), \
                 mock.patch.object(urllib.request, "urlopen",
                                   side_effect=lambda req, timeout=None:
                                       io.BytesIO(payload.encode("utf-8"))):
                rc, out, err = self.run_main(["gate", "--run", rs.run_id, "--mode", "api"])
            self.assertEqual(rc, 1)  # 99 被 cap 至 90 → 未通过
            self.assertIn("（evidence 空，按 90 计）", out)
            # score-history 已写入（api 判定路径）
            sh = rs.dir / "gates" / "score-history.jsonl"
            self.assertEqual(len(sh.read_text(encoding="utf-8").strip().splitlines()), 1)
        finally:
            os.environ.pop("AUTOLOOP_TEST_KEY", None)


class TestIncludeDiff(InProcessTestBase):
    """FIX-5：--include-diff 采集 git 变更注入评审提示词。"""

    def test_local_prompt_contains_diff(self):
        rs = st.RunState.create("diff 注入测试")
        art = rs.dir / "artifacts" / "P1-card.md"
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text("# 需求卡\n", encoding="utf-8")
        with mock.patch.object(harness, "collect_git_diff", return_value="FAKE_DIFF_CONTENT"):
            rc, out, err = self.run_main([
                "gate", "--run", rs.run_id, "--mode", "local", "--include-diff",
                "--artifacts", "artifacts/P1-card.md"])
        self.assertEqual(rc, 0, err)
        for ev in st.EVALUATOR_IDS:
            prompt = (rs.dir / "gates" / "P1-iter1.prompts" / (ev + ".md")).read_text(
                encoding="utf-8")
            self.assertIn("## 代码变更（供代码类阶段评审参考）", prompt)
            self.assertIn("FAKE_DIFF_CONTENT", prompt)

    def test_collect_git_diff_mocked_subprocess(self):
        # mock subprocess：git 可用且有输出 → 文本包含两段命令输出
        def fake_run(cmd, **kw):
            if cmd[:2] == ["git", "diff"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="+diff line", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="M a.py", stderr="")
        with mock.patch.object(harness.subprocess, "run", side_effect=fake_run):
            text = harness.collect_git_diff()
        self.assertIn("git status --short", text)
        self.assertIn("git diff HEAD", text)
        self.assertIn("M a.py", text)
        self.assertIn("+diff line", text)

    def test_collect_git_diff_truncated(self):
        # 输出超过 6000 字符 → 截断并标注
        def fake_run(cmd, **kw):
            if cmd[:2] == ["git", "diff"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="x" * 9000, stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        with mock.patch.object(harness.subprocess, "run", side_effect=fake_run):
            text = harness.collect_git_diff()
        self.assertLessEqual(len(text), 6100)
        self.assertIn("已截断", text)

    def test_collect_git_diff_not_a_repo(self):
        # git 返回非 0（非 git 仓库）→ 警告并返回 None
        bad = subprocess.CompletedProcess(["git", "diff"], 128, stdout="",
                                          stderr="fatal: not a git repository")
        err = io.StringIO()
        with mock.patch.object(harness.subprocess, "run", return_value=bad):
            with contextlib.redirect_stderr(err):
                self.assertIsNone(harness.collect_git_diff())
        self.assertIn("警告", err.getvalue())

    def test_collect_git_diff_git_missing(self):
        # git 可执行不存在 → 警告并返回 None
        err = io.StringIO()
        with mock.patch.object(harness.subprocess, "run", side_effect=FileNotFoundError("git")):
            with contextlib.redirect_stderr(err):
                self.assertIsNone(harness.collect_git_diff())
        self.assertIn("警告", err.getvalue())


class TestGateIncludeDiffCli(unittest.TestCase):
    """FIX-5：CLI 级 --include-diff（真实 git 仓库，提示词含代码变更标注）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="autoloop-cli-diff-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_gate_include_diff_in_git_repo(self):
        r = run_cli(HARNESS, ["init", "include-diff CLI 测试"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        run_id = parse_json_line(r.stdout)["run_id"]
        r = run_cli(HARNESS, ["gate", "--run", run_id, "--mode", "local",
                              "--include-diff"], self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        prompt = (Path(self.tmp) / run_id / "gates" / "P1-iter1.prompts" / "A.md") \
            .read_text(encoding="utf-8")
        self.assertIn("## 代码变更（供代码类阶段评审参考）", prompt)
        self.assertIn("git diff HEAD", prompt)
        self.assertIn("git status --short", prompt)


if __name__ == "__main__":
    unittest.main()
