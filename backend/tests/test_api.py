import json

import pytest


# ═══════════════════════════════════════════════════════════════
# 健康检查
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_health_check(client):
    """服务健康检查 —— 最基础的存活验证"""
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ═══════════════════════════════════════════════════════════════
# 会话 CRUD
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_session(client):
    """创建新会话 → 返回 UUID + 默认标题"""
    r = await client.post("/api/session", json={"title": "周末东京游"})
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["title"] == "周末东京游"
    assert "created_at" in data
    assert len(data["id"]) == 36  # UUID 格式


@pytest.mark.asyncio
async def test_create_session_default_title(client):
    """创建会话不传标题 → 使用默认值"""
    r = await client.post("/api/session", json={})
    assert r.status_code == 201
    assert r.json()["title"] == "新规划"


@pytest.mark.asyncio
async def test_list_sessions(client):
    """列出全部会话 → 按更新时间倒序"""
    await client.post("/api/session", json={"title": "A"})
    await client.post("/api/session", json={"title": "B"})

    r = await client.get("/api/history")
    assert r.status_code == 200
    sessions = r.json()
    assert len(sessions) == 2
    assert sessions[0]["title"] == "B"  # 最新的在前


@pytest.mark.asyncio
async def test_get_session_detail(client):
    """获取会话详情 → 含 messages / slots / travel_plan"""
    r = await client.post("/api/session", json={"title": "详情测试"})
    sid = r.json()["id"]

    r = await client.get(f"/api/session/{sid}")
    assert r.status_code == 200
    data = r.json()
    assert data["messages"] == []
    assert data["slots"] == {}
    assert data["travel_plan"] is None


