import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["TRAVELLER_DATABASE_URL"] = "sqlite+aiosqlite:///./test_traveller.db"

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import Base, async_session, engine, init_db
from app.main import app


@pytest.fixture
async def db():
    await init_db()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


SAMPLE_TRAVEL_PLAN = {
    "title": "东京7日美食之旅",
    "days": [
        {
            "day": 1,
            "city": "东京",
            "theme": "浅草·传统美食",
            "activities": [
                {
                    "name": "浅草寺",
                    "type": "景点",
                    "lat": None,
                    "lng": None,
                    "duration": "1.5h",
                    "time": "09:00",
                    "notes": "清晨前往避开人流",
                },
                {
                    "name": "筑地市场",
                    "type": "美食",
                    "lat": None,
                    "lng": None,
                    "duration": "2h",
                    "time": "11:00",
                    "notes": "品尝新鲜寿司",
                },
            ],
            "transport": {"mode": "步行", "duration": "约20分钟"},
            "hotel": "浅草地区酒店",
        }
    ],
}


@pytest.fixture
def mock_llm():
    fake_model = MagicMock()
    fake_model.ainvoke = AsyncMock()

    with patch(
        "app.agent.intent_analysis.extract_slots.create_chat_model",
        return_value=fake_model,
    ), patch(
        "app.agent.intent_analysis.generate_question.create_chat_model",
        return_value=fake_model,
    ), patch(
        "app.agent.plan_generation.generate.create_chat_model",
        return_value=fake_model,
    ):
        yield fake_model


@pytest.fixture
def mock_plan_llm(mock_llm):
    r = MagicMock()
    r.content = json.dumps(SAMPLE_TRAVEL_PLAN, ensure_ascii=False)
    mock_llm.ainvoke.return_value = r
    return mock_llm
