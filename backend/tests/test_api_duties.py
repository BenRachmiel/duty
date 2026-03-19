import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_crud_duties(client: AsyncClient):
    resp = await client.post("/api/duties", json={"name": "Guard A", "date": "2026-03-20", "headcount": 2})
    assert resp.status_code == 201
    duty = resp.json()
    assert duty["name"] == "Guard A"
    assert duty["headcount"] == 2

    resp = await client.get("/api/duties")
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1

    resp = await client.put(f"/api/duties/{duty['id']}", json={"name": "Guard B"})
    assert resp.json()["name"] == "Guard B"

    resp = await client.delete(f"/api/duties/{duty['id']}")
    assert resp.status_code == 204

    resp = await client.get("/api/duties")
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_duty_date_filter(client: AsyncClient):
    await client.post("/api/duties", json={"name": "D1", "date": "2026-03-18"})
    await client.post("/api/duties", json={"name": "D2", "date": "2026-03-25"})

    resp = await client.get("/api/duties", params={"date_from": "2026-03-20"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "D2"


@pytest.mark.asyncio
async def test_duty_tags(client: AsyncClient):
    tag_resp = await client.post("/api/tags", json={"name": "night"})
    tag = tag_resp.json()

    duty_resp = await client.post("/api/duties", json={"name": "Night Watch", "date": "2026-03-20"})
    duty = duty_resp.json()

    resp = await client.post(
        f"/api/duties/{duty['id']}/tags",
        json={"id": tag["id"], "name": tag["name"], "color": tag["color"]},
    )
    assert len(resp.json()["tags"]) == 1

    resp = await client.delete(f"/api/duties/{duty['id']}/tags/{tag['id']}")
    assert len(resp.json()["tags"]) == 0


@pytest.mark.asyncio
async def test_duty_not_found(client: AsyncClient):
    resp = await client.put("/api/duties/999", json={"name": "Ghost"})
    assert resp.status_code == 404
    resp = await client.delete("/api/duties/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_duties_pagination(client: AsyncClient):
    for i in range(5):
        await client.post("/api/duties", json={"name": f"Duty {i}", "date": "2026-03-20"})

    resp = await client.get("/api/duties", params={"limit": 2, "offset": 0})
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_duties_search(client: AsyncClient):
    await client.post("/api/duties", json={"name": "Night Watch", "date": "2026-03-20"})
    await client.post("/api/duties", json={"name": "Gate Guard", "date": "2026-03-20"})

    resp = await client.get("/api/duties", params={"q": "night"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Night Watch"
