#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_state：状态机与持久化单元测试（全部离线）。"""

import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import state as st


def make_ev(score=96, evidence=None, issues=None, veto=None, parse_ok=True):
    """构造一个 evaluator 条目（默认带证据）。"""
    return {
        "name": "测试评审",
        "model": "local-subagent",
        "score": score,
        "dimension_scores": {},
        "strengths": [],
        "issues": issues or [],
        "evidence": evidence if evidence is not None else ["产物第 3 行"],
        "veto": veto,
        "raw_path": None,
        "parse_ok": parse_ok,
    }


def full_evaluators(score=96, **kw):
    return {e: make_ev(score=score, **kw) for e in st.EVALUATOR_IDS}


class StateTestBase(unittest.TestCase):
    """隔离 AUTOLOOP_STATE_DIR 的测试基类。"""

    def setUp(self):
        self._old_env = os.environ.get("AUTOLOOP_STATE_DIR")
        self.tmp = tempfile.mkdtemp(prefix="autoloop-test-state-")
        os.environ["AUTOLOOP_STATE_DIR"] = self.tmp

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("AUTOLOOP_STATE_DIR", None)
        else:
            os.environ["AUTOLOOP_STATE_DIR"] = self._old_env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def create(self, requirement="测试需求：守护独居老人"):
        return st.RunState.create(requirement)


class TestInitStructure(StateTestBase):
    def test_init_creates_structure(self):
        rs = self.create()
        # run 目录与文件
        self.assertTrue((rs.dir / "state.json").exists())
        self.assertTrue((rs.dir / "artifacts").is_dir())
        self.assertTrue((rs.dir / "gates").is_dir())
        self.assertTrue((rs.dir / "reports").is_dir())
        # run_id 格式：YYYYMMDD-HHMMSS-<6位随机>，共 8+1+6+1+6 = 22 字符
        rid = rs.run_id
        self.assertEqual(len(rid), 22)
        self.assertEqual(rid[8], "-")
        self.assertEqual(rid[15], "-")
        # state.json 内容
        with open(rs.dir / "state.json", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["phase"], 1)
        self.assertEqual(data["iteration"], 1)
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["requirement"], "测试需求：守护独居老人")
        self.assertEqual(len(data["phases"]), 9)
        self.assertEqual(data["phases"]["1"]["status"], "running")
        self.assertEqual(data["phases"]["1"]["name"], "intake")
        self.assertEqual(data["phases"]["2"]["status"], "pending")
        self.assertEqual(data["phases"]["9"]["name"], "evolve")
        self.assertEqual(data["notes"], [])
        self.assertIn("run_id", data)
        self.assertIn("created_at", data)

    def test_load_roundtrip(self):
        rs = self.create()
        rs2 = st.RunState.load(rs.run_id)
        self.assertEqual(rs2.data, rs.data)


