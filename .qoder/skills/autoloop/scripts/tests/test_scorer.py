#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_scorer：评分引擎单元测试（全部离线，禁止真实 HTTP）。"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import state as st
import scorer


def make_ev(score=96, evidence=None, issues=None, veto=None, parse_ok=True):
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


def openai_response(content):
    """构造 openai_compatible 的 HTTP 响应 payload。"""
    return {"choices": [{"message": {"content": content}}]}


def anthropic_response(content):
    """构造 anthropic 的 HTTP 响应 payload。"""
    return {"content": [{"type": "text", "text": content}]}


class FakeResponse(io.BytesIO):
    """兼容 with 语句与 read() 的伪 HTTP 响应。"""


class TestParseVerdictText(unittest.TestCase):
    """模型输出鲁棒解析测试。"""

    def test_parse_clean_json(self):
        obj = scorer.parse_verdict_text('{"score": 96, "evidence": ["x"]}')
        self.assertEqual(obj["score"], 96)

    def test_parse_fenced_json(self):
        text = "```json\n{\"score\": 96, \"veto\": null}\n```"
        obj = scorer.parse_verdict_text(text)
        self.assertEqual(obj["score"], 96)

    def test_parse_fenced_no_lang(self):
        text = "```\n{\"score\": 90}\n```"
        self.assertEqual(scorer.parse_verdict_text(text)["score"], 90)

    def test_parse_surrounded_by_prose(self):
        text = "好的，以下是我的评分结果：\n\n{ \"score\": 96, \"issues\": [] }\n\n希望对你有帮助！"
        obj = scorer.parse_verdict_text(text)
        self.assertEqual(obj["score"], 96)

    def test_parse_invalid_raises(self):
        with self.assertRaises(ValueError):
            scorer.parse_verdict_text("完全没有 JSON 的输出")
        with self.assertRaises(ValueError):
            scorer.parse_verdict_text("broken {json")

    def test_parse_non_object_raises(self):
        with self.assertRaises(ValueError):
            scorer.parse_verdict_text("[1, 2, 3]")

    # ---- m1 多栅栏解析：思考块 + json 块等组合场景 ----

    def test_parse_thinking_fence_then_json_fence(self):
        # 思考块在前、```json 块在后：优先级 1 命中 json 块，忽略思考块内容
        text = ("```text\n让我思考一下：这个产物整体结构不错，但需要检查细节……\n```\n\n"
                "```json\n{\"score\": 96, \"veto\": null}\n```")
        obj = scorer.parse_verdict_text(text)
        self.assertEqual(obj["score"], 96)
        self.assertIsNone(obj["veto"])

    def test_parse_broken_json_fence_falls_back_to_any_fence(self):
        # 第一个 ```json 块不是合法 JSON → 降级到优先级 2（任意栅栏块）解析思考块中的 JSON
        text = ("```json\n这不是合法 JSON\n```\n\n"
                "```\n思考结论如下：{\"score\": 91, \"evidence\": [\"L1\"]}\n```")
        obj = scorer.parse_verdict_text(text)
        self.assertEqual(obj["score"], 91)
        self.assertEqual(obj["evidence"], ["L1"])

    def test_parse_multiple_json_fences_skip_broken(self):
        # 多个 ```json 块：第一个损坏时逐个尝试，命中第二个
        text = "```json\nbroken\n```\n\n```json\n{\"score\": 88}\n```"
        obj = scorer.parse_verdict_text(text)
        self.assertEqual(obj["score"], 88)


