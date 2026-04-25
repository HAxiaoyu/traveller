import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════
# geocode 单元测试
# ═══════════════════════════════════════════════════════════════


class _FakeAsyncClient:
    def __init__(self, get_return=None, get_side_effect=None):
        self.get = AsyncMock(return_value=get_return, side_effect=get_side_effect)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_geocode_returns_coordinates():
    from app.agent.enrichment.geocoding import geocode

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"geometry": {"location": {"lat": 35.6895, "lng": 139.6917}}}
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient", return_value=_FakeAsyncClient(mock_response)):
        result = await geocode("浅草寺", "东京", "test-key")

    assert result == {"lat": 35.6895, "lng": 139.6917}


@pytest.mark.asyncio
async def test_geocode_empty_results():
    from app.agent.enrichment.geocoding import geocode

    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient", return_value=_FakeAsyncClient(mock_response)):
        result = await geocode("不存在的地址", "未知城市", "test-key")

    assert result is None


@pytest.mark.asyncio
async def test_geocode_no_api_key():
    from app.agent.enrichment.geocoding import geocode

    result = await geocode("浅草寺", "东京", "")
    assert result is None


@pytest.mark.asyncio
async def test_geocode_http_error():
    from app.agent.enrichment.geocoding import geocode

    with patch(
        "httpx.AsyncClient",
        return_value=_FakeAsyncClient(get_side_effect=Exception("网络错误")),
    ):
        result = await geocode("浅草寺", "东京", "test-key")

    assert result is None


# ═══════════════════════════════════════════════════════════════
# weather 单元测试
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_weather_returns_data():
    from app.agent.enrichment.weather import get_weather

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "weather": [{"description": "晴"}],
        "main": {"temp": 22.5, "temp_min": 18.0, "temp_max": 26.0, "humidity": 55},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient", return_value=_FakeAsyncClient(mock_response)):
        result = await get_weather(35.6895, 139.6917, "test-key")

    assert result == {
        "description": "晴",
        "temp": 22,
        "temp_min": 18,
        "temp_max": 26,
        "humidity": 55,
    }


@pytest.mark.asyncio
async def test_weather_no_api_key():
    from app.agent.enrichment.weather import get_weather

    result = await get_weather(35.6895, 139.6917, "")
    assert result is None


@pytest.mark.asyncio
async def test_weather_http_error():
    from app.agent.enrichment.weather import get_weather

    with patch(
        "httpx.AsyncClient",
        return_value=_FakeAsyncClient(get_side_effect=Exception("网络错误")),
    ):
        result = await get_weather(35.6895, 139.6917, "test-key")

    assert result is None


# ═══════════════════════════════════════════════════════════════
# enrich 节点测试
# ═══════════════════════════════════════════════════════════════


def make_state(travel_plan=None, intermediate_steps=None, maps_key="", weather_key=""):
    return {
        "messages": [],
        "slots": {},
        "travel_plan": travel_plan,
        "intermediate_steps": intermediate_steps or [],
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "",
        "google_maps_key": maps_key,
        "weather_api_key": weather_key,
        "slots_filled": True,
        "missing_slots": [],
        "follow_up_question": "",
        "formatted_response": "",
    }


PLAN_WITH_NULL_COORDS = {
    "title": "东京之旅",
    "days": [
        {
            "day": 1,
            "city": "东京",
            "theme": "探索",
            "activities": [
                {
                    "name": "浅草寺",
                    "type": "景点",
                    "lat": None,
                    "lng": None,
                    "duration": "1.5h",
                    "time": "09:00",
                    "notes": "",
                },
                {
                    "name": "秋叶原",
                    "type": "购物",
                    "lat": None,
                    "lng": None,
                    "duration": "2h",
                    "time": "14:00",
                    "notes": "",
                },
            ],
            "transport": {"mode": "地铁", "duration": "约30分钟"},
            "hotel": "东京站酒店",
        }
    ],
}


@pytest.mark.asyncio
async def test_enrich_fills_coordinates_and_weather(mock_enrichment):
    from app.agent.enrichment.enrich import enrich

    state = make_state(
        travel_plan=PLAN_WITH_NULL_COORDS,
        maps_key="maps-key",
        weather_key="weather-key",
    )
    result = await enrich(state)

    plan = result["travel_plan"]
    day0 = plan["days"][0]
    # 坐标已补全
    assert day0["activities"][0]["lat"] is not None
    assert day0["activities"][0]["lng"] is not None
    # 天气已添加
    assert "weather" in day0
    assert day0["weather"]["description"] == "晴"


@pytest.mark.asyncio
async def test_enrich_skips_when_no_travel_plan(mock_enrichment):
    from app.agent.enrichment.enrich import enrich

    state = make_state(travel_plan=None, maps_key="maps-key")
    result = await enrich(state)

    assert "无行程数据" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_enrich_skips_when_no_api_keys(mock_enrichment):
    from app.agent.enrichment.enrich import enrich

    state = make_state(travel_plan=PLAN_WITH_NULL_COORDS, maps_key="", weather_key="")
    result = await enrich(state)

    assert "未配置 API Key" in result["intermediate_steps"][-1]


@pytest.mark.asyncio
async def test_enrich_immutability(mock_enrichment):
    from app.agent.enrichment.enrich import enrich

    original_plan = json.loads(json.dumps(PLAN_WITH_NULL_COORDS))
    original_steps = ["before"]
    state = make_state(
        travel_plan=original_plan,
        intermediate_steps=original_steps,
        maps_key="maps-key",
        weather_key="weather-key",
    )
    await enrich(state)

    assert state["intermediate_steps"] == ["before"]
    assert state["travel_plan"]["days"][0]["activities"][0]["lat"] is None


@pytest.mark.asyncio
async def test_enrich_handles_partial_coords(mock_enrichment):
    from app.agent.enrichment.enrich import enrich

    plan = json.loads(json.dumps(PLAN_WITH_NULL_COORDS))
    plan["days"][0]["activities"][0]["lat"] = 35.0
    plan["days"][0]["activities"][0]["lng"] = 135.0
    # Only the second activity needs geocoding, but weather still runs

    state = make_state(
        travel_plan=plan,
        maps_key="maps-key",
        weather_key="weather-key",
    )
    result = await enrich(state)

    day0 = result["travel_plan"]["days"][0]
    assert day0["activities"][0]["lat"] == 35.0
    assert day0["activities"][1]["lat"] is not None
    assert "weather" in day0
