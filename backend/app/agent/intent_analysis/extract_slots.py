import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from app.agent.intent_analysis.prompts import EXTRACT_SLOTS_SYSTEM_PROMPT
from app.agent.llm_factory import create_chat_model
from app.agent.state import TravelPlannerState


async def extract_slots(state: TravelPlannerState) -> dict:
    model: BaseChatModel = create_chat_model(
        state.get("model_provider", "openai"),
        state.get("model_name", "gpt-4o"),
        state.get("api_key", ""),
    )
    slots: dict = dict(state.get("slots", {}))
    messages: list = list(state.get("messages", []))

    prompt = EXTRACT_SLOTS_SYSTEM_PROMPT.format(
        current_slots=json.dumps(slots, ensure_ascii=False) if slots else "暂无"
    )

    try:
        response = await model.ainvoke([
            SystemMessage(content=prompt),
            HumanMessage(content="请从对话中提取用户最新一条消息中的旅行偏好信息。"),
            *messages,
        ])
        content: str = response.content
    except Exception:
        steps: list[str] = list(state.get("intermediate_steps", []))
        steps.append("intent_analysis: LLM 调用失败，跳过偏好提取")
        return {"slots": slots, "intermediate_steps": steps}

    try:
        extracted: dict = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        steps: list[str] = list(state.get("intermediate_steps", []))
        steps.append("intent_analysis: 未从当前消息提取到新的偏好信息")
        return {"slots": slots, "intermediate_steps": steps}

    merged: dict = {**slots, **extracted}

    if "days" in merged and isinstance(merged["days"], str):
        try:
            merged["days"] = int(merged["days"])
        except ValueError:
            pass

    if "interest" in merged:
        if "interests" in merged:
            if isinstance(merged["interest"], str):
                merged["interests"] = list(merged["interests"]) + [merged.pop("interest")]
            else:
                merged.pop("interest")
        else:
            merged["interests"] = merged.pop("interest")
    if "interests" in merged and isinstance(merged["interests"], str):
        merged["interests"] = [merged["interests"]]

    steps: list[str] = list(state.get("intermediate_steps", []))
    if extracted:
        steps.append(f"intent_analysis: 提取到偏好 → {json.dumps(extracted, ensure_ascii=False)}")
    else:
        steps.append("intent_analysis: 未从当前消息提取到新的偏好信息")

    return {"slots": merged, "intermediate_steps": steps}
