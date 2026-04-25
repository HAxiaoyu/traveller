import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage


# ═══════════════════════════════════════════════════════════════
# Schema 校验
# ═══════════════════════════════════════════════════════════════


VALID_PLAN = {
    "title": "东京7日美食之旅",
    "days": [
        {
            "day": 1,
            "city": "东京",
            "theme": "浅草美食",
            "activities": [
                {
                    "name": "浅草寺",
                    "type": "景点",
                    "lat": None,
                    "lng": None,
                    "duration": "1.5h",
                    "time": "09:00",
                    "notes": "",
                }
            ],
            "transport": {"mode": "步行", "duration": "约20分钟"},
            "hotel": "浅草地区酒店",
        }
    ],
}


def test_schema_validates_complete_plan():
    from app.agent.plan_generation.schema import TravelPlan

    plan = TravelPlan.model_validate(VALID_PLAN)
    assert plan.title == "东京7日美食之旅"
    assert len(plan.days) == 1
    assert plan.days[0].city == "东京"
    assert plan.days[0].activities[0].name == "浅草寺"


def test_schema_defaults_activity_fields():
    from app.agent.plan_generation.schema import Activity

    act = Activity.model_validate({"name": "测试景点"})
    assert act.type == "景点"
    assert act.lat is None
    assert act.duration == "1h"
    assert act.time == "09:00"


def test_schema_defaults_transport():
    from app.agent.plan_generation.schema import Transport

    t = Transport()
    assert t.mode == "公共交通"
    assert t.duration == "约30分钟"


def test_schema_rejects_empty_days():
    from app.agent.plan_generation.schema import TravelPlan

    with pytest.raises(Exception):
        TravelPlan.model_validate({"title": "空行程", "days": []})


def test_schema_rejects_empty_activities():
    from app.agent.plan_generation.schema import DayPlan

    with pytest.raises(Exception):
        DayPlan.model_validate({"day": 1, "city": "东京", "activities": []})


def test_schema_rejects_missing_title():
    from app.agent.plan_generation.schema import TravelPlan

    with pytest.raises(Exception):
        TravelPlan.model_validate({"days": [{"day": 1, "city": "x", "activities": [{"name": "y"}]}]})


def test_travel_plan_model_dump():
    from app.agent.plan_generation.schema import TravelPlan

    plan = TravelPlan.model_validate(VALID_PLAN)
    dumped = plan.model_dump()
    assert dumped["days"][0]["activities"][0]["name"] == "浅草寺"


# ═══════════════════════════════════════════════════════════════
# generate_plan 节点
# ═══════════════════════════════════════════════════════════════


def make_state(slots=None, intermediate_steps=None, travel_plan=None):
    return {
        "messages": [],
        "slots": slots or {},
        "travel_plan": travel_plan,
        "intermediate_steps": intermediate_steps or [],
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "",
        "slots_filled": True,
        "missing_slots": [],
        "follow_up_question": "",
        "formatted_response": "",
    }


@pytest.mark.asyncio
async def test_generate_plan_produces_valid_travel_plan(mock_llm):
    from app.agent.plan_generation.generate import generate_plan

    mock_llm.ainvoke.return_value.content = json.dumps(VALID_PLAN, ensure_ascii=False)

    state = make_state(
        slots={"destination": "东京", "days": 7, "interests": ["美食"], "energy_level": "适中"}
    )
    result = await generate_plan(state)

    assert result["travel_plan"] is not None
    assert result["travel_plan"]["title"] == "东京7日美食之旅"
    assert "行程方案生成成功" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_generate_plan_strips_markdown_fence(mock_llm):
    from app.agent.plan_generation.generate import generate_plan

    mock_llm.ainvoke.return_value.content = (
        "```json\n" + json.dumps(VALID_PLAN, ensure_ascii=False) + "\n```"
    )

    state = make_state(slots={"destination": "东京", "days": 7, "interests": ["美食"]})
    result = await generate_plan(state)

    assert result["travel_plan"] is not None
    assert result["travel_plan"]["title"] == "东京7日美食之旅"


