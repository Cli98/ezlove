import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session
from app.deps import get_current_worker
from app.models.community import CommunityWorker
from app.utils.llm import get_client, get_model

logger = logging.getLogger("ezlove.agent")

router = APIRouter(prefix="/community", tags=["agent"])

SYSTEM_PROMPT = """你是溪东社区老人关怀助手「小溪」。你帮助社区工作者查询老人状态、活跃情况和告警信息。

回答要求：
- 简洁直接，用中文回答
- 优先使用工具获取实时数据，不要凭空编造数据
- 对于涉及老人隐私的信息，仅提供必要的工作信息
- 语气温暖专业，体现对老人的关怀
- 当回复涉及特定老人时，用 [[elder:老人社区档案ID:老人姓名]] 标记，例如 [[elder:abc123:王秀英]]
- 确认活跃操作完成后，告知工作者已记录
- 展示趋势数据时用简洁的文字描述变化方向"""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _convert_tools_to_openai(tools):
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


@router.post("/agent/chat")
async def agent_chat(
    data: ChatRequest,
    worker: CommunityWorker = Depends(get_current_worker),
):
    client = get_client()
    if not client:
        async def no_key():
            yield f"data: {json.dumps({'type': 'text_delta', 'content': 'AI 功能未配置，请联系管理员设置 LLM_API_KEY。'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(no_key(), media_type="text/event-stream")

    return StreamingResponse(
        _stream_response(data.messages, worker),
        media_type="text/event-stream",
    )


async def _stream_response(
    messages: list[ChatMessage],
    worker: CommunityWorker,
) -> AsyncGenerator[str, None]:
    from app.services.agent import TOOLS, execute_tool

    client = get_client()
    openai_tools = _convert_tools_to_openai(TOOLS)

    api_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ] + [{"role": m.role, "content": m.content} for m in messages]

    try:
        response = await client.chat.completions.create(
            model=get_model(),
            max_tokens=1024,
            tools=openai_tools,
            messages=api_messages,
        )

        max_rounds = 5
        round_count = 0

        while response.choices[0].finish_reason == "tool_calls" and round_count < max_rounds:
            round_count += 1
            assistant_msg = response.choices[0].message

            if assistant_msg.content:
                yield f"data: {json.dumps({'type': 'text_delta', 'content': assistant_msg.content}, ensure_ascii=False)}\n\n"

            api_messages.append(assistant_msg.model_dump(exclude_none=True))

            for tc in assistant_msg.tool_calls:
                func_name = tc.function.name
                func_args = json.loads(tc.function.arguments) if tc.function.arguments else {}

                yield f"data: {json.dumps({'type': 'tool_use', 'name': func_name}, ensure_ascii=False)}\n\n"

                async with async_session() as db:
                    result_str = await execute_tool(db, worker.community_id, func_name, func_args, worker_id=worker.id)

                api_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })

            response = await client.chat.completions.create(
                model=get_model(),
                max_tokens=1024,
                tools=openai_tools,
                messages=api_messages,
            )

        final_content = response.choices[0].message.content
        if final_content:
            yield f"data: {json.dumps({'type': 'text_delta', 'content': final_content}, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.exception("Agent chat error")
        yield f"data: {json.dumps({'type': 'error', 'content': f'AI 服务暂时不可用: {str(e)}'}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"
