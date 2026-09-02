from httpx import AsyncClient


async def test_settings_round_trip(client: AsyncClient) -> None:
    initial = await client.get("/api/v1/settings")
    assert initial.status_code == 200
    assert initial.json()["timezone"] == "Asia/Shanghai"

    payload = initial.json()
    payload.update({
        "timezone": "Asia/Tokyo",
        "markets": ["US", "JP", "US"],
        "critical_lead_minutes": [15, 120, 15],
    })
    saved = await client.put("/api/v1/settings", json=payload)
    assert saved.status_code == 200
    assert saved.json()["markets"] == ["US", "JP"]
    assert saved.json()["critical_lead_minutes"] == [120, 15]

    reloaded = await client.get("/api/v1/settings")
    assert reloaded.json() == saved.json()


async def test_settings_reject_invalid_reminder_minutes(client: AsyncClient) -> None:
    payload = (await client.get("/api/v1/settings")).json()
    payload["high_lead_minutes"] = [0]
    response = await client.put("/api/v1/settings", json=payload)
    assert response.status_code == 422