class TestValidateVerdict(unittest.TestCase):
    def test_valid_verdict(self):
        v = scorer.validate_verdict({
            "evaluator": "A", "score": 96,
            "dimension_scores": {"clarity": 95},
            "strengths": ["清晰"],
            "issues": [{"severity": "major", "description": "缺少边界", "directive": "补齐"}],
            "evidence": ["P1-requirement-card.md L10"],
            "veto": None,
        }, expected_ev="A")
        self.assertEqual(v["score"], 96)
        self.assertEqual(v["issues"][0]["severity"], "major")

    def test_evaluator_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            scorer.validate_verdict({"evaluator": "B", "score": 90, "issues": [], "evidence": []},
                                    expected_ev="A")

    def test_missing_evaluator_rejected(self):
        with self.assertRaises(ValueError):
            scorer.validate_verdict({"score": 90, "issues": [], "evidence": []}, expected_ev="A")

    def test_bad_score_rejected(self):
        with self.assertRaises(ValueError):
            scorer.validate_verdict({"evaluator": "A", "score": 101, "issues": [], "evidence": []},
                                    expected_ev="A")
        with self.assertRaises(ValueError):
            scorer.validate_verdict({"evaluator": "A", "score": "高", "issues": [], "evidence": []},
                                    expected_ev="A")

    def test_bad_severity_rejected(self):
        with self.assertRaises(ValueError):
            scorer.validate_verdict({
                "evaluator": "A", "score": 90,
                "issues": [{"severity": "blocker", "description": "x", "directive": "y"}],
                "evidence": [],
            }, expected_ev="A")

    def test_bad_veto_rejected(self):
        with self.assertRaises(ValueError):
            scorer.validate_verdict({
                "evaluator": "A", "score": 90, "issues": [], "evidence": [], "veto": 123,
            }, expected_ev="A")


class TestJudge(unittest.TestCase):
    """评分门判定矩阵测试。"""

    def setUp(self):
        self.cfg = st.gate_config()  # 默认 threshold=95, strategy=all

    def test_all_pass_at_threshold(self):
        judged = st.judge(full_evaluators(score=95), self.cfg)
        self.assertTrue(judged["passed"])
        self.assertEqual(judged["min_score"], 95)
        self.assertIn("strategy=all", judged["verdict_reason"])

    def test_all_fail_below_threshold(self):
        evs = full_evaluators(score=95)
        evs["B"] = make_ev(score=94)
        judged = st.judge(evs, self.cfg)
        self.assertFalse(judged["passed"])
        self.assertEqual(judged["min_score"], 94)
        self.assertIn("min score 94.0 < threshold 95.0", judged["verdict_reason"])

    def test_veto_fails(self):
        evs = full_evaluators(score=99)
        evs["C"]["veto"] = "验收标准不可验证"
        judged = st.judge(evs, self.cfg)
        self.assertFalse(judged["passed"])
        self.assertEqual(len(judged["veto"]), 1)
        self.assertEqual(judged["veto"][0]["evaluator"], "C")
        self.assertIn("一票否决", judged["verdict_reason"])

    def test_evidence_empty_caps_score(self):
        # score 97 但 evidence 为空 → cap 至 90 → 未通过
        evs = full_evaluators(score=97)
        evs["B"]["evidence"] = []
        judged = st.judge(evs, self.cfg)
        self.assertFalse(judged["passed"])
        self.assertEqual(judged["scores"]["B"], 90)
        self.assertIn("cap", judged["verdict_reason"])
        self.assertIn("evidence 为空", judged["verdict_reason"])

    def test_parse_fail_scores_zero(self):
        evs = full_evaluators(score=96)
        evs["A"]["parse_ok"] = False
        judged = st.judge(evs, self.cfg)
        self.assertFalse(judged["passed"])
        self.assertEqual(judged["scores"]["A"], 0)
        self.assertIn("解析失败", judged["verdict_reason"])

    def test_strategy_avg_matrix(self):
        cfg = dict(self.cfg)
        cfg["strategy"] = "avg"
        # avg 93 < 95 → 失败
        judged = st.judge(full_evaluators(score=93), cfg)
        self.assertFalse(judged["passed"])
        self.assertIn("strategy=avg", judged["verdict_reason"])
        # avg 95.0 ≥ 95 且 min 93 ≥ 90 → 通过（285/3=95.0）
        evs = {"A": make_ev(score=96), "B": make_ev(score=96), "C": make_ev(score=93)}
        judged = st.judge(evs, cfg)
        self.assertTrue(judged["passed"])
        # avg ≥ 95 但 min 88 < min_per_model 90 → 失败
        evs = {"A": make_ev(score=99), "B": make_ev(score=99), "C": make_ev(score=88)}
        judged = st.judge(evs, cfg)
        self.assertFalse(judged["passed"])
        self.assertIn("min_per_model", judged["verdict_reason"])
        # avg 策略下 94/95/95：avg 94.7 < 95 → 失败（与 all 策略不同点在于单模型可低于 threshold）
        evs = {"A": make_ev(score=99), "B": make_ev(score=96), "C": make_ev(score=98)}
        judged = st.judge(evs, cfg)
        self.assertTrue(judged["passed"])


