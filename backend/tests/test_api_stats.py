import pytest
from httpx import AsyncClient


async def _seed(client: AsyncClient):
    """Create people, duties, assignments for stats tests."""
    p1 = (await client.post("/api/people", json={"name": "Alice"})).json()
    p2 = (await client.post("/api/people", json={"name": "Bob"})).json()
    p3 = (await client.post("/api/people", json={"name": "Carol"})).json()

    d1 = (await client.post("/api/duties", json={
        "name": "Guard", "date": "2026-03-01", "headcount": 2, "duration_days": 2, "difficulty": 1.5,
    })).json()
    d2 = (await client.post("/api/duties", json={
        "name": "Patrol", "date": "2026-03-10", "headcount": 1, "duration_days": 1, "difficulty": 2.0,
    })).json()

    # Alice and Bob on Guard, Alice on Patrol
    await client.post("/api/assignments", json={"person_id": p1["id"], "duty_id": d1["id"]})
    await client.post("/api/assignments", json={"person_id": p2["id"], "duty_id": d1["id"]})
    await client.post("/api/assignments", json={"person_id": p1["id"], "duty_id": d2["id"]})

    return {"people": [p1, p2, p3], "duties": [d1, d2]}


@pytest.mark.asyncio
async def test_stats_empty(client: AsyncClient):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_points"] == 0.0
    assert data["fill_rate"] == 0.0
    assert data["active_personnel"] == 0
    assert data["total_personnel"] == 0
    assert data["upcoming_unfilled"] == 0
    assert data["points_distribution"] == []
    assert data["daily_workload"] == []
    assert data["top_loaded"] == []  # deprecated, always empty
    assert data["bottom_loaded"] == []  # deprecated, always empty


@pytest.mark.asyncio
async def test_stats_populated(client: AsyncClient):
    await _seed(client)
    resp = await client.get("/api/stats", params={
        "date_from": "2026-03-01", "date_to": "2026-03-31",
    })
    assert resp.status_code == 200
    data = resp.json()

    # Guard: 2*1.5=3.0 pts, Patrol: 1*2.0=2.0 pts
    # Alice: 3.0+2.0=5.0, Bob: 3.0
    assert data["total_points"] == 8.0
    assert data["active_personnel"] == 2
    assert data["total_personnel"] == 3

    # 3 assignments / (2+1)=3 slots = 1.0
    assert data["fill_rate"] == 1.0

    assert len(data["points_distribution"]) > 0
    assert len(data["daily_workload"]) > 0


@pytest.mark.asyncio
async def test_stats_date_filter(client: AsyncClient):
    await _seed(client)
    # Only include Patrol (2026-03-10)
    resp = await client.get("/api/stats", params={
        "date_from": "2026-03-05", "date_to": "2026-03-15",
    })
    data = resp.json()

    # Only Alice assigned to Patrol: 2.0 pts
    assert data["total_points"] == 2.0
    assert data["active_personnel"] == 1


@pytest.mark.asyncio
async def test_stats_daily_workload_duration(client: AsyncClient):
    """Guard has duration_days=2, so it should appear on two days."""
    await _seed(client)
    resp = await client.get("/api/stats", params={
        "date_from": "2026-03-01", "date_to": "2026-03-03",
    })
    data = resp.json()
    workload = {w["date"]: w for w in data["daily_workload"]}

    # Guard starts 03-01, duration 2 → active on 03-01 and 03-02
    assert "2026-03-01" in workload
    assert "2026-03-02" in workload
    assert workload["2026-03-01"]["demand"] == 2
    assert workload["2026-03-02"]["demand"] == 2
    # 2 assignments on each day (both Alice and Bob assigned to Guard)
    assert workload["2026-03-01"]["filled"] == 2
    assert workload["2026-03-02"]["filled"] == 2


@pytest.mark.asyncio
async def test_stats_multiday_duty_overlaps_range(client: AsyncClient):
    """A duty starting before date_from but active within the range should be counted."""
    p1 = (await client.post("/api/people", json={"name": "Alice"})).json()
    # Duty starts 03-01, lasts 10 days → active through 03-10
    d1 = (await client.post("/api/duties", json={
        "name": "LongGuard", "date": "2026-03-01", "headcount": 2,
        "duration_days": 10, "difficulty": 2.0,
    })).json()
    await client.post("/api/assignments", json={"person_id": p1["id"], "duty_id": d1["id"]})

    # Query range starts 03-05, after duty start but within its span
    resp = await client.get("/api/stats", params={
        "date_from": "2026-03-05", "date_to": "2026-03-15",
    })
    data = resp.json()

    # Duty should be included: 10 * 2.0 = 20.0 pts
    assert data["total_points"] == 20.0
    assert data["active_personnel"] == 1
    # Daily workload should show days 03-05 through 03-10 (clipped to range)
    workload = {w["date"]: w for w in data["daily_workload"]}
    assert "2026-03-05" in workload
    assert "2026-03-10" in workload
    # Day 03-11 is past the duty span
    assert "2026-03-11" not in workload


@pytest.mark.asyncio
async def test_stats_fill_rate_partial(client: AsyncClient):
    """Duty with headcount=2 but only 1 assignment → fill_rate = 0.5."""
    p1 = (await client.post("/api/people", json={"name": "Solo"})).json()
    d1 = (await client.post("/api/duties", json={
        "name": "BigDuty", "date": "2026-03-15", "headcount": 2,
    })).json()
    await client.post("/api/assignments", json={"person_id": p1["id"], "duty_id": d1["id"]})

    resp = await client.get("/api/stats", params={
        "date_from": "2026-03-01", "date_to": "2026-03-31",
    })
    data = resp.json()
    assert data["fill_rate"] == 0.5
