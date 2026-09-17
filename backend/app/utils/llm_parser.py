import json
import re

from app.utils.llm import get_client, get_model


async def parse_canteen_text(
    raw_text: str,
    elder_list: list[dict],
) -> dict:
    """
    调用 LLM 将非结构化食堂文本解析为结构化 JSON。
    失败时返回 {"error": "原因", "fallback": True}。
    """
    client = get_client()
    if not client:
        return {"error": "LLM API 未配置", "fallback": True}

    elder_context = "\n".join(
        f"- {e['name']} (id: {e['id']}, {e['care_level']}级)"
        for e in elder_list
    )

    system_prompt = f"""你是社区食堂就餐记录解析助手。
以下是该社区的老人名单：
{elder_context}

请将输入的就餐记录解析为以下 JSON 格式（只返回 JSON，不要其他文字）：
{{
  "date": "YYYY-MM-DD",
  "meal_type": "breakfast|lunch|dinner",
  "attendees": [
    {{"elder_id": "uuid", "elder_name": "姓名", "present": true, "notes": "备注"}}
  ],
  "parse_notes": "解析说明"
}}

规则：
1. present 为 true 表示就餐，false 表示未就餐
2. 如果无法判断，present 设为 null
3. elder_id 必须从名单中匹配，名字模糊匹配
4. 名单外的老人单独列出，elder_id 设为 null"""

    try:
        response = await client.chat.completions.create(
            model=get_model(),
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text},
            ],
        )
        text = response.choices[0].message.content
        match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
        if match:
            text = match.group(1)
        return json.loads(text.strip())
    except Exception as e:
        return {"error": str(e), "fallback": True}
