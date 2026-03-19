import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_solver_run_empty(client: AsyncClient):
    resp = await client.post("/api/solver/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["proposed"] == []
    assert data["unfilled"] == []
    assert data["duty_points"] == {}


@pytest.mark.asyncio
async def test_solver_run_and_accept(client: AsyncClient):
    # Setup
    person = (await client.post("/api/people", json={"name": "Alice"})).json()
    duty = (await client.post("/api/duties", json={"name": "Guard", "date": "2026-03-20"})).json()

    # Run solver
    resp = await client.post("/api/solver/run")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["proposed"]) == 1
    assert data["proposed"][0]["person"]["id"] == person["id"]
    assert data["proposed"][0]["duty"]["id"] == duty["id"]
    assert person["id"] in [int(k) for k in data["duty_points"]]

    # Accept
    resp = await client.post("/api/solver/accept", json={
        "assignments": [{"person_id": person["id"], "duty_id": duty["id"]}]
    })
    assert resp.status_code == 201
    assert resp.json()["accepted"] == 1

    # Verify assignment was created
    resp = await client.get("/api/assignments")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["is_manual"] is False


@pytest.mark.asyncio
async def test_solver_unfilled_with_exclusion_reasons(client: AsyncClient):
    """Unfilled duties include excluded people with reasons."""
    tag = (await client.post("/api/tags", json={"name": "special"})).json()
    duty = (await client.post("/api/duties", json={"name": "Special Duty", "date": "2026-03-20"})).json()
    await client.post(f"/api/duties/{duty['id']}/tags", json={"id": tag["id"], "name": tag["name"], "color": tag["color"]})

    # Create allow rule: only people with "special" tag can do "special" duties
    await client.post("/api/rules", json={
        "name": "Only special",
        "rule_type": "allow",
        "person_tag_id": tag["id"],
        "duty_tag_id": tag["id"],
    })

    # Create person without the special tag
    person = (await client.post("/api/people", json={"name": "Bob"})).json()

    resp = await client.post("/api/solver/run")
    data = resp.json()
    assert len(data["proposed"]) == 0
    assert len(data["unfilled"]) == 1

    unfilled = data["unfilled"][0]
    assert unfilled["duty"]["name"] == "Special Duty"
    assert unfilled["slots_needed"] == 1
    assert len(unfilled["excluded_people"]) == 1
    assert unfilled["excluded_people"][0]["person"]["name"] == "Bob"
    assert len(unfilled["excluded_people"][0]["reasons"]) == 1
    assert unfilled["excluded_people"][0]["reasons"][0]["rule_type"] == "allow"
    assert unfilled["excluded_people"][0]["reasons"][0]["rule_name"] == "Only special"


@pytest.mark.asyncio
async def test_solver_duty_points(client: AsyncClient):
    """duty_points reflects historical assignment points."""
    person = (await client.post("/api/people", json={"name": "Alice"})).json()

    # Create a past duty with duration_days=3, difficulty=2.0
    duty1 = (await client.post("/api/duties", json={
        "name": "Heavy Duty", "date": "2026-03-10",
        "duration_days": 3, "difficulty": 2.0,
    })).json()

    # Manually assign
    await client.post("/api/assignments", json={"person_id": person["id"], "duty_id": duty1["id"]})

    # Create a future duty to solve
    await client.post("/api/duties", json={"name": "Future Guard", "date": "2026-03-25"})

    resp = await client.post("/api/solver/run")
    data = resp.json()
    points = data["duty_points"]
    assert points[str(person["id"])] == 6.0  # 3 * 2.0


@pytest.mark.asyncio
async def test_solver_count_since(client: AsyncClient):
    """count_since filters which assignments contribute to duty_points."""
    person = (await client.post("/api/people", json={"name": "Alice"})).json()

    old = (await client.post("/api/duties", json={"name": "Old", "date": "2026-01-01", "duration_days": 5})).json()
    recent = (await client.post("/api/duties", json={"name": "Recent", "date": "2026-03-10", "duration_days": 2})).json()

    await client.post("/api/assignments", json={"person_id": person["id"], "duty_id": old["id"]})
    await client.post("/api/assignments", json={"person_id": person["id"], "duty_id": recent["id"]})

    # Create future duty
    await client.post("/api/duties", json={"name": "Future", "date": "2026-03-25"})

    # Without count_since — both count
    resp = await client.post("/api/solver/run")
    data = resp.json()
    assert data["duty_points"][str(person["id"])] == 7.0  # 5 + 2

    # With count_since — only recent counts
    resp = await client.post("/api/solver/run", json={"count_since": "2026-03-01"})
    data = resp.json()
    assert data["duty_points"][str(person["id"])] == 2.0


@pytest.mark.asyncio
async def test_force_accept_excluded_person(client: AsyncClient):
    """Force-accepting an excluded person through /accept works."""
    tag = (await client.post("/api/tags", json={"name": "restricted"})).json()
    duty = (await client.post("/api/duties", json={"name": "Restricted Duty", "date": "2026-03-20"})).json()
    await client.post(f"/api/duties/{duty['id']}/tags", json={"id": tag["id"], "name": tag["name"], "color": tag["color"]})

    await client.post("/api/rules", json={
        "name": "Only restricted",
        "rule_type": "allow",
        "person_tag_id": tag["id"],
        "duty_tag_id": tag["id"],
    })

    person = (await client.post("/api/people", json={"name": "Bob"})).json()

    # Solver won't propose Bob
    resp = await client.post("/api/solver/run")
    data = resp.json()
    assert len(data["proposed"]) == 0

    # Force-accept anyway
    resp = await client.post("/api/solver/accept", json={
        "assignments": [{"person_id": person["id"], "duty_id": duty["id"]}]
    })
    assert resp.status_code == 201
    assert resp.json()["accepted"] == 1

    # Verify it was created
    resp = await client.get("/api/assignments")
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_duty_duration_and_difficulty_in_response(client: AsyncClient):
    """Duty response includes duration_days and difficulty."""
    duty = (await client.post("/api/duties", json={
        "name": "Test", "date": "2026-03-20",
        "duration_days": 3, "difficulty": 1.5,
    })).json()
    assert duty["duration_days"] == 3
    assert duty["difficulty"] == 1.5

    # Update
    resp = await client.put(f"/api/duties/{duty['id']}", json={"difficulty": 2.0})
    assert resp.status_code == 200
    assert resp.json()["difficulty"] == 2.0


@pytest.mark.asyncio
async def test_solver_algorithm_parameter(client: AsyncClient):
    """Solver accepts algorithm and iterations parameters."""
    person = (await client.post("/api/people", json={"name": "Alice"})).json()
    await client.post("/api/duties", json={"name": "Guard", "date": "2026-03-20"})

    for algo in ["greedy", "montecarlo", "annealing"]:
        resp = await client.post("/api/solver/run", json={"algorithm": algo, "iterations": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["proposed"]) == 1
        assert data["proposed"][0]["person"]["id"] == person["id"]
