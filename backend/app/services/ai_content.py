import base64
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from app.utils.llm import get_client, get_model, get_vision_model, no_thinking_kwargs

logger = logging.getLogger("ezlove.ai_content")


PHOTO_ANALYSIS_PROMPT = """你是一个温暖的家庭关怀助手。一位子女拍了一张日常生活照片想分享给独居的老人。

请完成以下任务：
1. 用一句话描述照片内容（photo_description）
2. 生成3条不同风格的配文（captions），每条不超过60字，语气温暖口语化，像孩子跟父母说话：
   - 第1条：日常分享风格（tag: "日常"）
   - 第2条：回忆触发风格（tag: "回忆"）
   - 第3条：轻松幽默风格（tag: "幽默"）
3. 从4个海报模板中推荐最适合的（recommended_template）：
   - warm_letter: 温暖信笺风格，适合文字较多、情感深的内容
   - sunset_glow: 暮光温情风格，适合风景、户外照片
   - garden_frame: 花园相框风格，适合食物、小物件
   - simple_elegant: 素雅留白风格，适合人物照片

{user_text_hint}

请严格按以下JSON格式返回：
{{
  "photo_description": "照片描述",
  "captions": [
    {{"tag": "日常", "text": "配文内容"}},
    {{"tag": "回忆", "text": "配文内容"}},
    {{"tag": "幽默", "text": "配文内容"}}
  ],
  "recommended_template": "模板名称"
}}
"""


PROMPT_TEMPLATE = """你是一个温暖的家庭关怀助手。请为一位子女生成3条可以发给独居老人的温暖问候。

当前信息：
- 时间：{time}
- 日期：{date}

要求：
1. 每条不超过100字
2. 语气温暖、口语化，像孩子跟父母说话
3. 内容类型多样：天气问候、养生提示、日常分享、回忆触发
4. 不要使用"亲爱的"等过于正式的称呼，用"妈"、"爸"等口语

请严格按以下JSON格式返回：
[
  {{"tag": "内容类型", "text": "问候内容"}},
  {{"tag": "内容类型", "text": "问候内容"}},
  {{"tag": "内容类型", "text": "问候内容"}}
]
"""


def _extract_json(text: str) -> dict | list:
    """从模型返回中提取 JSON：兼容 markdown 代码块围栏与前后缀说明文字。

    qwen 系模型常把 JSON 包在 ```json ... ``` 中（实测 omni-flash 高概率如此），
    直接 json.loads 会在首个反引号处失败、白白降级为本地兜底文案。
    """
    s = (text or "").strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # 兜底：截取第一个括号对（对象或数组）之间的内容
        for open_ch, close_ch in (("{", "}"), ("[", "]")):
            i, j = s.find(open_ch), s.rfind(close_ch)
            if i != -1 and j > i:
                return json.loads(s[i:j + 1])
        raise


