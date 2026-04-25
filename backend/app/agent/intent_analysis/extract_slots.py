import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel

from app.agent.intent_analysis.prompts import EXTRACT_SLOTS_SYSTEM_PROMPT
from app.agent.llm_factory import create_chat_model
from app.agent.state import TravelPlannerState

# CJK Unified Ideographs range
_CJK_RANGE = chr(0x4e00) + "-" + chr(0x9fff)


def _extract_json(text: str) -> dict | None:
    """从 LLM 回复中提取 JSON 对象，兼容 markdown 包裹和前导文字。"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if block_match:
        try:
            return json.loads(block_match.group(1).strip())
        except json.JSONDecodeError:
            pass
    brace_match = re.search(r'\{.*?\}', text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _extract_from_message(text: str) -> dict:
    """纯文本规则兜底：从用户消息中提取目的地。"""
    result: dict = {}
    patterns = [
        (rf"去([{_CJK_RANGE}]{{2,6}}?)(?:玩|旅游|度假|旅行|的|$)", "destination"),
        (rf"到([{_CJK_RANGE}]{{2,6}}?)(?:玩|旅游|度假|旅行|去|$)", "destination"),
        (rf"在([{_CJK_RANGE}]{{2,6}}?)(?:玩|旅游|度假|旅行|$)", "destination"),
    ]
    for pattern, key in patterns:
        m = re.search(pattern, text)
        if m:
            result[key] = m.group(1).strip()
            break
    return result


async def extract_slots(state: TravelPlannerState) -> dict:
    model: BaseChatModel = create_chat_model(
        state.get("model_provider", "openai"),
        state.get("model_name", "gpt-4o"),
        state.get("api_key", ""),
        state.get("base_url", ""),
    )
    slots: dict = dict(state.get("slots", {}))
    messages: list = list(state.get("messages", []))

    prompt = EXTRACT_SLOTS_SYSTEM_PROMPT.format(
        current_slots=json.dumps(slots, ensure_ascii=False) if slots else "暂无"
    )

    try:
        response = await model.ainvoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(
                    content="请从对话中提取用户最新一条消息中的旅行偏好信息。"
                ),
                *messages,
            ]
        )
        content: str = response.content if isinstance(response.content, str) else str(response.content)
    except Exception:
        steps: list[str] = list(state.get("intermediate_steps", []))
        steps.append("intent_analysis: LLM 调用失败，跳过偏好提取")
        return {"slots": slots, "intermediate_steps": steps}

    extracted: dict | None = _extract_json(content)
    if extracted is None:
        user_text = " ".join(
            m.content for m in messages if hasattr(m, "content") and isinstance(m.content, str)
        )
        extracted = _extract_from_message(user_text)

    if not extracted:
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
                merged["interests"] = list(merged["interests"]) + [
                    merged.pop("interest")
                ]
            else:
                merged.pop("interest")
        else:
            merged["interests"] = merged.pop("interest")
    if "interests" in merged and isinstance(merged["interests"], str):
        merged["interests"] = [merged["interests"]]

    steps: list[str] = list(state.get("intermediate_steps", []))
    if extracted:
        steps.append(
            f"intent_analysis: 提取到偏好 → {json.dumps(extracted, ensure_ascii=False)}"
        )
    else:
        steps.append("intent_analysis: 未从当前消息提取到新的偏好信息")

    return {"slots": merged, "intermediate_steps": steps}
