import json
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from trade_calendar import translations
from trade_calendar.core.config import Settings
from trade_calendar.languages import display_text, needs_translation, translation_key
from trade_calendar.models.domain import DatePrecision, Event, TextTranslation
from trade_calendar.preferences import persist_web_settings
from trade_calendar.schemas.events import EventSourceRead
from trade_calendar.schemas.settings import WebSettings


@pytest.fixture(autouse=True)
def agnes_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(agnes_api_key=SecretStr("sk-test-only"), agnes_model="agnes-2.5-flash")
    monkeypatch.setattr(translations, "get_settings", lambda: settings)


def test_legacy_mixed_titles_do_not_leak_through_fallbacks() -> None:
    assert needs_translation("韩国统计发布：소비자물가동향")
    assert needs_translation("ㅎㅏㄴ")
    assert display_text("소비자물가", {}, "韩国统计发布：소비자물가") == "翻译中"
    assert display_text("소비자물가", {}, "韩国消费者价格") == "韩国消费者价格"
    assert display_text("Consumer Price Index", {}) == "Consumer Price Index"


def test_quarter_notation_can_be_localized_without_changing_the_reporting_period() -> None:
    expected = translations.reference_numbers("2025년 4/4분기 생활인구 산정 결과")
    assert translations.reference_numbers("2025年第四季度生活人口估算结果") == expected
    assert translations.reference_numbers("2025年第4季度生活人口估算结果") == expected
    assert translations.reference_numbers("2025年第3季度生活人口估算结果") != expected
    assert translations.reference_numbers("2026年第4季度生活人口估算结果") != expected


@pytest.mark.parametrize("result", [
    {"translations": []},
    {"translations": ["아직 한국어"]},
    {"translations": ["2027年消费者物价指数"]},
])
async def test_invalid_translations_are_rejected(result: dict[str, list[str]]) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(
        200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(result, ensure_ascii=False),
        }}]},
    ))) as client:
        with pytest.raises(translations.TranslationError):
            await translations.translate_batch(["2026 소비자물가동향"], client)


async def seed_public_event(session: AsyncSession) -> Event:
    event = Event(
        canonical_key=str(uuid4()), title_original="2026 소비자물가동향",
        title_zh="韩国统计发布：2026 소비자물가동향", normalized_title="original",
        institution="Korea Statistics", country_code="KR", category="macro_release",
        event_type="inflation", date_precision=DatePrecision.DATE,
        local_date=date(2026, 9, 7), is_manual=False, notes="비공개 개인 메모",
    )
    session.add(event)
    await session.commit()
    return event


async def test_backfill_is_cached_excludes_notes_and_preserves_source(
    session_factory: async_sessionmaker[AsyncSession], client: httpx.AsyncClient,
) -> None:
    async with session_factory() as session:
        event = await seed_public_event(session)
        event_id = event.id
        await persist_web_settings(session, WebSettings(auto_translation="auto"))
        assert await translations.enqueue_calendar_translations(session) == 2
        assert await translations.enqueue_calendar_translations(session) == 0

    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        payload = json.loads(request.content)
        texts = json.loads(payload["messages"][1]["content"])["texts"]
        assert all("메모" not in text for text in texts)
        assert payload["model"] == "agnes-2.5-flash"
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"translations": ["2026年消费者物价指数"] * len(texts)}),
        }}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as agnes:
        assert await translations.process_translation_batch(session_factory, client=agnes) == {
            "translated": 2, "failed": 0,
        }
        assert await translations.process_translation_batch(session_factory, client=agnes) == {
            "translated": 0, "failed": 0,
        }
    assert len(calls) == 1

    detail = (await client.get(f"/api/v1/events/{event_id}")).json()
    assert detail["display_title"] == "2026年消费者物价指数"
    assert detail["title_original"] == "2026 소비자물가동향"
    assert "translations" not in detail
    items = (await client.get("/api/v1/events")).json()["items"]
    assert items[0]["display_title"] == detail["display_title"]
    async with session_factory() as session:
        persisted = await session.get(Event, UUID(str(event_id)))
        assert persisted and persisted.current_version == 1
        assert persisted.title_zh == "韩国统计发布：2026 소비자물가동향"
        source = EventSourceRead(
            source_id=uuid4(), source_key="korea", source_name="Official schedule",
            institution="Korea Statistics", official_url="https://example.com",
            source_event_id="old-id", source_title=persisted.title_original,
            is_primary=True, last_verified_at=None,
        )
        rendered = (await translations.attach_translations(session, [source]))[0]
        assert rendered.display_title == detail["display_title"]


async def test_rate_limit_defers_retry_without_exposing_provider_body(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await persist_web_settings(session, WebSettings(auto_translation="auto"))
        session.add(TextTranslation(text_hash=translation_key("한국"), source_text="한국"))
        await session.commit()
    requests: list[httpx.Request] = []

    def reject(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(429, text="provider response with confidential details")

    async with httpx.AsyncClient(transport=httpx.MockTransport(reject)) as agnes:
        assert (await translations.process_translation_batch(session_factory, client=agnes))[
            "failed"
        ] == 1
        await translations.process_translation_batch(session_factory, client=agnes)
    assert len(requests) == 1
    async with session_factory() as session:
        row = await session.scalar(select(TextTranslation))
        assert row and row.status == "failed" and row.translated_text is None
        assert row.last_error == "agnes_http_429"
        assert row.next_attempt_at and row.next_attempt_at.replace(tzinfo=UTC) > datetime.now(UTC)


async def test_manual_events_are_not_queued(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        event = await seed_public_event(session)
        event.is_manual = True
        await session.commit()
        assert await translations.enqueue_calendar_translations(session) == 0
