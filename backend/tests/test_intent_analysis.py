import json

import pytest
from langchain_core.messages import HumanMessage, SystemMessage


# ═══════════════════════════════════════════════════════════════
# check_slots — 纯逻辑，无需 mock
# ═══════════════════════════════════════════════════════════════


def make_state(
    messages=None,
    slots=None,
    intermediate_steps=None,
    missing_slots=None,
    follow_up_question=None,
    slots_filled=None,
):
    return {
        "messages": messages or [],
        "slots": slots or {},
        "travel_plan": None,
        "intermediate_steps": intermediate_steps or [],
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "",
        "slots_filled": slots_filled if slots_filled is not None else False,
        "missing_slots": missing_slots or [],
        "follow_up_question": follow_up_question or "",
    }


@pytest.mark.asyncio
async def test_check_slots_all_filled():
    from app.agent.intent_analysis.check_slots import check_slots

    state = make_state(slots={"destination": "东京", "days": 7, "interests": ["美食"]})
    result = await check_slots(state)

    assert result["slots_filled"] is True
    assert result["slots"]["energy_level"] == "适中"
    assert "所有必填槽位已填充" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_check_slots_energy_already_set():
    from app.agent.intent_analysis.check_slots import check_slots

    state = make_state(
        slots={
            "destination": "东京",
            "days": 5,
            "interests": ["自然"],
            "energy_level": "轻松",
        }
    )
    result = await check_slots(state)

    assert result["slots_filled"] is True
    assert result["slots"]["energy_level"] == "轻松"


@pytest.mark.asyncio
async def test_check_slots_missing_destination():
    from app.agent.intent_analysis.check_slots import check_slots

    state = make_state(slots={"days": 3, "interests": ["购物"]})
    result = await check_slots(state)

    assert result["slots_filled"] is False
    assert "destination" in result["missing_slots"]
    assert "槽位不完整" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_check_slots_missing_multiple():
    from app.agent.intent_analysis.check_slots import check_slots

    state = make_state(slots={})
    result = await check_slots(state)

    assert result["slots_filled"] is False
    assert len(result["missing_slots"]) == 3
    assert "destination" in result["missing_slots"]
    assert "days" in result["missing_slots"]
    assert "interests" in result["missing_slots"]


@pytest.mark.asyncio
async def test_check_slots_empty_interests():
    from app.agent.intent_analysis.check_slots import check_slots

    state = make_state(slots={"destination": "京都", "interests": []})
    result = await check_slots(state)

    assert result["slots_filled"] is False
    assert "interests" in result["missing_slots"]


@pytest.mark.asyncio
async def test_check_slots_immutability():
    from app.agent.intent_analysis.check_slots import check_slots

    original_slots = {"destination": "大阪"}
    state = make_state(slots=original_slots, intermediate_steps=["before"])
    await check_slots(state)

    assert state["slots"] == {"destination": "大阪"}
    assert "energy_level" not in state["slots"]
    assert state["intermediate_steps"] == ["before"]


# ═══════════════════════════════════════════════════════════════
# extract_slots — LLM mock
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_extract_slots_merges_new_values(mock_llm):
    from app.agent.intent_analysis.extract_slots import extract_slots

    mock_llm.ainvoke.return_value.content = json.dumps(
        {"destination": "东京", "days": 7}
    )

    state = make_state(
        messages=[HumanMessage(content="想去东京玩7天")],
        slots={"interests": ["美食"]},
    )
    result = await extract_slots(state)

    assert result["slots"]["destination"] == "东京"
    assert result["slots"]["days"] == 7
    assert result["slots"]["interests"] == ["美食"]
    assert "提取到偏好" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_extract_slots_preserves_existing(mock_llm):
    from app.agent.intent_analysis.extract_slots import extract_slots

    mock_llm.ainvoke.return_value.content = json.dumps({"destination": "大阪"})

    state = make_state(
        messages=[HumanMessage(content="改去大阪吧")],
        slots={"destination": "东京", "days": 5},
    )
    result = await extract_slots(state)

    assert result["slots"]["destination"] == "大阪"
    assert result["slots"]["days"] == 5


