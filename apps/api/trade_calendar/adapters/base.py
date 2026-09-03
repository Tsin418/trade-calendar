from abc import ABC, abstractmethod

from trade_calendar.adapters.types import AdapterHealth, NormalizedEvent, RawPayload, SourceEvent


class SourceAdapter(ABC):
    source_key: str
    version: str
    allow_empty: bool = False

    @abstractmethod
    async def fetch(self) -> RawPayload:
        """Fetch a source without mutating canonical event tables."""

    @abstractmethod
    def parse(self, payload: RawPayload) -> list[SourceEvent]:
        """Turn an immutable raw payload into source observations."""

    @abstractmethod
    def normalize(self, event: SourceEvent) -> NormalizedEvent:
        """Map one source event into the shared, validated schema."""

    def health_check(self, events: list[NormalizedEvent]) -> AdapterHealth:
        if not events:
            if self.allow_empty:
                return AdapterHealth(
                    healthy=True,
                    event_count=0,
                    completeness=1,
                    warnings=["no matching watchlist events in the current source window"],
                )
            return AdapterHealth(
                healthy=False,
                event_count=0,
                completeness=0,
                warnings=["source returned zero events"],
            )
        complete = sum(
            bool(item.title_original and (item.starts_at or item.local_date)) for item in events
        )
        completeness = complete / len(events)
        return AdapterHealth(
            healthy=completeness >= 0.95,
            event_count=len(events),
            completeness=completeness,
            warnings=[] if completeness >= 0.95 else ["required field completeness below 95%"],
        )
