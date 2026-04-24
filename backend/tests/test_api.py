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
async def test_chat_sse_streams_all_events(client):
    """SSE 聊天 → 应输出 6 个事件：1 条初始 status + 4 条节点 status + 1 条 done"""
    r = await client.post("/api/session", json={})
    sid = r.json()["id"]

    r = await client.post(
        f"/api/chat/{sid}",
        json={"message": "想去日本7天"},
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

    assert len(events) == 6, f"期望 6 个事件，实际 {len(events)}"

    # 事件类型序列
    assert events[0][0] == "status"
    assert "正在分析您的偏好" in events[0][1]["content"]

    assert events[1][0] == "status"
    assert "intent_analysis" in events[1][1]["content"]

    assert events[2][0] == "status"
    assert "plan_generation" in events[2][1]["content"]

    assert events[3][0] == "status"
    assert "enrichment" in events[3][1]["content"]

    assert events[4][0] == "status"
    assert "format_response" in events[4][1]["content"]

    assert events[5][0] == "done"
    assert "收到您的消息" in events[5][1]["content"]


@pytest.mark.asyncio
async def test_chat_sse_persists_messages(client):
    """聊天后刷新会话详情 → 应看到 user + assistant 两条消息"""
    r = await client.post("/api/session", json={})
    sid = r.json()["id"]

    await client.post(f"/api/chat/{sid}", json={"message": "Hello"}, timeout=10)

    r = await client.get(f"/api/session/{sid}")
    data = r.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hello"
    assert data["messages"][1]["role"] == "assistant"
    assert "Agent 流水线已就绪" in data["messages"][1]["content"]


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
async def test_agent_graph_nodes_execute_in_order():
    """直接调用 Agent 图 → 验证 4 个节点按序执行"""
    from langchain_core.messages import HumanMessage

    from app.agent.graph import build_agent_graph

    graph = build_agent_graph()
    state = {
        "messages": [HumanMessage(content="测试")],
        "slots": {},
        "travel_plan": None,
        "intermediate_steps": [],
    }

    result = await graph.ainvoke(state)
    steps = result["intermediate_steps"]

    assert len(steps) == 4
    assert steps[0].startswith("intent_analysis:")
    assert steps[1].startswith("plan_generation:")
    assert steps[2].startswith("enrichment:")
    assert steps[3].startswith("format_response:")


@pytest.mark.asyncio
async def test_agent_graph_preserves_state():
    """Agent 图执行后 → 原始 state 字段不丢失"""
    from langchain_core.messages import HumanMessage

    from app.agent.graph import build_agent_graph

    graph = build_agent_graph()
    state = {
        "messages": [HumanMessage(content="test")],
        "slots": {"destination": "Tokyo"},
        "travel_plan": None,
        "intermediate_steps": [],
    }

    result = await graph.ainvoke(state)
    assert result["slots"] == {"destination": "Tokyo"}
    assert result["travel_plan"] is None
    assert len(result["messages"]) == 1