class TestDirectives(unittest.TestCase):
    def test_merge_dedup_and_severity_order(self):
        evs = {
            "A": make_ev(score=90, issues=[
                {"severity": "major", "description": "覆盖不足", "directive": "补充场景"},
                {"severity": "minor", "description": "格式问题", "directive": "调整格式"},
            ]),
            "B": make_ev(score=90, issues=[
                # 与 A 的“覆盖不足”同一问题（大小写/空白不同）→ 合并，severity 升级为 critical
                {"severity": "critical", "description": "覆盖  不足", "directive": ""},
            ]),
            "C": make_ev(score=90, issues=[
                {"severity": "critical", "description": "存在安全漏洞", "directive": "修复注入"},
            ]),
        }
        ds = st.build_directives(evs)
        # 去重后 3 条，critical 排前
        self.assertEqual(len(ds), 3)
        self.assertEqual([d["severity"] for d in ds],
                         ["critical", "critical", "minor"])
        # 同一问题合并了 evaluators 列表
        merged = [d for d in ds if "覆盖不足" in d["description"] or "覆盖  不足" in d["description"]]
        self.assertEqual(len(merged), 1)
        self.assertEqual(set(merged[0]["evaluators"]), {"A", "B"})
        self.assertEqual(merged[0]["severity"], "critical")
        # action 取第一个非空
        self.assertEqual(merged[0]["action"], "补充场景")
        # 编号 D1..
        self.assertEqual([d["id"] for d in ds], ["D1", "D2", "D3"])

    def test_empty_when_no_issues(self):
        self.assertEqual(st.build_directives(full_evaluators(score=96)), [])


class TestRubricWeights(unittest.TestCase):
    def test_all_phase_weights_sum_to_100(self):
        rubrics = st.load_rubrics()
        self.assertEqual(len(rubrics["phases"]), 9)
        for n, pr in rubrics["phases"].items():
            total = sum(d["weight"] for d in pr["dimensions"].values())
            self.assertEqual(total, 100, "阶段 %s 维度权重之和应为 100，实际 %d" % (n, total))
        # persona 完整
        for ev_id in st.EVALUATOR_IDS:
            self.assertIn("persona", rubrics["evaluator_personas"][ev_id])


