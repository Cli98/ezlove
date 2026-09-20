#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""autoloop 评分引擎（scorer）。

职责：
- api 模式：并行调用 3 个模型评审（openai_compatible / anthropic），解析 verdict
- local 模式：生成 3 个评审提示词文件，等待评审代理通过 ingest 提交 verdict
- ingest 命令：接收单个 evaluator 的 verdict JSON，3 个齐全时自动判定

仅使用 Python 标准库（urllib.request 做 HTTP）。
"""

import argparse
import concurrent.futures
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover —— Windows 等平台无 fcntl
    fcntl = None

# 确保同目录模块可导入（脚本直接运行 / 测试导入两种场景都兼容）
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import state as st

# scorer 脚本绝对路径（供提示词文件中给出可执行的提交命令）
SCORER_SCRIPT_PATH = Path(__file__).resolve()

# 单个 artifact 内容注入提示词的最大字符数
ARTIFACT_CHAR_LIMIT = 8000


class InfraError(Exception):
    """api 模式基础设施故障（网络/密钥/配置等）：本轮不计入迭代，由上层以退出码 2 处理。"""


# 网络类异常集合：命中即视为基础设施故障（FIX-4），不再按 0 分静默处理
NETWORK_ERRORS = (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError)


def is_network_error(exc):
    """判断异常是否为网络类（基础设施）异常。"""
    return isinstance(exc, NETWORK_ERRORS)


def _exc_summary(exc, limit=200):
    """异常摘要：类型名 + 消息，限长，供重试提示词与错误文案使用。"""
    s = "%s: %s" % (type(exc).__name__, exc)
    return s if len(s) <= limit else s[:limit] + "…"


# ---------------------------------------------------------------------------
# 评分门路径规则
# ---------------------------------------------------------------------------

def gate_paths(rs, phase, iteration):
    """返回某次评分门相关的全部路径（绝对 + 相对形式）。"""
    base = rs.dir / "gates"
    stem = "P%d-iter%d" % (phase, iteration)
    return {
        "stem": stem,
        "gate": base / (stem + ".json"),
        "gate_rel": "gates/%s.json" % stem,
        "prompts": base / (stem + ".prompts"),
        "verdicts": base / (stem + ".verdicts"),
        "raw": base / (stem + ".raw"),
    }


# ---------------------------------------------------------------------------
# 提示词构造
# ---------------------------------------------------------------------------

def build_system_prompt(ev_id, rubrics, phase_meta):
    """构造评分 system 提示词：persona + 阶段评分细则 + 输出规则。"""
    persona = rubrics["evaluator_personas"][ev_id]
    pr = rubrics["phases"][str(phase_meta["n"])]
    lines = []
    lines.append("# 你的角色")
    lines.append(persona["persona"])
    lines.append("")
    lines.append("# 评分细则（阶段 %d/%d %s，%s）" % (
        phase_meta["n"], len(rubrics["phases"]), phase_meta["title"], pr["name"]))
    lines.append("## 维度（dimension_scores 按这些维度名打分）")
    for dim, d in pr["dimensions"].items():
        lines.append("- %s（权重 %d）：%s" % (dim, d["weight"], d["desc"]))
    lines.append("## 一票否决情形（触发时 veto 字段填理由字符串，否则填 null）")
    for v in pr.get("veto", []):
        lines.append("- %s" % v)
    lines.append("## 检查清单")
    for c in pr.get("checklist", []):
        lines.append("- %s" % c)
    lines.append("")
    lines.append("# 评分规则")
    lines.append("- score 为 0-100 整数总评分；95 分以上意味着几乎无可挑剔，必须给出充分证据，禁止人情分。")
    lines.append("- issues 中每个问题必须附带 directive（具体可执行的修复指令）。")
    lines.append("- evidence 必须引用待评审产物中的具体内容/文件/行号/测试名，禁止泛泛而谈；evidence 为空将导致分数被强制 cap。")
    lines.append("- 若发现上述一票否决情形，veto 字段填写理由字符串；否则必须为 null。")
    lines.append("- 只输出一个 JSON 对象，不要输出任何其他文字。")
    return "\n".join(lines)


def build_user_prompt(ev_id, rubrics, phase_meta, requirement, artifact_texts, prev_directives,
                      diff_text=None):
    """构造评分 user 提示词：阶段信息 + 需求 + 上轮指令 + 产物全文（+ 可选代码变更）。"""
    pr = rubrics["phases"][str(phase_meta["n"])]
    lines = []
    lines.append("# 待评审任务")
    lines.append("阶段：%d %s（%s）" % (phase_meta["n"], phase_meta["title"], pr["name"]))
    lines.append("评审编号：%s" % ev_id)
    lines.append("")
    lines.append("# 项目需求")
    lines.append(requirement)
    if prev_directives:
        lines.append("")
        lines.append("# 上一轮改进指令（本轮必须逐条核实是否已解决，未解决的应体现在 issues 中）")
        for d in prev_directives:
            lines.append("- %s [%s]（评审: %s）%s" % (
                d.get("id"), d.get("severity"), ",".join(d.get("evaluators", [])), d.get("description", "")))
            if d.get("action"):
                lines.append("  行动: %s" % d["action"])
    lines.append("")
    lines.append("# 待评审产物")
    if artifact_texts:
        for path, text in artifact_texts.items():
            lines.append("## %s" % path)
            lines.append(text)
            lines.append("")
    else:
        lines.append("（本次未提供产物内容，仅凭需求与上下文评分）")
    lines.append("")
    lines.append("# 输出格式（只输出一个 JSON 对象，不要任何其他文字）")
    lines.append('{')
    lines.append('  "evaluator": "%s",' % ev_id)
    lines.append('  "score": 0到100的整数总评分,')
    lines.append('  "dimension_scores": {"<维度名>": 各维度0到100的分数, ...},')
    lines.append('  "strengths": ["亮点1", ...],')
    lines.append('  "issues": [{"severity": "critical或major或minor", "description": "问题描述", "directive": "具体可执行的修复指令"}],')
    lines.append('  "evidence": ["必须引用待评审产物中的具体内容/文件/行号/测试名"],')
    lines.append('  "veto": null')
    lines.append('}')
    # FIX-5：--include-diff 时在 user prompt 末尾注入代码变更（供代码类阶段评审参考）
    if diff_text:
        lines.append("")
        lines.append("## 代码变更（供代码类阶段评审参考）")
        lines.append(diff_text)
    return "\n".join(lines)


def build_local_prompt_content(ev_id, rubrics, phase_meta, requirement, artifact_texts,
                               prev_directives, run_id, paths, diff_text=None):
    """local 模式提示词文件内容（system + user 合并 + 提交说明）。"""
    system = build_system_prompt(ev_id, rubrics, phase_meta)
    user = build_user_prompt(ev_id, rubrics, phase_meta, requirement, artifact_texts,
                             prev_directives, diff_text)
    verdict_rel = "gates/%s.verdicts/%s.json" % (paths["stem"], ev_id)
    footer = []
    footer.append("# 提交方式")
    footer.append("评审完成后，将你的 verdict JSON 写入：")
    footer.append("  <run目录>/%s" % verdict_rel)
    footer.append("然后执行：")
    footer.append("  python3 %s ingest --run %s --evaluator %s --file <run目录>/%s"
                  % (SCORER_SCRIPT_PATH, run_id, ev_id, verdict_rel))
    footer.append("（ingest 也接受 --file 指向任意路径的 verdict JSON。）")
    footer.append("你的评审对象编号是 %s，verdict JSON 的 evaluator 字段必须为 \"%s\"。" % (ev_id, ev_id))
    return system + "\n\n---\n\n" + user + "\n\n---\n\n" + "\n".join(footer)


# ---------------------------------------------------------------------------
# verdict 解析与校验
# ---------------------------------------------------------------------------

def _try_parse_fragment(fragment):
    """尝试把单个候选片段解析为 JSON 对象；失败返回 None（不抛异常）。

    先整体 json.loads（纯 JSON 片段），失败再截取第一个 { 到最后一个 }。
    解析结果不是对象时同样返回 None，交由下一个候选。
    """
    frag = str(fragment).strip()
    if not frag:
        return None
    obj = None
    try:
        obj = json.loads(frag)
    except json.JSONDecodeError:
        start = frag.find("{")
        end = frag.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            obj = json.loads(frag[start:end + 1])
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def parse_verdict_text(text):
    """鲁棒解析模型输出为 JSON 对象（m1 多栅栏解析）。

    解析优先级（逐个候选尝试，成功即返回）：
    1. 所有 ```json 栅栏块
    2. 所有栅栏块（任意语言标注，如思考块 ```text）
    3. 截取第一个 { 到最后一个 } 之间的内容
    全部失败才抛 ValueError。
    """
    s = str(text).strip()
    # 优先级 1：所有 ```json 栅栏块
    for m in re.finditer(r"```json\s*(.*?)```", s, re.DOTALL):
        obj = _try_parse_fragment(m.group(1))
        if obj is not None:
            return obj
    # 优先级 2：所有栅栏块（任意标注）
    for m in re.finditer(r"```[\w-]*\s*(.*?)```", s, re.DOTALL):
        obj = _try_parse_fragment(m.group(1))
        if obj is not None:
            return obj
    # 优先级 3：first-{ 到 last-}
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(s[start:end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    raise ValueError("输出中未找到 JSON 对象")


def validate_verdict(obj, expected_ev=None):
    """校验并规范化 verdict JSON；不合法抛 ValueError（中文消息）。

    expected_ev 非 None 时强制要求 evaluator 字段一致（local ingest 场景）。
    """
    if not isinstance(obj, dict):
        raise ValueError("verdict 必须是 JSON 对象")
    ev_field = obj.get("evaluator")
    if expected_ev is not None and ev_field is not None and ev_field != expected_ev:
        raise ValueError("evaluator 字段(%r)与 --evaluator(%s) 不一致" % (ev_field, expected_ev))
    if expected_ev is not None and ev_field is None:
        raise ValueError("缺少 evaluator 字段（应为 %s）" % expected_ev)

    score = obj.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise ValueError("score 必须是 0-100 的数字")
    if not (0 <= float(score) <= 100):
        raise ValueError("score 必须在 0-100 之间，当前为 %s" % score)

    issues_raw = obj.get("issues", [])
    if not isinstance(issues_raw, list):
        raise ValueError("issues 必须是数组")
    issues = []
    for i, it in enumerate(issues_raw):
        if not isinstance(it, dict):
            raise ValueError("issues[%d] 必须是对象" % i)
        sev = it.get("severity")
        if sev not in st.SEVERITY_ORDER:
            raise ValueError("issues[%d].severity 必须是 critical/major/minor，当前为 %r" % (i, sev))
        desc = it.get("description")
        if not desc or not str(desc).strip():
            raise ValueError("issues[%d].description 不能为空" % i)
        issues.append({
            "severity": sev,
            "description": str(desc).strip(),
            "directive": str(it.get("directive", "") or "").strip(),
        })

    evidence_raw = obj.get("evidence", [])
    if not isinstance(evidence_raw, list):
        raise ValueError("evidence 必须是数组")
    evidence = [str(e) for e in evidence_raw]

    strengths_raw = obj.get("strengths", [])
    if not isinstance(strengths_raw, list):
        raise ValueError("strengths 必须是数组")
    strengths = [str(s) for s in strengths_raw]

    dims_raw = obj.get("dimension_scores", {})
    if not isinstance(dims_raw, dict):
        raise ValueError("dimension_scores 必须是对象")
    dims = {}
    for k, v in dims_raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("dimension_scores.%s 的分数必须是数字" % k)
        dims[str(k)] = v

    veto = obj.get("veto", None)
    if veto is not None:
        if not isinstance(veto, str) or not veto.strip():
            raise ValueError("veto 必须是 null 或非空理由字符串")

    f = float(score)
    return {
        "evaluator": expected_ev if expected_ev is not None else (ev_field if ev_field else None),
        "score": int(f) if f.is_integer() else f,
        "dimension_scores": dims,
        "strengths": strengths,
        "issues": issues,
        "evidence": evidence,
        "veto": (veto.strip() if isinstance(veto, str) else None),
    }


# ---------------------------------------------------------------------------
# api 模式：模型调用
# ---------------------------------------------------------------------------

def load_models_config():
    """读取 config/models.json；不存在返回 None。"""
    return st.read_json(st.CONFIG_MODELS_PATH)


def api_ready(models_cfg):
    """api 模式可用性：配置存在、3 个 evaluator 都有非空 provider 且 api_key_env 环境变量非空。"""
    if not models_cfg or not isinstance(models_cfg.get("evaluators"), dict):
        return False
    evs = models_cfg["evaluators"]
    for ev_id in st.EVALUATOR_IDS:
        ev = evs.get(ev_id) or {}
        if not str(ev.get("provider") or "").strip():
            return False
        env_name = str(ev.get("api_key_env") or "").strip()
        if not env_name:
            return False
        if not os.environ.get(env_name, "").strip():
            return False
    return True


def build_api_request(ev_cfg, system, user):
    """按 provider 构造 HTTP 请求（url, headers, body）。"""
    provider = str(ev_cfg.get("provider") or "").strip()
    key = os.environ.get(str(ev_cfg.get("api_key_env") or ""), "")
    if provider == "openai_compatible":
        url = str(ev_cfg["base_url"]).rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        }
        body = {
            "model": ev_cfg["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": ev_cfg.get("temperature", 0.1),
            "max_tokens": ev_cfg.get("max_tokens", 3000),
        }
    elif provider == "anthropic":
        url = str(ev_cfg["base_url"]).rstrip("/") + "/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }
        body = {
            "model": ev_cfg["model"],
            "system": system,
            "messages": [{"role": "user", "content": user}],
            # m4：anthropic 请求体同样携带 temperature（默认 0.1，与 openai_compatible 一致）
            "temperature": ev_cfg.get("temperature", 0.1),
            "max_tokens": ev_cfg.get("max_tokens", 3000),
        }
    else:
        raise ValueError("不支持的 provider: %r" % provider)
    return url, headers, body


def call_evaluator_once(ev_cfg, system, user, extra=""):
    """单次调用模型，返回响应文本；网络/HTTP 错误向上抛异常。"""
    url, headers, body = build_api_request(ev_cfg, system, user + extra)
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    timeout = int(ev_cfg.get("timeout_seconds", 120))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if str(ev_cfg.get("provider")) == "anthropic":
        parts = [b.get("text", "") for b in payload.get("content", [])
                 if isinstance(b, dict) and b.get("type") == "text"]
        return "".join(parts)
    return payload["choices"][0]["message"]["content"]


def call_evaluator(ev_cfg, system, user, expected_ev=None):
    """调用模型并解析 verdict；网络异常与解析失败各自重试 1 次（FIX-4）。

    返回 (verdict 或 None, parse_ok, raw_text)。
    - 网络类异常：第一次失败后携带具体失败原因重试一次（m8），
      仍失败则向上抛网络类异常（调用方按基础设施故障处理，不按 0 分）
    - 解析失败：重试一次（追加“仅输出 JSON”要求），仍失败返回 (None, False, raw)，
      该 evaluator 以 0 分参与判定，raw 原文存档
    - api 模式下模型自报的 evaluator 字段不可靠：解析时宽松校验，
      成功后以 expected_ev 覆盖
    """
    def _parse(text):
        v = validate_verdict(parse_verdict_text(text), expected_ev=None)
        v["evaluator"] = expected_ev
        return v

    # 第一次调用：网络类异常 → 携带失败原因重试一次，仍失败向上抛（基础设施故障）
    try:
        raw1 = call_evaluator_once(ev_cfg, system, user)
    except Exception as e:
        if not is_network_error(e):
            raise
        retry_extra = "\n\n上次调用失败原因：%s，请重新输出。" % _exc_summary(e)
        raw1 = call_evaluator_once(ev_cfg, system, user, retry_extra)

    try:
        return _parse(raw1), True, raw1
    except Exception:
        raw2 = call_evaluator_once(
            ev_cfg, system, user, "\n\n注意：仅输出 JSON，不要输出任何其他文字。")
    raw_all = raw1 + "\n\n[重试输出]\n" + raw2
    try:
        return _parse(raw2), True, raw_all
    except Exception:
        return None, False, raw_all


def assemble_evaluator_entry(ev_id, verdict, parse_ok, model_name, raw_rel):
    """组装 gate 文件中的 evaluator 条目。"""
    persona = st.load_rubrics()["evaluator_personas"][ev_id]
    entry = {
        "name": persona["name"],
        "model": model_name,
        "raw_path": raw_rel,
        "parse_ok": bool(parse_ok),
    }
    if parse_ok and verdict:
        entry.update({
            "score": verdict["score"],
            "dimension_scores": verdict["dimension_scores"],
            "strengths": verdict["strengths"],
            "issues": verdict["issues"],
            "evidence": verdict["evidence"],
            "veto": verdict["veto"],
        })
    else:
        entry.update({
            "score": 0,
            "dimension_scores": {},
            "strengths": [],
            "issues": [],
            "evidence": [],
            "veto": None,
        })
    return entry


def run_api_evaluations(rs, phase_meta, artifact_texts, prev_directives, diff_text=None):
    """api 模式：并行调用 3 个模型，返回 (evaluators, paths)。

    - 单个 evaluator 响应已返回但解析失败 → 以 0 分参与判定（不中断其他）
    - 任一 evaluator 网络类异常（重试后仍失败）→ 抛 InfraError：本轮不计入迭代，
      已完成 evaluator 的 raw 仍写入 gates/P{n}-iter{k}.raw/（FIX-4）
    """
    models_cfg = load_models_config()
    if not models_cfg:
        raise st.AutoloopError("缺少 config/models.json，无法使用 api 模式")
    ev_cfgs = models_cfg.get("evaluators") or {}
    missing = [e for e in st.EVALUATOR_IDS if e not in ev_cfgs]
    if missing:
        raise st.AutoloopError("config/models.json 缺少 evaluator 配置: %s" % ", ".join(missing))

    rubrics = st.load_rubrics()
    paths = gate_paths(rs, phase_meta["n"], rs.iteration)
    paths["raw"].mkdir(parents=True, exist_ok=True)

    tasks = {}
    for ev_id in st.EVALUATOR_IDS:
        ev_cfg = ev_cfgs[ev_id]
        system = build_system_prompt(ev_id, rubrics, phase_meta)
        user = build_user_prompt(ev_id, rubrics, phase_meta,
                                 rs.data["requirement"], artifact_texts, prev_directives, diff_text)
        tasks[ev_id] = (ev_cfg, system, user)

    evaluators = {}
    infra_errors = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(st.EVALUATOR_IDS)) as ex:
        futures = {
            ev_id: ex.submit(call_evaluator, tasks[ev_id][0], tasks[ev_id][1], tasks[ev_id][2], ev_id)
            for ev_id in st.EVALUATOR_IDS
        }
        for ev_id, fut in futures.items():
            raw_rel = "gates/%s.raw/%s.md" % (paths["stem"], ev_id)
            try:
                verdict, parse_ok, raw = fut.result()
            except Exception as e:
                if is_network_error(e):
                    # 网络类异常：基础设施故障，本轮不计入迭代（向上汇聚为 InfraError）
                    infra_errors[ev_id] = e
                    raw = "基础设施错误（网络类异常）：%s" % _exc_summary(e)
                else:
                    raw = "调用失败：%s" % e
                verdict, parse_ok = None, False
            # 无论成败都保留 raw 存档（供事后排查）
            (paths["raw"] / (ev_id + ".md")).write_text(str(raw), encoding="utf-8")
            evaluators[ev_id] = assemble_evaluator_entry(
                ev_id, verdict, parse_ok, tasks[ev_id][0].get("model"), raw_rel)
    if infra_errors:
        detail = "；".join(
            "评审 %s 调用失败（%s）" % (ev_id, _exc_summary(e))
            for ev_id, e in sorted(infra_errors.items()))
        raise InfraError(detail)
    return evaluators, paths


# ---------------------------------------------------------------------------
# local 模式：提示词文件生成
# ---------------------------------------------------------------------------

def write_local_prompts(rs, phase_meta, artifact_texts, prev_directives, diff_text=None):
    """local 模式：生成 3 个评审提示词文件与 gate 骨架。

    返回 (prompts 路径 dict, paths)。
    """
    rubrics = st.load_rubrics()
    paths = gate_paths(rs, phase_meta["n"], rs.iteration)
    paths["prompts"].mkdir(parents=True, exist_ok=True)
    paths["verdicts"].mkdir(parents=True, exist_ok=True)

    # gate 骨架文件（等待 3 个 evaluator ingest）
    gcfg = st.gate_config()
    gate_data = {
        "phase": phase_meta["n"],
        "phase_name": phase_meta["name"],
        "iteration": rs.iteration,
        "timestamp": st.now_iso(),
        "mode": "local",
        "threshold": float(gcfg.get("threshold", 95.0)),
        "strategy": gcfg.get("strategy", "all"),
        "min_per_model": float(gcfg.get("min_per_model", 90.0)),
        "evaluators": {},
        "status": "awaiting_ingest",
    }
    st.write_json(paths["gate"], gate_data)

    prompts = {}
    for ev_id in st.EVALUATOR_IDS:
        content = build_local_prompt_content(
            ev_id, rubrics, phase_meta, rs.data["requirement"],
            artifact_texts, prev_directives, rs.run_id, paths, diff_text)
        p = paths["prompts"] / (ev_id + ".md")
        p.write_text(content, encoding="utf-8")
        prompts[ev_id] = str(p)
    return prompts, paths


# ---------------------------------------------------------------------------
# ingest 命令（local 模式评审结果提交）
# ---------------------------------------------------------------------------

def _fmt_scores(scores):
    return ", ".join("%s=%s" % (k, scores[k]) for k in st.EVALUATOR_IDS if k in scores)


def _acquire_ingest_lock(run_dir):
    """获取 run 目录的 ingest 排他文件锁，返回锁文件描述符（FIX-2）。

    fcntl 不可用（如 Windows）时抛出清晰错误，避免无锁并发。
    """
    if fcntl is None:
        raise st.AutoloopError("当前平台不支持 fcntl 文件锁，无法安全执行 ingest")
    lock_path = Path(run_dir) / ".ingest.lock"
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError:
        os.close(fd)
        raise
    return fd


def _release_ingest_lock(fd):
    """释放 ingest 文件锁并关闭描述符。"""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def cmd_ingest(args):
    """ingest 子命令实现，返回退出码。

    FIX-2：读 state → 校验重复 → 写 evaluators → 判定 → 写 state 的整个临界区
    在 run 目录级排他文件锁（<run>/.ingest.lock + flock）保护下串行执行。
    """
    # 先定位 run 目录（只读），随后持锁重新加载最新状态，避免读到过期 state
    rs0 = st.RunState.load(args.run)
    lock_fd = _acquire_ingest_lock(rs0.dir)
    try:
        return _cmd_ingest_locked(args)
    finally:
        _release_ingest_lock(lock_fd)


def _cmd_ingest_locked(args):
    """ingest 临界区逻辑（调用方已持有 run 级文件锁）。"""
    rs = st.RunState.load(args.run)
    if rs.data["status"] != "awaiting_ingest":
        raise st.AutoloopError(
            "当前状态为 %s，没有等待 ingest 的评分门（请先用 gate 命令发起）" % rs.data["status"])
    pending = rs.data.get("pending_gate") or {}
    if not pending:
        raise st.AutoloopError("state 中缺少 pending_gate 记录，状态文件可能已损坏")

    ev_id = args.evaluator
    received = pending.get("received") or []
    if ev_id in received:
        raise st.AutoloopError("评审 %s 的 verdict 已提交过，请勿重复提交" % ev_id)

    # 读取并校验 verdict 文件
    vf = Path(args.file)
    if not vf.exists():
        raise st.AutoloopError("verdict 文件不存在: %s" % args.file)
    try:
        raw_obj = json.loads(vf.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise st.AutoloopError("verdict 文件不是合法 JSON: %s" % e)
    try:
        verdict = validate_verdict(raw_obj, expected_ev=ev_id)
    except ValueError as e:
        raise st.AutoloopError("verdict 校验失败: %s" % e)

    phase = pending["phase"]
    iteration = pending["iter"]
    paths = gate_paths(rs, phase, iteration)
    gate_data = st.read_json(paths["gate"]) or {}

    # 归档 verdict 副本（即使 --file 指向外部路径也统一存到 verdicts 目录）
    paths["verdicts"].mkdir(parents=True, exist_ok=True)
    archive_rel = "gates/%s.verdicts/%s.json" % (paths["stem"], ev_id)
    st.write_json(rs.dir / archive_rel, raw_obj)

    gate_data.setdefault("evaluators", {})[ev_id] = assemble_evaluator_entry(
        ev_id, verdict, True, "local-subagent", archive_rel)

    received_now = sorted(gate_data["evaluators"].keys())
    missing = [e for e in st.EVALUATOR_IDS if e not in received_now]

    if missing:
        # 尚未齐 3 个：仅记录，等待其余评审
        gate_data["status"] = "awaiting_ingest"
        st.write_json(paths["gate"], gate_data)
        pending["received"] = received_now
        rs.save()
        print("已接收评审 %s 的 verdict（评分 %s），已归档至 <run目录>/%s" % (ev_id, verdict["score"], archive_rel))
        print("已收到 %d/3，待提交: %s" % (len(received_now), ", ".join(missing)))
        st.emit_json({
            "run_id": rs.run_id, "gate": paths["stem"], "evaluator": ev_id,
            "score": verdict["score"], "received": received_now,
            "pending": missing, "status": "awaiting_ingest",
        })
        return 0

    # 3 个齐全：自动判定
    judged = st.judge(gate_data["evaluators"], st.gate_config())
    gate_data.update({
        "scores": judged["scores"],
        "avg_score": judged["avg_score"],
        "min_score": judged["min_score"],
        "max_score": judged["max_score"],
        "passed": judged["passed"],
        "veto": judged["veto"],
        "directives": judged["directives"],
        "verdict_reason": judged["verdict_reason"],
        "status": "judged",
    })
    st.write_json(paths["gate"], gate_data)
    # FIX-1：判定完成即写入 score-history（P9 复盘权威数据源，每轮 gate 一行）
    st.append_score_history(rs, gate_data)
    rs.apply_judged_gate(paths["gate_rel"], judged, phase, iteration)

    # 输出判定摘要
    print("评审 %s 已提交，3 位评审齐全，自动判定评分门 %s：" % (ev_id, paths["stem"]))
    print("  分数: %s（avg %s / min %s，threshold %s）" % (
        _fmt_scores(judged["scores"]), judged["avg_score"], judged["min_score"], judged["threshold"]))
    print("  理由: %s" % judged["verdict_reason"])
    if judged["passed"]:
        print("GATE_RESULT: passed")
        if rs.data["status"] == "done":
            print("  最后阶段已通过，运行状态: done")
        else:
            nxt = rs.phase_meta()
            print("  阶段 %d 已通过，进入阶段 %d/%d %s（%s）" % (
                phase, nxt["n"], rs.phase_count, nxt["title"], nxt["name"]))
    else:
        print("GATE_RESULT: failed")
        if rs.data["status"] == "blocked":
            # m5：明确区分已完成轮次与待批准轮次，避免误导
            print("  已完成 %d 轮迭代均未通过，第 %d 轮待批准后开始（执行 continue --run %s 批准后继续）。"
                  % (rs.data["iteration"] - 1, rs.data["iteration"], rs.run_id))
        else:
            print("  未通过，进入第 %d 轮迭代，请用 directives 命令查看改进指令。" % rs.data["iteration"])
    st.emit_json({
        "run_id": rs.run_id, "gate": paths["stem"], "phase": phase,
        "iteration": iteration, "passed": judged["passed"],
        "scores": judged["scores"], "avg_score": judged["avg_score"],
        "min_score": judged["min_score"], "threshold": judged["threshold"],
        "iteration_next": rs.data["iteration"], "status": rs.data["status"],
        "directives_count": len(judged["directives"]),
        "verdict_reason": judged["verdict_reason"],
    })
    if rs.data["status"] == "blocked":
        return 2
    return 0 if judged["passed"] else 1


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="scorer.py", description="autoloop 评分引擎（api/local 双模式）")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ingest", help="提交单个评审的 verdict JSON")
    p.add_argument("--run", required=True, help="run_id")
    p.add_argument("--evaluator", required=True, choices=list(st.EVALUATOR_IDS), help="评审编号")
    p.add_argument("--file", required=True, help="verdict JSON 文件路径")
    args = parser.parse_args(argv)

    try:
        if args.command == "ingest":
            return cmd_ingest(args)
        parser.error("未知命令: %s" % args.command)
    except st.AutoloopError as e:
        print("错误: %s" % e, file=sys.stderr)
        return 2
    except (ValueError, OSError, KeyError) as e:
        # m9：与 harness.py 一致的异常兑底，避免未预期异常以 traceback 崩出
        print("错误: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
