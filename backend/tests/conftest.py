import os

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
