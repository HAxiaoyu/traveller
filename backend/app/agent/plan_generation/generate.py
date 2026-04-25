import json
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm_factory import create_chat_model
from app.agent.plan_generation.prompts import (
    PLAN_GENERATION_RETRY_PROMPT,
    PLAN_GENERATION_SYSTEM_PROMPT,
)
from app.agent.plan_generation.schema import TravelPlan
from app.agent.state import TravelPlannerState

ACTIVITY_COUNTS = {"轻松": (3, 4), "适中": (4, 5), "高强度": (5, 7)}


async def generate_plan(state: TravelPlannerState) -> dict:
    model: BaseChatModel = create_chat_model(
        state.get("model_provider", "openai"),
        state.get("model_name", "gpt-4o"),
        state.get("api_key", ""),
        state.get("base_url", ""),
    )
    slots: dict = state.get("slots", {})
    steps: list[str] = list(state.get("intermediate_steps", []))

    destination: str = slots.get("destination", "")
    days: int = slots.get("days", 3)
    interests: list = slots.get("interests", [])
    energy_level: str = slots.get("energy_level", "适中")
    min_act, max_act = ACTIVITY_COUNTS.get(energy_level, (4, 5))

    prompt = PLAN_GENERATION_SYSTEM_PROMPT.format(
        destination=destination,
        days=days,
        interests="、".join(interests) if interests else "不限",
        energy_level=energy_level,
        min_activities=min_act,
        max_activities=max_act,
    )

    plan = await _generate_with_retry(model, prompt, steps)
    if plan is not None:
        steps.append("plan_generation: 行程方案生成成功")
        return {
            "travel_plan": plan.model_dump(),
            "intermediate_steps": steps,
        }

    steps.append("plan_generation: 行程生成失败，JSON 解析错误")
    return {"intermediate_steps": steps}


async def _generate_with_retry(
    model: BaseChatModel, prompt: str, steps: list[str]
) -> TravelPlan | None:
    for attempt in range(2):
        steps.append("plan_generation: 正在调用 LLM 生成行程...")
        try:
            response = await model.ainvoke([
                SystemMessage(content=prompt),
                HumanMessage(content="请开始生成行程 JSON。"),
            ])
        except Exception:
            steps.append("plan_generation: LLM 调用失败")
            return None

        content: str = response.content.strip()

        content = re.sub(r'^```\w*\n?', '', content)
        content = re.sub(r'\n?```\s*$', '', content)
        content = content.strip()

        try:
            data: dict = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            if attempt == 0:
                prompt = PLAN_GENERATION_RETRY_PROMPT
                steps.append("plan_generation: JSON 解析失败，正在重试...")
                continue
            return None

        try:
            return TravelPlan.model_validate(data)
        except Exception:
            if attempt == 0:
                prompt = PLAN_GENERATION_RETRY_PROMPT
                steps.append("plan_generation: 行程校验失败，正在重试...")
                continue
            return None

    return None
