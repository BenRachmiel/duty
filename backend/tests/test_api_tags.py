import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_tags(client: AsyncClient):
    resp = await client.post("/api/tags", json={"name": "rank:sergeant", "color": "#ff0000"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "rank:sergeant"
    assert data["color"] == "#ff0000"
    assert "id" in data

    resp = await client.get("/api/tags")
    assert resp.status_code == 200
    tags = resp.json()
    assert len(tags) == 1
    assert tags[0]["name"] == "rank:sergeant"


@pytest.mark.asyncio
async def test_create_tag_no_color(client: AsyncClient):
    resp = await client.post("/api/tags", json={"name": "no-color"})
    assert resp.status_code == 201
    assert resp.json()["color"] is None


@pytest.mark.asyncio
async def test_delete_tag(client: AsyncClient):
    resp = await client.post("/api/tags", json={"name": "to-delete"})
    tag_id = resp.json()["id"]

    resp = await client.delete(f"/api/tags/{tag_id}")
    assert resp.status_code == 204

    resp = await client.get("/api/tags")
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_tag_not_found(client: AsyncClient):
    resp = await client.delete("/api/tags/999")
    assert resp.status_code == 404