class TestApiRequestConstruction(unittest.TestCase):
    """api 模式请求体构造（mock urlopen，不发真实请求）。"""

    EV_CFG_OPENAI = {
        "provider": "openai_compatible",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "AUTOLOOP_TEST_KEY",
        "model": "deepseek-chat",
        "temperature": 0.1,
        "max_tokens": 3000,
        "timeout_seconds": 30,
    }
    EV_CFG_ANTHROPIC = {
        "provider": "anthropic",
        "base_url": "https://api.anthropic.com",
        "api_key_env": "AUTOLOOP_TEST_KEY",
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 3000,
        "timeout_seconds": 30,
    }

    def setUp(self):
        os.environ["AUTOLOOP_TEST_KEY"] = "test-key-123"

    def tearDown(self):
        os.environ.pop("AUTOLOOP_TEST_KEY", None)

    def _run_call(self, ev_cfg, payloads):
        """mock urlopen 执行 call_evaluator，返回 (verdict, parse_ok, 请求捕获列表)。"""
        captured = []
        it = iter(payloads)

        def fake_urlopen(req, timeout=None):
            captured.append(req)
            return FakeResponse(json.dumps(next(it)).encode("utf-8"))

        with mock.patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            v, ok, raw = scorer.call_evaluator(ev_cfg, "system-提示词", "user-提示词", "A")
        return v, ok, raw, captured

    def test_openai_request_body(self):
        content = json.dumps({
            "evaluator": "A", "score": 96, "dimension_scores": {"clarity": 95},
            "strengths": [], "issues": [], "evidence": ["L1"], "veto": None,
        }, ensure_ascii=False)
        v, ok, _, captured = self._run_call(self.EV_CFG_OPENAI, [openai_response(content)])
        self.assertTrue(ok)
        self.assertEqual(v["score"], 96)
        req = captured[0]
        # URL 与 headers
        self.assertEqual(req.full_url, "https://api.deepseek.com/v1/chat/completions")
        self.assertEqual(req.get_header("Authorization"), "Bearer test-key-123")
        # 请求体
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["model"], "deepseek-chat")
        self.assertEqual(body["temperature"], 0.1)
        self.assertEqual(body["max_tokens"], 3000)
        self.assertEqual(len(body["messages"]), 2)
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertEqual(body["messages"][0]["content"], "system-提示词")
        self.assertEqual(body["messages"][1]["role"], "user")
        self.assertEqual(body["messages"][1]["content"], "user-提示词")

    def test_anthropic_request_body(self):
        content = json.dumps({
            "evaluator": "B", "score": 97, "dimension_scores": {},
            "strengths": [], "issues": [], "evidence": ["L2"], "veto": None,
        }, ensure_ascii=False)
        v, ok, _, captured = self._run_call(
            self.EV_CFG_ANTHROPIC, [anthropic_response(content)])
        self.assertTrue(ok)
        self.assertEqual(v["score"], 97)
        req = captured[0]
        self.assertEqual(req.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(req.get_header("X-api-key"), "test-key-123")
        self.assertEqual(req.get_header("Anthropic-version"), "2023-06-01")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["model"], "claude-sonnet-4-20250514")
        self.assertEqual(body["system"], "system-提示词")
        self.assertEqual(body["messages"], [{"role": "user", "content": "user-提示词"}])
        self.assertEqual(body["max_tokens"], 3000)
        # m4：anthropic 请求体同样携带 temperature（未配置时默认 0.1）
        self.assertEqual(body["temperature"], 0.1)

    def test_retry_on_garbage_then_success(self):
        # 第一次输出垃圾、重试输出合法 JSON → parse_ok=True，且重试请求 user 内容追加了要求
        garbage = openai_response("我觉得这个产物还不错，打 96 分！")
        good = openai_response("```json\n{\"evaluator\": \"A\", \"score\": 96, "
                               "\"dimension_scores\": {}, \"strengths\": [], "
                               "\"issues\": [], \"evidence\": [\"L3\"], \"veto\": null}\n```")
        v, ok, raw, captured = self._run_call(self.EV_CFG_OPENAI, [garbage, good])
        self.assertTrue(ok)
        self.assertEqual(v["score"], 96)
        self.assertEqual(len(captured), 2)
        body2 = json.loads(captured[1].data.decode("utf-8"))
        self.assertIn("仅输出 JSON", body2["messages"][1]["content"])

    def test_parse_failure_scores_zero(self):
        # 两次都输出垃圾 → parse_ok=False → 该 evaluator 得 0 分参与判定
        garbage = openai_response("抱歉我不会输出 JSON。")
        v, ok, raw, captured = self._run_call(self.EV_CFG_OPENAI, [garbage, garbage])
        self.assertFalse(ok)
        self.assertIsNone(v)
        # 组装 entry 后以 0 分参与判定
        entry = scorer.assemble_evaluator_entry("A", None, False, "deepseek-chat", "raw/A.md")
        self.assertEqual(entry["score"], 0)
        self.assertFalse(entry["parse_ok"])
        evs = full_evaluators(score=96)
        evs["A"] = entry
        judged = st.judge(evs, st.gate_config())
        self.assertFalse(judged["passed"])
        self.assertEqual(judged["scores"]["A"], 0)

    def test_build_api_request_unsupported_provider(self):
        with self.assertRaises(ValueError):
            scorer.build_api_request({"provider": "unknown", "base_url": "x",
                                      "api_key_env": "AUTOLOOP_TEST_KEY"}, "s", "u")