async def generate_suggestions() -> list[dict]:
    now = datetime.now()
    prompt = PROMPT_TEMPLATE.format(
        time=now.strftime("%H:%M"),
        date=now.strftime("%Y年%m月%d日"),
    )

    client = get_client()
    if not client:
        return _fallback_suggestions()

    try:
        response = await client.chat.completions.create(
            model=get_model(),
            max_tokens=512,
            **no_thinking_kwargs(),
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content
        return _extract_json(text)
    except Exception:
        return _fallback_suggestions()


TEMPLATE_KEYWORDS = {
    "sunset_glow": ["天空", "日落", "风景", "户外", "公园", "山", "海", "河", "树", "路", "散步", "阳光"],
    "garden_frame": ["菜", "饭", "花", "水果", "食物", "厨房", "盆栽", "茶", "杯", "碗"],
    "simple_elegant": ["人", "自拍", "合影", "笑", "坐", "站"],
    "warm_letter": [],
}


async def analyze_photo_and_suggest(image_path: str, user_text: str | None = None) -> dict:
    user_text_hint = f"用户附带的文字：「{user_text}」\n请在配文中自然融入用户想表达的内容。" if user_text else "用户没有附带文字。"
    prompt = PHOTO_ANALYSIS_PROMPT.format(user_text_hint=user_text_hint)

    client = get_client()
    if not client:
        return _fallback_photo_analysis(user_text)

    t0 = time.monotonic()
    try:
        img_path = Path(image_path)
        if not img_path.exists():
            return _fallback_photo_analysis(user_text)

        with open(img_path, "rb") as f:
            img_data = base64.standard_b64encode(f.read()).decode("utf-8")

        suffix = img_path.suffix.lower()
        media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}.get(suffix.lstrip("."), "image/jpeg")

        response = await client.chat.completions.create(
            # 视觉理解需独立的多模态模型，不能复用文本 LLM_MODEL
            model=get_vision_model(),
            max_tokens=512,
            # 单请求超时兜底：模型侧慢/挂起时快速降级为本地文案，避免海报页长时间等待
            timeout=45.0,
            **no_thinking_kwargs(),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{img_data}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        text = response.choices[0].message.content
        result = _extract_json(text)
        logger.info("photo analysis ok: model=%s %.1fs", get_vision_model(), time.monotonic() - t0)
        return result
    except Exception as e:
        logger.warning("photo analysis failed after %.1fs, fallback: %s: %s", time.monotonic() - t0, type(e).__name__, e)
        return _fallback_photo_analysis(user_text)


def _fallback_photo_analysis(user_text: str | None = None) -> dict:
    hour = datetime.now().hour
    base_text = user_text or ""

    if hour < 12:
        captions = [
            {"tag": "日常", "text": f"妈，早上好！{base_text or '今天天气真不错，出门走走吧。'}"},
            {"tag": "回忆", "text": f"看到这个就想起小时候你带我去公园的日子。{base_text or ''}".strip()},
            {"tag": "幽默", "text": f"妈你看！{base_text or '是不是觉得我越来越会拍照了哈哈'}"},
        ]
    elif hour < 18:
        captions = [
            {"tag": "日常", "text": f"妈，给你看看我今天的生活！{base_text or ''}".strip()},
            {"tag": "回忆", "text": f"这个让我想到小时候家里的味道。{base_text or '你还记得吗？'}"},
            {"tag": "幽默", "text": f"哈哈妈你猜这是啥？{base_text or '提示：跟吃有关！'}"},
        ]
    else:
        captions = [
            {"tag": "日常", "text": f"妈，分享一下今天的小确幸。{base_text or '明天继续加油！'}"},
            {"tag": "回忆", "text": f"晚上看到这个突然好想家。{base_text or '想你做的饭了。'}"},
            {"tag": "幽默", "text": f"妈，你看我今天的战果！{base_text or '是不是该表扬我？'}"},
        ]

    return {
        "photo_description": "一张温馨的日常生活照片",
        "captions": captions,
        "recommended_template": "warm_letter",
    }


def _fallback_suggestions() -> list[dict]:
    hour = datetime.now().hour
    if hour < 12:
        return [
            {"tag": "早安", "text": "妈，早上好！今天天气不错，记得出去走走，别老闷在家里。"},
            {"tag": "养生", "text": "爸，早饭吃了吗？别光喝粥，煮个鸡蛋吃，营养要跟上。"},
            {"tag": "日常", "text": "妈，我今天上班路上看到桂花开了，特别香，想起小时候你带我在楼下摘桂花。"},
        ]
    elif hour < 18:
        return [
            {"tag": "午安", "text": "爸，中午别忘了午休一会儿，别一直看电视。"},
            {"tag": "日常", "text": "妈，我今天中午自己做了番茄炒蛋，味道越来越像你做的了！"},
            {"tag": "关心", "text": "爸，天气热了，记得多喝水。冰箱里的西瓜别放太久了啊。"},
        ]
    else:
        return [
            {"tag": "晚安", "text": "妈，早点休息，别看手机太晚了，对眼睛不好。"},
            {"tag": "日常", "text": "爸，今天加班刚到家，给你看看我养的那盆绿萝，长得可好了。"},
            {"tag": "关心", "text": "妈，晚上出去散步注意安全，带好手机。想你了，周末回来看你。"},
        ]
