import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_crud_assignments(client: AsyncClient):
    person = (await client.post("/api/people", json={"name": "Alice"})).json()
    duty = (await client.post("/api/duties", json={"name": "Guard", "date": "2026-03-20"})).json()

    resp = await client.post("/api/assignments", json={"person_id": person["id"], "duty_id": duty["id"]})
    assert resp.status_code == 201
    assignment = resp.json()
    assert assignment["is_manual"] is True
    assert assignment["person"]["name"] == "Alice"
    assert assignment["duty"]["name"] == "Guard"

    resp = await client.get("/api/assignments")
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1

    resp = await client.delete(f"/api/assignments/{assignment['id']}")
    assert resp.status_code == 204

    resp = await client.get("/api/assignments")
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_assignment_date_filter(client: AsyncClient):
    p = (await client.post("/api/people", json={"name": "Bob"})).json()
    d1 = (await client.post("/api/duties", json={"name": "D1", "date": "2026-03-18"})).json()
    d2 = (await client.post("/api/duties", json={"name": "D2", "date": "2026-03-25"})).json()

    await client.post("/api/assignments", json={"person_id": p["id"], "duty_id": d1["id"]})
    await client.post("/api/assignments", json={"person_id": p["id"], "duty_id": d2["id"]})

    resp = await client.get("/api/assignments", params={"date_from": "2026-03-20"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["duty"]["name"] == "D2"


@pytest.mark.asyncio
async def test_assignment_not_found(client: AsyncClient):
    resp = await client.delete("/api/assignments/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_assignments_pagination(client: AsyncClient):
    p = (await client.post("/api/people", json={"name": "Alice"})).json()
    for i in range(5):
        d = (await client.post("/api/duties", json={"name": f"D{i}", "date": f"2026-03-{20+i}"})).json()
        await client.post("/api/assignments", json={"person_id": p["id"], "duty_id": d["id"]})

    resp = await client.get("/api/assignments", params={"limit": 2, "offset": 0})
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
