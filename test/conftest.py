import os
from collections.abc import AsyncGenerator

os.environ["POSTGRES_DB"] = "test_crag_db"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from database import Base, get_db
from config import setting
from main import app

TEST_PASSWORD = "123456789"

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
def db_engine():
    engine = create_async_engine(setting.database_url, poolclass=NullPool)
    return engine

@pytest.fixture(scope="session")
async def setup_database(db_engine):
    async with db_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await db_engine.dispose()

@pytest.fixture
async def db_session(db_engine, setup_database):
    conn = await db_engine.connect()
    trans = await conn.begin()

    session_factory = async_sessionmaker(bind=conn, class_=AsyncSession, expire_on_commit=False, join_transaction_mode="create_savepoint")

    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
            await conn.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

async def create_test_user(client:AsyncClient, username:str = "charlie", email:str = "example@g.com", password:str = TEST_PASSWORD):
    response = await client.post("/api/users", json={
        "username" : username,
        "email" : email,
        "password" : password
    })
    assert response.status_code == 201, f"Failed to create user: {response.text}"

async def login_test_user(client:AsyncClient, email:str = "example@g.com", password:str = TEST_PASSWORD):
    response = await client.post("/api/users/token", data={"username":email, "password":password})
    assert response.status_code == 200, f"Wrong username or password: {response.text}"
    return response.json()["access_token"]




def bearer_header(token):
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def user_data():
    return {"username":"charlie", "email":"charlie@example.com", "password":TEST_PASSWORD}

@pytest.fixture
def query_data():
    return {"query":"hello"}

@pytest.fixture
def mocked_crag(monkeypatch):
    monkeypatch.setattr("router.query.capped_main", lambda q: "fake answer")

@pytest.fixture
async def auth_headers(user_data, client: AsyncClient):
    await create_test_user(client, username=user_data["username"], email=user_data["email"], password=user_data["password"])
    token = await login_test_user(client, email=user_data["email"], password=user_data["password"])
    return bearer_header(token)