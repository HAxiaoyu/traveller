import json
from datetime import datetime, timezone

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
            "model_provider": body.model_provider,
            "model_name": body.model_name,
            "api_key": body.api_key,
            "slots_filled": False,
            "missing_slots": [],
            "follow_up_question": "",
        }

        final_state = await graph.ainvoke(state)

        for step in final_state.get("intermediate_steps", []):
            yield f"event: status\ndata: {json.dumps({'content': step})}\n\n"

        ai_content: str
        if final_state.get("slots_filled"):
            travel_plan = final_state.get("travel_plan")
            if travel_plan and travel_plan.get("days"):
                day_count = len(travel_plan["days"])
                ai_content = f"已为您规划好 {travel_plan['title']}，共 {day_count} 天行程，请查看。"
            else:
                ai_content = f"收到您的消息：「{body.message}」\n\nAgent 流水线已就绪，各节点执行完毕。"
        else:
            question = final_state.get("follow_up_question", "请告诉我更多关于您旅行的偏好。")
            ai_content = question

        ai_msg = {"role": "assistant", "content": ai_content}
        messages.append(ai_msg)

        session.messages = messages
        session.slots = final_state.get("slots", {})
        session.travel_plan = final_state.get("travel_plan")
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()

        yield f"event: done\ndata: {json.dumps({'content': ai_content, 'travel_plan': final_state.get('travel_plan'), 'slots_filled': final_state.get('slots_filled', False)})}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'content': '处理您的请求时遇到问题，请稍后重试'})}\n\n"


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