@pytest.mark.asyncio
async def test_delete_session(client):
    """删除会话 → 204，二次查询 404"""
    r = await client.post("/api/session", json={})
    sid = r.json()["id"]

    r = await client.delete(f"/api/session/{sid}")
    assert r.status_code == 204

    r = await client.get(f"/api/session/{sid}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_session(client):
    """查询不存在的会话 → 404"""
    r = await client.get("/api/session/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert "不存在" in r.json()["detail"]


# ═══════════════════════════════════════════════════════════════
# SSE 聊天（Agent 流水线核心验证）
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_chat_sse_streams_status_events(client, mock_llm):
    """SSE 聊天 → 槽位不完整时输出追问流程"""
    mock_llm.ainvoke.return_value.content = "您想去哪里旅行呢？"

    r = await client.post("/api/session", json={})
    sid = r.json()["id"]

    r = await client.post(
        f"/api/chat/{sid}",
        json={"message": "你好"},
        timeout=10,
    )
    assert r.status_code == 200

    lines = [ln for ln in r.text.strip().split("\n") if ln]
    events = []
    for i in range(0, len(lines), 2):
        event_line = lines[i]
        data_line = lines[i + 1]
        evt_type = event_line.replace("event: ", "")
        payload = json.loads(data_line.replace("data: ", ""))
        events.append((evt_type, payload))

    assert len(events) == 5, f"期望 5 个事件，实际 {len(events)}"

    # 事件类型序列
    assert events[0][0] == "status"
    assert "正在分析您的偏好" in events[0][1]["content"]

    assert events[1][0] == "status"
    assert "未从当前消息提取到新的偏好信息" in events[1][1]["content"]

    assert events[2][0] == "status"
    assert "槽位不完整" in events[2][1]["content"]

    assert events[3][0] == "status"
    assert "追问 →" in events[3][1]["content"]

    assert events[4][0] == "done"
    assert "您想去哪里旅行呢" in events[4][1]["content"]
    assert events[4][1]["slots_filled"] is False


@pytest.mark.asyncio
async def test_chat_sse_slots_complete_triggers_planning(client, mock_llm):
    """SSE 聊天 → 槽位完整时进入行程规划流水线"""
    from unittest.mock import MagicMock

    slots_r = MagicMock()
    slots_r.content = json.dumps({"destination": "东京", "days": 7, "interests": ["美食"]})
    plan_r = MagicMock()
    plan_r.content = json.dumps(
        {
            "title": "东京美食之旅",
            "days": [
                {
                    "day": 1,
                    "city": "东京",
                    "theme": "美食探索",
                    "activities": [
                        {
                            "name": "筑地市场",
                            "type": "美食",
                            "lat": None,
                            "lng": None,
                            "duration": "2h",
                            "time": "09:00",
                            "notes": "",
                        }
                    ],
                    "transport": {"mode": "步行", "duration": "约20分钟"},
                    "hotel": "银座地区酒店",
                }
            ],
        },
        ensure_ascii=False,
    )
    mock_llm.ainvoke.side_effect = [slots_r, plan_r]

    r = await client.post("/api/session", json={})
    sid = r.json()["id"]

    r = await client.post(
        f"/api/chat/{sid}",
        json={"message": "想去东京7天美食之旅"},
        timeout=10,
    )
    assert r.status_code == 200

    lines = [ln for ln in r.text.strip().split("\n") if ln]
    events = []
    for i in range(0, len(lines), 2):
        event_line = lines[i]
        data_line = lines[i + 1]
        evt_type = event_line.replace("event: ", "")
        payload = json.loads(data_line.replace("data: ", ""))
        events.append((evt_type, payload))

    # 应该包含 plan_generation, enrichment, format_response
    steps_text = " ".join(e[1]["content"] for e in events if e[0] == "status")
    assert "plan_generation" in steps_text
    assert "enrichment" in steps_text
    assert "format_response" in steps_text

    # done 事件应包含 travel_plan
    done_events = [e for e in events if e[0] == "done"]
    assert len(done_events) == 1
    assert done_events[0][1]["travel_plan"] is not None
    assert done_events[0][1]["travel_plan"]["title"] == "东京美食之旅"


@pytest.mark.asyncio
async def test_chat_sse_persists_messages(client, mock_llm):
    """聊天后刷新会话详情 → 应看到 user + assistant 两条消息"""
    mock_llm.ainvoke.return_value.content = "您想去哪里旅行呢？"

    r = await client.post("/api/session", json={})
    sid = r.json()["id"]

    await client.post(f"/api/chat/{sid}", json={"message": "Hello"}, timeout=10)

    r = await client.get(f"/api/session/{sid}")
    data = r.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hello"
    assert data["messages"][1]["role"] == "assistant"
    assert "您想去哪里旅行呢" in data["messages"][1]["content"]


@pytest.mark.asyncio
async def test_chat_nonexistent_session_returns_error(client):
    """向不存在的会话发消息 → SSE error 事件"""
    r = await client.post(
        "/api/chat/00000000-0000-0000-0000-000000000000",
        json={"message": "Hello"},
        timeout=10,
    )
    assert r.status_code == 200  # SSE 连接本身成功
    assert "event: error" in r.text
    payload = json.loads(r.text.split("\n")[1].replace("data: ", ""))
    assert "会话不存在" in payload["content"]


@pytest.mark.asyncio
async def test_chat_empty_message_rejected(client):
    """空消息 → 422 校验失败"""
    r = await client.post("/api/session", json={})
    sid = r.json()["id"]

    r = await client.post(f"/api/chat/{sid}", json={"message": ""})
    assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Agent 图结构
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_agent_graph_nodes_execute_in_order(mock_llm):
    """槽位完整时 → 4 个节点按序执行"""
    from unittest.mock import MagicMock

    from langchain_core.messages import HumanMessage

    from app.agent.graph import build_agent_graph

    slots_r = MagicMock()
    slots_r.content = json.dumps({})
    plan_r = MagicMock()
    plan_r.content = json.dumps(
        {
            "title": "东京美食之旅",
            "days": [
                {
                    "day": 1,
                    "city": "东京",
                    "theme": "美食",
                    "activities": [
                        {
                            "name": "筑地市场",
                            "type": "美食",
                            "lat": None,
                            "lng": None,
                            "duration": "2h",
                            "time": "09:00",
                            "notes": "",
                        }
                    ],
                    "transport": {"mode": "步行", "duration": "约20分钟"},
                    "hotel": "银座酒店",
                }
            ],
        },
        ensure_ascii=False,
    )
    mock_llm.ainvoke.side_effect = [slots_r, plan_r]

    graph = build_agent_graph()
    state = {
        "messages": [HumanMessage(content="测试")],
        "slots": {"destination": "东京", "days": 7, "interests": ["美食"]},
        "travel_plan": None,
        "intermediate_steps": [],
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "",
        "slots_filled": False,
        "missing_slots": [],
        "follow_up_question": "",
    }

    result = await graph.ainvoke(state)
    steps = result["intermediate_steps"]

    assert any("intent_analysis" in s for s in steps)
    assert any("plan_generation" in s for s in steps)
    assert any("enrichment" in s for s in steps)
    assert any("format_response" in s for s in steps)
    assert result["slots_filled"] is True
    assert result["travel_plan"] is not None


@pytest.mark.asyncio
async def test_agent_graph_stops_when_slots_incomplete(mock_llm):
    """槽位不完整时 → 图在 intent_analysis 之后终止"""
    from langchain_core.messages import HumanMessage

    from app.agent.graph import build_agent_graph

    mock_llm.ainvoke.return_value.content = "您想去哪里？"

    graph = build_agent_graph()
    state = {
        "messages": [HumanMessage(content="你好")],
        "slots": {},
        "travel_plan": None,
        "intermediate_steps": [],
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "",
        "slots_filled": False,
        "missing_slots": [],
        "follow_up_question": "",
    }

    result = await graph.ainvoke(state)
    steps = result["intermediate_steps"]

    assert result["slots_filled"] is False
    assert not any("plan_generation" in s for s in steps)
    assert "follow_up_question" in result


@pytest.mark.asyncio
async def test_agent_graph_preserves_slots(mock_llm):
    """Agent 图执行后 → 原有 slots 不丢失，energy_level 被补全"""
    from unittest.mock import MagicMock

    from langchain_core.messages import HumanMessage

    from app.agent.graph import build_agent_graph

    slots_r = MagicMock()
    slots_r.content = json.dumps({})
    plan_r = MagicMock()
    plan_r.content = json.dumps(
        {
            "title": "Tokyo Trip",
            "days": [
                {
                    "day": 1,
                    "city": "Tokyo",
                    "theme": "History",
                    "activities": [
                        {
                            "name": "Asakusa",
                            "type": "景点",
                            "lat": None,
                            "lng": None,
                            "duration": "1h",
                            "time": "09:00",
                            "notes": "",
                        }
                    ],
                    "transport": {"mode": "walk", "duration": "20min"},
                    "hotel": "Tokyo Hotel",
                }
            ],
        },
        ensure_ascii=False,
    )
    mock_llm.ainvoke.side_effect = [slots_r, plan_r]

    graph = build_agent_graph()
    state = {
        "messages": [HumanMessage(content="test")],
        "slots": {"destination": "Tokyo", "days": 5, "interests": ["history"]},
        "travel_plan": None,
        "intermediate_steps": [],
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "",
        "slots_filled": False,
        "missing_slots": [],
        "follow_up_question": "",
    }

    result = await graph.ainvoke(state)
    assert result["slots"]["destination"] == "Tokyo"
    assert result["slots"]["days"] == 5
    assert result["slots"]["interests"] == ["history"]
    assert result["slots"]["energy_level"] == "适中"
    assert len(result["messages"]) == 1
