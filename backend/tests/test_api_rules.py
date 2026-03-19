import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_crud_rules(client: AsyncClient):
    tag_resp = await client.post("/api/tags", json={"name": "night"})
    tag = tag_resp.json()

    resp = await client.post("/api/rules", json={
        "name": "No nights",
        "rule_type": "deny",
        "person_tag_id": tag["id"],
        "duty_tag_id": tag["id"],
    })
    assert resp.status_code == 201
    rule = resp.json()
    assert rule["name"] == "No nights"
    assert rule["rule_type"] == "deny"
    assert rule["person_tag"]["id"] == tag["id"]

    resp = await client.get("/api/rules")
    assert len(resp.json()) == 1

    resp = await client.put(f"/api/rules/{rule['id']}", json={"name": "Updated"})
    assert resp.json()["name"] == "Updated"

    resp = await client.delete(f"/api/rules/{rule['id']}")
    assert resp.status_code == 204

    resp = await client.get("/api/rules")
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_cooldown_rule(client: AsyncClient):
    t1 = (await client.post("/api/tags", json={"name": "weekend"})).json()
    t2 = (await client.post("/api/tags", json={"name": "holiday"})).json()

    resp = await client.post("/api/rules", json={
        "name": "Weekend cooldown",
        "rule_type": "cooldown",
        "duty_tag_id": t1["id"],
        "cooldown_days": 7,
        "cooldown_duty_tag_id": t2["id"],
    })
    assert resp.status_code == 201
    rule = resp.json()
    assert rule["cooldown_days"] == 7
    assert rule["cooldown_duty_tag"]["id"] == t2["id"]


@pytest.mark.asyncio
async def test_rule_not_found(client: AsyncClient):
    resp = await client.put("/api/rules/999", json={"name": "Ghost"})
    assert resp.status_code == 404
    resp = await client.delete("/api/rules/999")
    assert resp.status_code == 404