@pytest.mark.asyncio
async def test_extract_slots_empty_response(mock_llm):
    from app.agent.intent_analysis.extract_slots import extract_slots

    mock_llm.ainvoke.return_value.content = json.dumps({})

    state = make_state(
        messages=[HumanMessage(content="你好")],
        slots={"destination": "东京"},
    )
    result = await extract_slots(state)

    assert result["slots"] == {"destination": "东京"}
    assert "未从当前消息提取到新的偏好信息" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_extract_slots_invalid_json(mock_llm):
    from app.agent.intent_analysis.extract_slots import extract_slots

    mock_llm.ainvoke.return_value.content = "not valid json"

    state = make_state(
        messages=[HumanMessage(content="想去日本")],
        slots={},
    )
    result = await extract_slots(state)

    assert result["slots"] == {}


@pytest.mark.asyncio
async def test_extract_slots_immutability(mock_llm):
    from app.agent.intent_analysis.extract_slots import extract_slots

    mock_llm.ainvoke.return_value.content = json.dumps({"destination": "北海道"})

    original_slots = {"days": 3}
    state = make_state(messages=[HumanMessage(content="北海道")], slots=original_slots)
    await extract_slots(state)

    assert state["slots"] == {"days": 3}
    assert "destination" not in state["slots"]


# ═══════════════════════════════════════════════════════════════
# generate_question — LLM mock
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_generate_question_asks_about_missing(mock_llm):
    from app.agent.intent_analysis.generate_question import generate_question

    mock_llm.ainvoke.return_value.content = "请问您计划去多少天呢？"

    state = make_state(
        slots={"destination": "东京", "interests": ["美食"]},
        missing_slots=["days"],
    )
    result = await generate_question(state)

    assert "follow_up_question" in result
    assert "请问您计划去多少天呢？" == result["follow_up_question"]
    assert "追问 →" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_generate_question_immutability(mock_llm):
    from app.agent.intent_analysis.generate_question import generate_question

    mock_llm.ainvoke.return_value.content = "您的预算是多少？"

    original_steps = ["existing_step"]
    state = make_state(
        slots={},
        intermediate_steps=original_steps,
        missing_slots=["destination"],
    )
    await generate_question(state)

    assert state["intermediate_steps"] == ["existing_step"]
    assert state["follow_up_question"] == ""


# ═══════════════════════════════════════════════════════════════
# subgraph 集成测试
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_subgraph_slots_complete_exits(mock_llm):
    from app.agent.intent_analysis import build_intent_analysis_subgraph

    mock_llm.ainvoke.return_value.content = json.dumps({})

    subgraph = build_intent_analysis_subgraph()
    state = make_state(
        messages=[HumanMessage(content="ok")],
        slots={"destination": "东京", "days": 7, "interests": ["美食", "自然"]},
    )

    result = await subgraph.ainvoke(state)
    assert result["slots_filled"] is True


@pytest.mark.asyncio
async def test_subgraph_slots_incomplete_generates_question(mock_llm):
    from app.agent.intent_analysis import build_intent_analysis_subgraph

    mock_llm.ainvoke.return_value.content = "您想去哪里旅行呢？"

    subgraph = build_intent_analysis_subgraph()
    state = make_state(
        messages=[HumanMessage(content="hi")],
        slots={"days": 5},
    )

    result = await subgraph.ainvoke(state)
    assert result["slots_filled"] is False
    assert "follow_up_question" in result


