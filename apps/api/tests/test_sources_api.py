from httpx import AsyncClient


async def test_sources_include_complete_metadata_and_all_available_adapters(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/sources")
    assert response.status_code == 200
    sources = {item["key"]: item for item in response.json()}

    for key in (
        "korea_statistics_calendar",
        "hk_censtatd_schedule",
        "longbridge_earnings",
    ):
        assert sources[key]["enabled"] is True
        assert sources[key]["adapter_available"] is True
        assert sources[key]["categories"]
        assert sources[key]["role"] in {"primary", "secondary"}
        assert sources[key]["terms"]
        assert sources[key]["fallback"]
        assert sources[key]["stale_after_hours"] > 0

    if "manual" in sources:
        assert sources["manual"]["is_internal"] is True
        assert sources["manual"]["adapter_available"] is False