class TestGateTransitions(StateTestBase):
    def _apply(self, rs, passed, phase=None, iteration=None):
        """对 rs 应用一次判定（写 gate 文件 + 状态转移）。"""
        phase = phase if phase is not None else rs.data["phase"]
        iteration = iteration if iteration is not None else rs.data["iteration"]
        evs = full_evaluators(score=96 if passed else 88)
        judged = st.judge(evs, st.gate_config())
        if not passed:  # 失败时补一条 issue 便于 directives 生成
            evs["C"]["issues"] = [{
                "severity": "critical",
                "description": "覆盖不足",
                "directive": "补充边界场景",
            }]
            judged = st.judge(evs, st.gate_config())
        gate_rel = "gates/P%d-iter%d.json" % (phase, iteration)
        st.write_json(rs.dir / gate_rel, {"phase": phase, "directives": judged["directives"]})
        rs.apply_judged_gate(gate_rel, judged, phase, iteration)
        return judged

    def test_pass_advances_phase(self):
        rs = self.create()
        self._apply(rs, passed=True)
        self.assertEqual(rs.data["phase"], 2)
        self.assertEqual(rs.data["iteration"], 1)
        self.assertEqual(rs.data["status"], "running")
        self.assertEqual(rs.data["phases"]["1"]["status"], "passed")
        self.assertEqual(rs.data["phases"]["2"]["status"], "running")
        # gates 摘要写入当前阶段条目
        entry = rs.data["phases"]["1"]
        self.assertEqual(len(entry["gates"]), 1)
        self.assertEqual(entry["gates"][0]["iter"], 1)
        self.assertTrue(entry["gates"][0]["passed"])
        self.assertEqual(entry["iterations"], 1)
        # last_gate 记录
        self.assertEqual(rs.data["last_gate"]["passed"], True)

    def test_fail_increments_iteration(self):
        rs = self.create()
        judged = self._apply(rs, passed=False)
        self.assertEqual(rs.data["phase"], 1)
        self.assertEqual(rs.data["iteration"], 2)
        self.assertEqual(rs.data["status"], "running")
        self.assertEqual(rs.data["phases"]["1"]["status"], "running")
        self.assertEqual(rs.data["phases"]["1"]["gates"][0]["passed"], False)
        # 失败时生成了 directives
        self.assertTrue(any(d["severity"] == "critical" for d in judged["directives"]))
        # current_prev_directives 能取到上轮指令
        self.assertEqual(len(rs.current_prev_directives()), 1)

    def test_exceed_max_iterations_blocked(self):
        rs = self.create()
        max_iter = int(st.gate_config()["max_iterations"])
        for i in range(1, max_iter + 1):
            self.assertEqual(rs.data["status"], "running")
            self._apply(rs, passed=False)
        # 第 max_iter 轮失败后：iteration = max_iter + 1 > max_iter → blocked
        self.assertEqual(rs.data["status"], "blocked")
        self.assertEqual(rs.data["iteration"], max_iter + 1)
        self.assertEqual(rs.data["phases"]["1"]["iterations"], max_iter)

    def test_continue_restores_running(self):
        rs = self.create()
        max_iter = int(st.gate_config()["max_iterations"])
        for _ in range(max_iter):
            self._apply(rs, passed=False)
        self.assertEqual(rs.data["status"], "blocked")
        blocked_iter = rs.data["iteration"]
        rs.approve_continue()
        self.assertEqual(rs.data["status"], "running")
        # iteration 继续累加，不重置
        self.assertEqual(rs.data["iteration"], blocked_iter)
        # 非 blocked 状态下 continue 报错
        with self.assertRaises(st.AutoloopError):
            rs.approve_continue()

    def test_last_phase_pass_done(self):
        rs = self.create()
        # 快进到阶段 9
        for n in range(1, 9):
            self._apply(rs, passed=True)
        self.assertEqual(rs.data["phase"], 9)
        self._apply(rs, passed=True)
        self.assertEqual(rs.data["status"], "done")
        self.assertEqual(rs.data["phases"]["9"]["status"], "passed")
        # phase 不越界
        self.assertEqual(rs.data["phase"], 9)

    def test_resume_latest_run(self):
        rs1 = self.create("第一个需求")
        # 强造一个更晚的 run_id 保证排序在后面
        rs2 = self.create("第二个需求")
        self.assertEqual(st.latest_run_id(), rs2.run_id)
        # list_run_ids 包含两个
        ids = st.list_run_ids()
        self.assertIn(rs1.run_id, ids)
        self.assertIn(rs2.run_id, ids)


class TestRunIdCollision(StateTestBase):
    """m12：create 时 run_id 碰撞重新生成（最多 3 次），仍冲突则报错。"""

    def test_create_retries_on_collision(self):
        root = Path(self.tmp)
        (root / "dup-id").mkdir(parents=True)
        with mock.patch.object(st, "new_run_id",
                               side_effect=["dup-id", "dup-id", "fresh-id"]):
            rs = st.RunState.create("碰撞重试测试")
        self.assertEqual(rs.run_id, "fresh-id")

    def test_create_fails_after_three_collisions(self):
        root = Path(self.tmp)
        (root / "dup-id").mkdir(parents=True)
        with mock.patch.object(st, "new_run_id", side_effect=["dup-id"] * 3):
            with self.assertRaises(st.AutoloopError):
                st.RunState.create("碰撞失败测试")


