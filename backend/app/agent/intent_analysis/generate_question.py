from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.intent_analysis.prompts import GENERATE_QUESTION_SYSTEM_PROMPT
from app.agent.llm_factory import create_chat_model
from app.agent.state import TravelPlannerState


async def generate_question(state: TravelPlannerState) -> dict:
    model: BaseChatModel = create_chat_model(
        state.get("model_provider", "openai"),
        state.get("model_name", "gpt-4o"),
        state.get("api_key", ""),
        state.get("base_url", ""),
    )
    slots: dict = state.get("slots", {})
    missing: list[str] = state.get("missing_slots", [])

    known = {k: v for k, v in slots.items() if v}
    known_text = "\n".join(f"- {k}: {v}" for k, v in known.items()) if known else "暂无"

    prompt = GENERATE_QUESTION_SYSTEM_PROMPT.format(
        known_slots=known_text,
        missing_slots="、".join(missing),
    )

    try:
        response = await model.ainvoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content="请生成一个追问，收集缺失的信息。"),
            ]
        )
        question: str = response.content.strip()
    except Exception:
        question = f"请告诉我更多关于{'、'.join(missing)}的信息吧～"
    steps: list[str] = list(state.get("intermediate_steps", []))
    steps.append(f"intent_analysis: 追问 → {question}")

    return {"intermediate_steps": steps, "follow_up_question": question}
