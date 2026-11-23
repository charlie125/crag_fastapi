import pytest
from httpx import AsyncClient

from test.conftest import TEST_PASSWORD, create_test_user, login_test_user, bearer_header


@pytest.mark.anyio
async def test_get_all_queries_empty(client: AsyncClient):
    response = await client.get("/api/queries")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_create_query(client: AsyncClient, mocked_crag, query_data, user_data, auth_headers):
    response = await client.post("/api/queries", json=query_data, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["response"] == "fake answer"
    assert response.json()["user"]["username"] == user_data["username"]


@pytest.mark.anyio
async def test_delete_query(client: AsyncClient, auth_headers, query_data, user_data, mocked_crag):
    create_response = await client.post("/api/queries", json=query_data, headers=auth_headers)
    assert create_response.status_code == 201
    query_id = create_response.json()["id"]

    list_before = await client.get(f"/api/users/{user_data['username']}/queries", headers=auth_headers)
    assert list_before.status_code == 200
    assert len(list_before.json()) == 1

    delete_response = await client.delete(f"/api/queries/{query_id}", headers=auth_headers)
    assert delete_response.status_code == 204

    list_after = await client.get(f"/api/users/{user_data['username']}/queries", headers=auth_headers)
    assert list_after.status_code == 200
    assert list_after.json() == []


@pytest.mark.anyio
async def test_delete_other_users_query_returns_404(client: AsyncClient, auth_headers, query_data, mocked_crag):
    await create_test_user(client, username="bob", email="bob@example.com", password=TEST_PASSWORD)
    bob_token = await login_test_user(client, email="bob@example.com", password=TEST_PASSWORD)
    bob_headers = bearer_header(bob_token)

    bob_create_response = await client.post("/api/queries", json=query_data, headers=bob_headers)
    assert bob_create_response.status_code == 201
    bob_query_id = bob_create_response.json()["id"]

    delete_response = await client.delete(f"/api/queries/{bob_query_id}", headers=auth_headers)
    assert delete_response.status_code == 404

    bob_list_response = await client.get("/api/users/bob/queries", headers=bob_headers)
    assert bob_list_response.status_code == 200
    assert len(bob_list_response.json()) == 1