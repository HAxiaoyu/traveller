import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import build_agent_graph
from app.database import async_session
from app.models import Session

router = APIRouter(prefix="/api")

_NODE_LABELS: dict[str, str] = {
    "extract_slots": "intent_analysis: 正在分析出行偏好...",
    "check_slots": "intent_analysis: 正在检查信息完整性...",
    "generate_question": "intent_analysis: 正在生成追问...",
    "plan_generation": "plan_generation: 正在调用 AI 生成行程方案...",
    "enrichment": "enrichment: 正在获取坐标和天气信息...",
    "format_response": "format_response: 正在整理回复...",
}


def _derive_title(message: str, slots: dict) -> str:
    destination: str = slots.get("destination", "")
    days = slots.get("days", 0)
    if destination and days:
        return f"{destination}{days}日游"
    if destination:
        return f"{destination}之旅"
    clean: str = message.strip().rstrip("。！？….")
    if len(clean) > 20:
        clean = clean[:20] + "…"
    return clean or "新规划"


def _hint_from_error(err_msg: str) -> str:
    lower = err_msg.lower()
    if "api_key" in lower or "unauthorized" in lower or "invalid" in lower:
        return "API Key 无效或未配置，请在设置中检查。"
    if "timeout" in lower or "timed out" in lower:
        return "请求超时，请稍后重试。"
    return "处理您的请求时遇到问题，请稍后重试。"


async def _build_ai_content(final_state: dict, default_message: str) -> str:
    formatted = final_state.get("formatted_response", "")
    if formatted:
        return formatted
    if final_state.get("slots_filled"):
        travel_plan = final_state.get("travel_plan")
        if travel_plan and travel_plan.get("days"):
            return f"已为您规划好 {travel_plan['title']}，共 {len(travel_plan['days'])} 天行程，请查看。"
        return f"收到您的消息：「{default_message}」\n\nAgent 流水线已就绪，各节点执行完毕。"
    return final_state.get("follow_up_question", "请告诉我更多关于您旅行的偏好。")


async def _send(websocket: WebSocket, data: dict) -> bool:
    """发送消息到 WebSocket，连接断开时返回 False。"""
    try:
        await websocket.send_json(data)
        return True
    except WebSocketDisconnect:
        return False


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        raw = await websocket.receive_json()
    except WebSocketDisconnect:
        return

    if raw.get("type") != "chat":
        await websocket.send_json({"type": "error", "content": "无效的消息类型"})
        return

    message: str = (raw.get("message") or "").strip()
    if not message:
        await websocket.send_json({"type": "error", "content": "消息不能为空"})
        return

    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if session is None:
            await websocket.send_json({"type": "error", "content": "会话不存在"})
            return

        user_msg = {"role": "user", "content": message}
        messages: list = list(session.messages)
        messages.append(user_msg)

        ok = await _send(websocket, {"type": "status", "content": "正在分析您的偏好..."})
        if not ok:
            return

        try:
            graph = build_agent_graph()
            state = {
                "messages": [HumanMessage(content=message)],
                "slots": session.slots or {},
                "travel_plan": None,
                "intermediate_steps": [],
                "model_provider": raw.get("model_provider", "openai"),
                "model_name": raw.get("model_name", "gpt-4o"),
                "api_key": raw.get("api_key", ""),
                "base_url": raw.get("base_url", ""),
                "google_maps_key": raw.get("google_maps_key", ""),
                "weather_api_key": raw.get("weather_api_key", ""),
                "slots_filled": False,
                "missing_slots": [],
                "follow_up_question": "",
                "formatted_response": "",
            }

            last_step_count = 0
            accumulated_state = dict(state)
            current_phase_key = ""
            disconnected = False

            async for event in graph.astream_events(state, version="v1"):
                kind = event.get("event", "")
                name = event.get("name", "")

                if kind == "on_chain_start" and name in _NODE_LABELS:
                    label = _NODE_LABELS[name]
                    current_phase_key = label.split(":")[0]
                    if not disconnected:
                        ok = await _send(websocket, {"type": "status", "content": label})
                        if not ok:
                            disconnected = True
                    continue

                if kind == "on_chat_model_stream" and not disconnected:
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is not None:
                        text = chunk.content if hasattr(chunk, "content") else str(chunk)
                        if text:
                            ok = await _send(websocket, {"type": "token", "content": text})
                            if not ok:
                                disconnected = True
                    continue

                if kind != "on_chain_end":
                    continue
                if name == "LangGraph":
                    continue
                output = event.get("data", {}).get("output", {})
                if not isinstance(output, dict):
                    continue
                accumulated_state.update(output)
                steps: list[str] = accumulated_state.get("intermediate_steps", [])
                for step in steps[last_step_count:]:
                    if not disconnected:
                        ok = await _send(websocket, {"type": "status", "content": step})
                        if not ok:
                            disconnected = True
                last_step_count = len(steps)

            final_state = accumulated_state
            ai_content = await _build_ai_content(final_state, message)

            if session.title == "新规划" and len(session.messages) == 0:
                session.title = _derive_title(message, final_state.get("slots", {}))

            ai_msg = {"role": "assistant", "content": ai_content}
            messages.append(ai_msg)
            session.messages = messages
            session.slots = final_state.get("slots", {})
            session.travel_plan = final_state.get("travel_plan")
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()

            if not disconnected:
                await _send(websocket, {
                    "type": "done",
                    "content": ai_content,
                    "travel_plan": final_state.get("travel_plan"),
                    "slots_filled": final_state.get("slots_filled", False),
                })

        except Exception as e:
            hint = _hint_from_error(str(e))
            await _send(websocket, {"type": "error", "content": hint})