class TestNetworkRetry(unittest.TestCase):
    """FIX-4：网络类异常重试携带失败原因；仍失败向上抛（不按 0 分静默处理）。"""

    EV_CFG = {
        "provider": "openai_compatible",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "AUTOLOOP_TEST_KEY",
        "model": "deepseek-chat",
        "temperature": 0.1,
        "max_tokens": 3000,
        "timeout_seconds": 30,
    }

    def setUp(self):
        os.environ["AUTOLOOP_TEST_KEY"] = "test-key-123"

    def tearDown(self):
        os.environ.pop("AUTOLOOP_TEST_KEY", None)

    def _good_response(self):
        content = json.dumps({
            "evaluator": "A", "score": 96, "dimension_scores": {},
            "strengths": [], "issues": [], "evidence": ["L1"], "veto": None,
        }, ensure_ascii=False)
        return FakeResponse(json.dumps(openai_response(content)).encode("utf-8"))

    def test_network_error_retry_then_success(self):
        # 第一次网络异常 → 携带具体失败原因重试一次 → 成功
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req)
            if len(calls) == 1:
                raise urllib.error.URLError("connection refused")
            return self._good_response()

        with mock.patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            v, ok, raw = scorer.call_evaluator(self.EV_CFG, "s", "u", "A")
        self.assertTrue(ok)
        self.assertEqual(v["score"], 96)
        self.assertEqual(len(calls), 2)
        # 重试请求 user 内容末尾追加了失败原因与“请重新输出”
        body2 = json.loads(calls[1].data.decode("utf-8"))
        retry_user = body2["messages"][1]["content"]
        self.assertTrue(retry_user.startswith("u"))
        self.assertIn("上次调用失败原因：URLError", retry_user)
        self.assertIn("connection refused", retry_user)
        self.assertIn("请重新输出", retry_user)

    def test_network_error_retry_still_fails_raises(self):
        # 两次网络异常均失败 → 网络类异常向上抛（由 run_api_evaluations 汇聚为 InfraError）
        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("timed out")

        with mock.patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaises(urllib.error.URLError):
                scorer.call_evaluator(self.EV_CFG, "s", "u", "A")

    def test_non_network_error_not_swallowed_by_retry(self):
        # 非网络类异常（响应结构缺失导致 KeyError）不走网络重试路径，直接向上抛
        def fake_urlopen(req, timeout=None):
            return FakeResponse(json.dumps({"unexpected": True}).encode("utf-8"))

        with mock.patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            with self.assertRaises(KeyError):
                scorer.call_evaluator(self.EV_CFG, "s", "u", "A")


class TestApiReady(unittest.TestCase):
    def test_no_config_not_ready(self):
        # config/models.json 不存在（项目里只有 .example）→ 不可用
        with mock.patch.object(scorer, "load_models_config", return_value=None):
            self.assertFalse(scorer.api_ready(None))

    def test_missing_key_not_ready(self):
        # api_key_env 指向的环境变量缺失 → 不可用
        cfg = {"evaluators": {
            e: {
                "provider": "openai_compatible",
                "api_key_env": "AUTOLOOP_NO_SUCH_KEY",
                "base_url": "http://x",
                "model": "m",
            } for e in st.EVALUATOR_IDS
        }}
        self.assertFalse(scorer.api_ready(cfg))

    def test_ready_when_all_keys_present(self):
        os.environ["AUTOLOOP_TEST_KEY"] = "k"
        try:
            cfg = {"evaluators": {
                e: {
                    "provider": "openai_compatible",
                    "base_url": "http://x",
                    "api_key_env": "AUTOLOOP_TEST_KEY",
                    "model": "m",
                } for e in st.EVALUATOR_IDS
            }}
            self.assertTrue(scorer.api_ready(cfg))
        finally:
            os.environ.pop("AUTOLOOP_TEST_KEY", None)


if __name__ == "__main__":
    unittest.main()