# ═══════════════════════════════════════════════════════════════
# 主图条件路由
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_main_graph_routes_to_end_when_slots_incomplete(mock_llm):
    from app.agent.graph import build_agent_graph

    mock_llm.ainvoke.return_value.content = "您想去哪里？"

    graph = build_agent_graph()
    state = make_state(
        messages=[HumanMessage(content="你好")],
        slots={},
    )

    result = await graph.ainvoke(state)
    steps = result["intermediate_steps"]

    assert result["slots_filled"] is False
    assert "follow_up_question" in result
    assert not any("plan_generation" in s for s in steps)


@pytest.mark.asyncio
async def test_main_graph_routes_to_planning_when_slots_complete(mock_llm):
    from app.agent.graph import build_agent_graph

    mock_llm.ainvoke.return_value.content = json.dumps({})

    graph = build_agent_graph()
    state = make_state(
        messages=[HumanMessage(content="ok")],
        slots={"destination": "东京", "days": 7, "interests": ["美食"]},
    )

    result = await graph.ainvoke(state)
    steps = result["intermediate_steps"]

    assert result["slots_filled"] is True
    assert any("plan_generation" in s for s in steps)
    assert any("enrichment" in s for s in steps)
    assert any("format_response" in s for s in steps)


# ═══════════════════════════════════════════════════════════════
# 边界情况
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_extract_slots_llm_failure_skips(mock_llm):
    from app.agent.intent_analysis.extract_slots import extract_slots

    mock_llm.ainvoke.side_effect = RuntimeError("API 不可用")

    state = make_state(
        messages=[HumanMessage(content="想去东京")],
        slots={"days": 3},
    )
    result = await extract_slots(state)

    assert result["slots"] == {"days": 3}
    assert "LLM 调用失败" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_generate_question_llm_failure_fallback(mock_llm):
    from app.agent.intent_analysis.generate_question import generate_question

    mock_llm.ainvoke.side_effect = RuntimeError("API 不可用")

    state = make_state(missing_slots=["destination", "days"])
    result = await generate_question(state)

    assert "destination" in result["follow_up_question"]
    assert "days" in result["follow_up_question"]


def test_llm_factory_unknown_provider_raises():
    from app.agent.llm_factory import create_chat_model

    with pytest.raises(ValueError, match="不支持的模型提供商"):
        create_chat_model("unknown", "gpt-4o", "sk-test")


@pytest.mark.asyncio
async def test_extract_slots_normalizes_interest_key(mock_llm):
    from app.agent.intent_analysis.extract_slots import extract_slots

    mock_llm.ainvoke.return_value.content = json.dumps(
        {"interest": "购物", "destination": "大阪"}
    )

    state = make_state(messages=[HumanMessage(content="想去大阪购物")])
    result = await extract_slots(state)

    assert "interests" in result["slots"]
    assert result["slots"]["interests"] == ["购物"]
    assert "interest" not in result["slots"]


@pytest.mark.asyncio
async def test_extract_slots_merges_interest_with_existing(mock_llm):
    from app.agent.intent_analysis.extract_slots import extract_slots

    mock_llm.ainvoke.return_value.content = json.dumps({"interest": "自然"})

    state = make_state(
        messages=[HumanMessage(content="也喜欢自然")],
        slots={"interests": ["美食"]},
    )
    result = await extract_slots(state)

    assert "interests" in result["slots"]
    assert result["slots"]["interests"] == ["美食", "自然"]
    assert "interest" not in result["slots"]


# ═══════════════════════════════════════════════════════════════
# LLM factory
# ═══════════════════════════════════════════════════════════════


def test_llm_factory_returns_openai():
    from app.agent.llm_factory import create_chat_model

    model = create_chat_model("openai", "gpt-4o", "sk-test")
    from langchain_openai import ChatOpenAI

    assert isinstance(model, ChatOpenAI)


def test_llm_factory_returns_anthropic():
    from app.agent.llm_factory import create_chat_model

    model = create_chat_model("anthropic", "claude-sonnet-4-6", "sk-ant-test")
    from langchain_anthropic import ChatAnthropic

    assert isinstance(model, ChatAnthropic)
