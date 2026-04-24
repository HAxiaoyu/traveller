import json
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import build_agent_graph
from app.database import get_session
from app.models import Session
from app.schemas import ChatRequest

router = APIRouter(prefix="/api")


async def event_stream(session_id: str, body: ChatRequest, db: AsyncSession):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        yield f"event: error\ndata: {json.dumps({'content': '会话不存在'})}\n\n"
        return

    user_msg = {"role": "user", "content": body.message}
    messages: list = list(session.messages)
    messages.append(user_msg)

    yield f"event: status\ndata: {json.dumps({'content': '正在分析您的偏好...'})}\n\n"

    try:
        graph = build_agent_graph()
        state = {
            "messages": [HumanMessage(content=body.message)],
            "slots": session.slots or {},
            "travel_plan": None,
            "intermediate_steps": [],
        }

        final_state = await graph.ainvoke(state)

        for step in final_state.get("intermediate_steps", []):
            yield f"event: status\ndata: {json.dumps({'content': step})}\n\n"

        echo_reply = (
            f"收到您的消息：「{body.message}」\n\nAgent 流水线已就绪，各节点执行完毕。"
        )

        ai_msg = {"role": "assistant", "content": echo_reply}
        messages.append(ai_msg)

        session.messages = messages
        session.updated_at = datetime.utcnow()
        await db.commit()

        yield f"event: done\ndata: {json.dumps({'content': echo_reply, 'travel_plan': None})}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'content': f'处理出错: {str(e)}'})}\n\n"


@router.post("/chat/{session_id}")
async def chat(
    session_id: str, body: ChatRequest, db: AsyncSession = Depends(get_session)
):
    return StreamingResponse(
        event_stream(session_id, body, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
