import io

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_crud_people(client: AsyncClient):
    # Create
    resp = await client.post("/api/people", json={"name": "Alice", "external_id": "A001"})
    assert resp.status_code == 201
    alice = resp.json()
    assert alice["name"] == "Alice"
    assert alice["external_id"] == "A001"
    assert alice["tags"] == []

    # List
    resp = await client.get("/api/people")
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1

    # Update
    resp = await client.put(f"/api/people/{alice['id']}", json={"name": "Alice B"})
    assert resp.json()["name"] == "Alice B"

    # Delete
    resp = await client.delete(f"/api/people/{alice['id']}")
    assert resp.status_code == 204

    resp = await client.get("/api/people")
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_person_tags(client: AsyncClient):
    tag_resp = await client.post("/api/tags", json={"name": "medic"})
    tag = tag_resp.json()

    person_resp = await client.post("/api/people", json={"name": "Bob"})
    person = person_resp.json()

    # Add tag
    resp = await client.post(
        f"/api/people/{person['id']}/tags",
        json={"id": tag["id"], "name": tag["name"], "color": tag["color"]},
    )
    assert resp.status_code == 200
    assert len(resp.json()["tags"]) == 1

    # Remove tag
    resp = await client.delete(f"/api/people/{person['id']}/tags/{tag['id']}")
    assert len(resp.json()["tags"]) == 0


@pytest.mark.asyncio
async def test_csv_import(client: AsyncClient):
    csv_content = "name,external_id,tags\nAlice,A001,medic\nBob,B002,\n"
    files = {"file": ("people.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = await client.post("/api/people/import", files=files)
    assert resp.status_code == 200
    people = resp.json()
    assert len(people) >= 2


@pytest.mark.asyncio
async def test_person_not_found(client: AsyncClient):
    resp = await client.put("/api/people/999", json={"name": "Ghost"})
    assert resp.status_code == 404
    resp = await client.delete("/api/people/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_people_pagination(client: AsyncClient):
    for i in range(5):
        await client.post("/api/people", json={"name": f"Person {i}"})

    resp = await client.get("/api/people", params={"limit": 2, "offset": 0})
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2

    resp = await client.get("/api/people", params={"limit": 2, "offset": 4})
    data = resp.json()
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_people_search(client: AsyncClient):
    await client.post("/api/people", json={"name": "Alice Smith"})
    await client.post("/api/people", json={"name": "Bob Jones"})

    resp = await client.get("/api/people", params={"q": "alice"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_people_sort_by_points(client: AsyncClient):
    p1 = (await client.post("/api/people", json={"name": "Alice"})).json()
    p2 = (await client.post("/api/people", json={"name": "Bob"})).json()
    d1 = (await client.post("/api/duties", json={"name": "Guard", "date": "2026-03-01", "headcount": 2})).json()
    d2 = (await client.post("/api/duties", json={"name": "Patrol", "date": "2026-03-02", "headcount": 1})).json()
    # Alice gets 2 assignments (2 pts), Bob gets 1 (1 pt)
    await client.post("/api/assignments", json={"person_id": p1["id"], "duty_id": d1["id"]})
    await client.post("/api/assignments", json={"person_id": p1["id"], "duty_id": d2["id"]})
    await client.post("/api/assignments", json={"person_id": p2["id"], "duty_id": d1["id"]})

    # Sort by points descending
    resp = await client.get("/api/people", params={"sort_by": "points_desc"})
    items = resp.json()["items"]
    assert items[0]["name"] == "Alice"
    assert items[1]["name"] == "Bob"

    # Sort by points ascending
    resp = await client.get("/api/people", params={"sort_by": "points_asc"})
    items = resp.json()["items"]
    assert items[0]["name"] == "Bob"
    assert items[1]["name"] == "Alice"
