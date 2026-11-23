import pytest
from httpx import AsyncClient

from test.conftest import TEST_PASSWORD, create_test_user

@pytest.mark.anyio
async def test_unknown_route_returns_404(client: AsyncClient):
    response = await client.get("/not-found")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_create_user(user_data, client: AsyncClient):
    response = await client.post("/api/users", json=user_data)
    assert response.status_code == 201, f"{response.text}"
    assert response.json()["username"] == user_data["username"]
    assert response.json()["email"] == user_data["email"]


@pytest.mark.anyio
async def test_get_all_users(client: AsyncClient, user_data):
    await create_test_user(client, username=user_data["username"], email=user_data["email"], password=user_data["password"])
    response = await client.get("/api/users")
    assert response.status_code == 200
    assert response.json()[0]["username"] == user_data["username"]


@pytest.mark.anyio
async def test_get_user_queries(client: AsyncClient, query_data, user_data, mocked_crag, auth_headers):
    create_response = await client.post("/api/queries", json=query_data, headers=auth_headers)
    list_response = await client.get(f"/api/users/{user_data['username']}/queries", headers=auth_headers)
    assert create_response.status_code == 201, create_response.text
    assert list_response.status_code == 200
    assert list_response.json()[0]["query"] == query_data["query"]
    assert list_response.json()[0]["response"] == "fake answer"


@pytest.mark.anyio
async def test_get_other_users_queries_returns_403(client: AsyncClient, auth_headers):
    await create_test_user(client, username="bob", email="bob@example.com", password=TEST_PASSWORD)
    response = await client.get("/api/users/bob/queries", headers=auth_headers)
    assert response.status_code == 403