class TestJudgeFallbackDirectives(unittest.TestCase):
    """FIX-3：veto / evidence 空导致失败时合成兑底指令。"""

    def setUp(self):
        self.cfg = st.gate_config()

    def test_veto_failure_synthesizes_critical_directive(self):
        evs = full_evaluators(score=99)  # 无 issues → 合并 directives 为空
        evs["B"]["veto"] = "违反安全红线"
        judged = st.judge(evs, self.cfg)
        self.assertFalse(judged["passed"])
        self.assertTrue(judged["directives"], "veto 失败必须有兑底指令")
        d = judged["directives"][0]
        self.assertEqual(d["severity"], "critical")
        self.assertEqual(d["evaluators"], ["B"])
        self.assertIn("一票否决", d["description"])
        self.assertIn("违反安全红线", d["description"])
        self.assertEqual(d["id"], "D1")
        self.assertTrue(d["action"])

    def test_evidence_empty_failure_synthesizes_major_directive(self):
        # 触发 cap（99 > 90）与未触发 cap（85 < 90）都应有兑底指令
        evs = full_evaluators(score=99)
        evs["A"]["evidence"] = []
        evs["C"]["evidence"] = []
        evs["C"]["score"] = 85  # 未触发 cap 也算证据缺失
        judged = st.judge(evs, self.cfg)
        self.assertFalse(judged["passed"])
        evidence_dirs = [d for d in judged["directives"]
                         if "未提供任何评分证据" in d["description"]]
        self.assertEqual(len(evidence_dirs), 2)
        self.assertEqual({d["evaluators"][0] for d in evidence_dirs}, {"A", "C"})
        for d in evidence_dirs:
            self.assertEqual(d["severity"], "major")
            self.assertIn("证据", d["action"])

    def test_issues_present_no_fallback(self):
        # 评审已给出 issues → 走正常合并路径，不合成兑底
        evs = full_evaluators(score=88)
        evs["A"]["issues"] = [
            {"severity": "major", "description": "问题", "directive": "修"}]
        judged = st.judge(evs, self.cfg)
        self.assertEqual(len(judged["directives"]), 1)
        self.assertEqual(judged["directives"][0]["description"], "问题")

    def test_evidence_empty_low_score_still_reasoned(self):
        # m11：score ≤ cap 时 evidence 空也记入 verdict_reason
        evs = full_evaluators(score=88)
        evs["C"]["evidence"] = []
        judged = st.judge(evs, self.cfg)
        self.assertIn("评审 C evidence 为空", judged["verdict_reason"])


class TestStrategyAvgEvidence(unittest.TestCase):
    """m2：avg 策略下任一 evaluator evidence 为空 → 直接不通过。"""

    def test_avg_empty_evidence_fails_even_if_scores_ok(self):
        cfg = dict(st.gate_config())
        cfg["strategy"] = "avg"
        # 99/99/99，C evidence 空 → cap 90 → avg 96 ≥ 95 且 min 90 ≥ 90，
        # 旧逻辑将通过；新逻辑因证据不完整直接不通过
        evs = {"A": make_ev(score=99), "B": make_ev(score=99), "C": make_ev(score=99)}
        evs["C"]["evidence"] = []
        judged = st.judge(evs, cfg)
        self.assertFalse(judged["passed"])
        self.assertIn("strategy=avg", judged["verdict_reason"])
        self.assertIn("evidence 为空", judged["verdict_reason"])


class TestScoreHistory(StateTestBase):
    """FIX-1：append_score_history 单元测试。"""

    def test_append_score_history_records(self):
        rs = self.create()
        gate_data = {
            "phase": 1, "phase_name": "intake", "iteration": 2,
            "passed": False, "scores": {"A": 80, "B": 85, "C": 88},
            "avg_score": 84.3, "min_score": 80,
            "directives": [{"id": "D1"}, {"id": "D2"}],
        }
        st.append_score_history(rs, gate_data)
        st.append_score_history(rs, dict(gate_data, iteration=3, passed=True))
        path = rs.dir / "gates" / "score-history.jsonl"
        self.assertTrue(path.exists())
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        rec = json.loads(lines[0])
        self.assertEqual(rec["run_id"], rs.run_id)
        self.assertEqual(rec["phase"], 1)
        self.assertEqual(rec["phase_name"], "intake")
        self.assertEqual(rec["iter"], 2)
        self.assertFalse(rec["passed"])
        self.assertEqual(rec["scores"], {"A": 80, "B": 85, "C": 88})
        self.assertEqual(rec["avg"], 84.3)
        self.assertEqual(rec["min"], 80)
        self.assertEqual(rec["directives_count"], 2)
        self.assertIn("ts", rec)
        rec2 = json.loads(lines[1])
        self.assertEqual(rec2["iter"], 3)
        self.assertTrue(rec2["passed"])


class TestWriteJsonConcurrency(StateTestBase):
    """FIX-2：write_json 并发安全（mkstemp 唯一临时名 + replace）。"""

    def test_concurrent_write_json_no_tmp_left(self):
        target = Path(self.tmp) / "shared.json"
        errors = []

        def writer(i):
            try:
                for _ in range(5):
                    st.write_json(target, {"i": i})
            except Exception as e:  # 测试用：记录任何异常
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        # 最终文件是合法 JSON 且为某次完整写入（内容完整，无撕裂）
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertIn(data["i"], list(range(8)))
        # 无临时文件残留
        leftovers = [p for p in Path(self.tmp).iterdir() if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
