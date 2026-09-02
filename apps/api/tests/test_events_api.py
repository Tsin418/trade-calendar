from httpx import AsyncClient


async def test_health_has_request_id(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 200
    assert response.json()["request_id"] == "test-request"
    assert response.headers["X-Request-ID"] == "test-request"


async def test_create_event_is_idempotent_and_versioned(
    client: AsyncClient, minute_event_payload: dict[str, object]
) -> None:
    first = await client.post("/api/v1/events", json=minute_event_payload)
    second = await client.post("/api/v1/events", json=minute_event_payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["starts_at"] == "2026-09-16T18:00:00Z"
    assert first.json()["country_code"] == "US"

    versions = await client.get(f"/api/v1/events/{first.json()['id']}/versions")
    assert versions.status_code == 200
    assert [version["version"] for version in versions.json()] == [1]


async def test_date_only_event_never_fabricates_midnight(client: AsyncClient) -> None:
    payload = {
        "title_zh": "台积电财报发布",
        "institution": "TSMC",
        "country_code": "TW",
        "category": "corporate",
        "event_type": "earnings_release",
        "status": "tba",
        "importance": "high",
        "date_precision": "date",
        "local_date": "2026-10-15",
        "original_timezone": "Asia/Taipei",
    }
    response = await client.post("/api/v1/events", json=payload)
    assert response.status_code == 201
    assert response.json()["local_date"] == "2026-10-15"
    assert response.json()["starts_at"] is None

    invalid = dict(payload, starts_at="2026-10-15T00:00:00+08:00")
    invalid["idempotency_key"] = "invalid-midnight"
    error = await client.post("/api/v1/events", json=invalid)
    assert error.status_code == 422
    assert error.json()["error"]["code"] == "validation_error"


async def test_tba_to_specific_time_creates_one_change(client: AsyncClient) -> None:
    create = await client.post(
        "/api/v1/events",
        json={
            "title_zh": "财报说明会",
            "institution": "Example Corp",
            "country_code": "JP",
            "category": "corporate",
            "event_type": "earnings_call",
            "status": "tba",
            "importance": "medium",
            "date_precision": "date",
            "local_date": "2026-09-10",
            "original_timezone": "Asia/Tokyo",
        },
    )
    event_id = create.json()["id"]
    patch = {
        "status": "confirmed",
        "date_precision": "minute",
        "local_date": None,
        "starts_at": "2026-09-10T15:00:00+09:00",
        "original_time_text": "15:00 JST",
    }
    updated = await client.patch(f"/api/v1/events/{event_id}", json=patch)
    repeated = await client.patch(f"/api/v1/events/{event_id}", json=patch)
    assert updated.status_code == 200
    assert repeated.status_code == 200

    versions = (await client.get(f"/api/v1/events/{event_id}/versions")).json()
    changes = (await client.get(f"/api/v1/events/{event_id}/changes")).json()
    assert [item["version"] for item in versions] == [2, 1]
    assert changes[0]["change_type"] == "time_confirmed"


async def test_lock_and_soft_delete_flow(
    client: AsyncClient, minute_event_payload: dict[str, object]
) -> None:
    created = await client.post("/api/v1/events", json=minute_event_payload)
    event_id = created.json()["id"]
    locked = await client.put(
        f"/api/v1/events/{event_id}/locks/title_zh", json={"reason": "人工核验标题"}
    )
    assert locked.status_code == 200
    assert locked.json()["field_name"] == "title_zh"

    deleted = await client.delete(f"/api/v1/events/{event_id}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/events/{event_id}")).status_code == 404

