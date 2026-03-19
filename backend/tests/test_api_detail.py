import pytest
from httpx import AsyncClient


async def _seed(client: AsyncClient):
    """Create tags, people, duties, and assignments for detail/filter tests."""
    t1 = (await client.post("/api/tags", json={"name": "medic", "color": "#00f"})).json()
    t2 = (await client.post("/api/tags", json={"name": "officer", "color": "#f00"})).json()

    p1 = (await client.post("/api/people", json={"name": "Alice"})).json()
    p2 = (await client.post("/api/people", json={"name": "Bob"})).json()

    await client.post(f"/api/people/{p1['id']}/tags", json=t1)
    await client.post(f"/api/people/{p2['id']}/tags", json=t2)

    d1 = (await client.post("/api/duties", json={
        "name": "Guard", "date": "2026-03-01", "headcount": 2, "duration_days": 2, "difficulty": 1.5,
    })).json()
    d2 = (await client.post("/api/duties", json={
        "name": "Patrol", "date": "2026-03-10", "headcount": 1, "duration_days": 1, "difficulty": 1.0,
    })).json()

    await client.post(f"/api/duties/{d1['id']}/tags", json=t1)
    await client.post(f"/api/duties/{d2['id']}/tags", json=t2)

    a1 = (await client.post("/api/assignments", json={"person_id": p1["id"], "duty_id": d1["id"]})).json()
    a2 = (await client.post("/api/assignments", json={"person_id": p2["id"], "duty_id": d1["id"]})).json()

    return {"tags": [t1, t2], "people": [p1, p2], "duties": [d1, d2], "assignments": [a1, a2]}


@pytest.mark.asyncio
async def test_people_tag_filter(client: AsyncClient):
    s = await _seed(client)
    resp = await client.get("/api/people", params={"tag_id": s["tags"][0]["id"]})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_people_points(client: AsyncClient):
    await _seed(client)
    resp = await client.get("/api/people")
    data = resp.json()
    alice = next(i for i in data["items"] if i["name"] == "Alice")
    # Guard: 2 * 1.5 = 3.0 points
    assert alice["points"] == 3.0


@pytest.mark.asyncio
async def test_people_points_count_since(client: AsyncClient):
    await _seed(client)
    # count_since after the Guard duty date — should exclude it
    resp = await client.get("/api/people", params={"count_since": "2026-03-05"})
    data = resp.json()
    alice = next(i for i in data["items"] if i["name"] == "Alice")
    assert alice["points"] == 0.0


@pytest.mark.asyncio
async def test_get_person(client: AsyncClient):
    s = await _seed(client)
    pid = s["people"][0]["id"]
    resp = await client.get(f"/api/people/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Alice"
    assert data["points"] == 3.0


@pytest.mark.asyncio
async def test_get_person_not_found(client: AsyncClient):
    resp = await client.get("/api/people/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_duties_tag_filter(client: AsyncClient):
    s = await _seed(client)
    resp = await client.get("/api/duties", params={"tag_id": s["tags"][1]["id"]})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Patrol"


@pytest.mark.asyncio
async def test_get_duty(client: AsyncClient):
    s = await _seed(client)
    did = s["duties"][0]["id"]
    resp = await client.get(f"/api/duties/{did}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Guard"
    assert data["assignment_count"] == 2


@pytest.mark.asyncio
async def test_get_duty_not_found(client: AsyncClient):
    resp = await client.get("/api/duties/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_assignments_person_filter(client: AsyncClient):
    s = await _seed(client)
    pid = s["people"][0]["id"]
    resp = await client.get("/api/assignments", params={"person_id": pid})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["person"]["name"] == "Alice"


@pytest.mark.asyncio
async def test_assignments_duty_filter(client: AsyncClient):
    s = await _seed(client)
    did = s["duties"][0]["id"]
    resp = await client.get("/api/assignments", params={"duty_id": did})
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_tag_summary(client: AsyncClient):
    s = await _seed(client)
    tid = s["tags"][0]["id"]

    # Create a rule referencing this tag
    await client.post("/api/rules", json={
        "name": "Medic allow", "rule_type": "allow",
        "person_tag_id": tid, "duty_tag_id": tid,
    })

    resp = await client.get(f"/api/tags/{tid}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["people_count"] == 1
    assert data["duties_count"] == 1
    assert len(data["rules"]) == 1
    assert data["rules"][0]["name"] == "Medic allow"


@pytest.mark.asyncio
async def test_tag_summary_not_found(client: AsyncClient):
    resp = await client.get("/api/tags/999/summary")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rules_tag_filter(client: AsyncClient):
    s = await _seed(client)
    tid = s["tags"][0]["id"]
    await client.post("/api/rules", json={
        "name": "R1", "rule_type": "deny", "person_tag_id": tid,
    })
    await client.post("/api/rules", json={
        "name": "R2", "rule_type": "allow", "person_tag_id": s["tags"][1]["id"],
    })

    resp = await client.get("/api/rules", params={"tag_id": tid})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "R1"