@pytest.mark.asyncio
async def test_generate_plan_strips_fence_same_line(mock_llm):
    from app.agent.plan_generation.generate import generate_plan

    mock_llm.ainvoke.return_value.content = (
        "```json\n" + json.dumps(VALID_PLAN, ensure_ascii=False) + "```"
    )

    state = make_state(slots={"destination": "东京", "days": 7, "interests": ["美食"]})
    result = await generate_plan(state)

    assert result["travel_plan"] is not None
    assert result["travel_plan"]["title"] == "东京7日美食之旅"


@pytest.mark.asyncio
async def test_generate_plan_invalid_json_retries(mock_llm):
    from app.agent.plan_generation.generate import generate_plan

    r1 = MagicMock()
    r1.content = "not valid json!!!"
    r2 = MagicMock()
    r2.content = json.dumps(VALID_PLAN, ensure_ascii=False)
    mock_llm.ainvoke.side_effect = [r1, r2]

    state = make_state(slots={"destination": "东京", "days": 7, "interests": ["美食"]})
    result = await generate_plan(state)

    assert result["travel_plan"] is not None
    assert any("重试" in s for s in result["intermediate_steps"])


@pytest.mark.asyncio
async def test_generate_plan_both_attempts_fail(mock_llm):
    from app.agent.plan_generation.generate import generate_plan

    r1 = MagicMock()
    r1.content = "bad json 1"
    r2 = MagicMock()
    r2.content = "bad json 2"
    mock_llm.ainvoke.side_effect = [r1, r2]

    state = make_state(slots={"destination": "东京", "days": 7, "interests": ["美食"]})
    result = await generate_plan(state)

    assert result.get("travel_plan") is None
    assert "行程生成失败" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_generate_plan_llm_exception(mock_llm):
    from app.agent.plan_generation.generate import generate_plan

    mock_llm.ainvoke.side_effect = RuntimeError("网络错误")

    state = make_state(slots={"destination": "东京", "days": 7, "interests": ["美食"]})
    result = await generate_plan(state)

    assert result.get("travel_plan") is None
    assert "LLM 调用失败" in str(result["intermediate_steps"])


@pytest.mark.asyncio
async def test_generate_plan_immutability(mock_llm):
    from app.agent.plan_generation.generate import generate_plan

    mock_llm.ainvoke.return_value.content = json.dumps(VALID_PLAN, ensure_ascii=False)

    original_steps = ["before"]
    original_slots = {"destination": "东京", "days": 7, "interests": ["美食"]}
    state = make_state(slots=original_slots, intermediate_steps=original_steps)
    await generate_plan(state)

    assert state["intermediate_steps"] == ["before"]
    assert state["travel_plan"] is None
    assert state["slots"] == original_slots


@pytest.mark.asyncio
async def test_generate_plan_validates_schema(mock_llm):
    from app.agent.plan_generation.generate import generate_plan

    bad_plan = {"title": "Bad", "days": [{"day": 1, "city": "Tokyo", "activities": []}]}
    mock_llm.ainvoke.return_value.content = json.dumps(bad_plan)

    state = make_state(slots={"destination": "东京", "days": 7, "interests": ["美食"]})
    result = await generate_plan(state)

    assert result.get("travel_plan") is None
    assert any("重试" in s or "失败" in s for s in result["intermediate_steps"])


# ═══════════════════════════════════════════════════════════════
# 主图集成
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_main_graph_produces_travel_plan(mock_llm, mock_enrichment):
    from langchain_core.messages import HumanMessage

    from app.agent.graph import build_agent_graph

    slots_r = MagicMock()
    slots_r.content = json.dumps({})
    plan_r = MagicMock()
    plan_r.content = json.dumps(VALID_PLAN, ensure_ascii=False)
    mock_llm.ainvoke.side_effect = [slots_r, plan_r]

    graph = build_agent_graph()
    state = {
        "messages": [HumanMessage(content="ok")],
        "slots": {"destination": "东京", "days": 7, "interests": ["美食"]},
        "travel_plan": None,
        "intermediate_steps": [],
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "",
        "slots_filled": False,
        "missing_slots": [],
        "follow_up_question": "",
        "formatted_response": "",
    }

    result = await graph.ainvoke(state)

    assert result["travel_plan"] is not None
    assert result["travel_plan"]["title"] == "东京7日美食之旅"
    assert result["slots_filled"] is True
