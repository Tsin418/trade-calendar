from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True, slots=True)
class WatchedCompany:
    key: str
    ticker: str
    market: str
    name_zh: str
    name_en: str
    finnhub_symbol: str | None
    longbridge_symbol: str | None
    source_names: tuple[str, ...]
    ir_url: str | None


def load_company_watchlist(config_dir: Path) -> list[WatchedCompany]:
    path = config_dir / "watchlists.yaml"
    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    rows = document.get("companies", [])
    if not isinstance(rows, list):
        raise ValueError("watchlists.yaml companies must be a list")

    companies: list[WatchedCompany] = []
    keys: set[str] = set()
    listings: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or not row.get("enabled", True):
            continue
        key = str(row.get("id") or "").strip()
        ticker = str(row.get("ticker") or "").strip().upper()
        market = str(row.get("market") or "").strip().upper()
        name_zh = str(row.get("name_zh") or "").strip()
        name_en = str(row.get("name_en") or name_zh).strip()
        if not all((key, ticker, market, name_zh, name_en)):
            raise ValueError("each enabled watchlist company needs id, ticker, market and names")
        if key in keys or (market, ticker) in listings:
            raise ValueError(f"duplicate watchlist company: {key} / {market}:{ticker}")
        keys.add(key)
        listings.add((market, ticker))
        aliases = tuple(
            dict.fromkeys(
                [
                    name_zh,
                    name_en,
                    *(str(value).strip() for value in row.get("source_names", [])),
                ]
            )
        )
        companies.append(WatchedCompany(
            key=key,
            ticker=ticker,
            market=market,
            name_zh=name_zh,
            name_en=name_en,
            finnhub_symbol=_optional_text(row.get("finnhub_symbol")),
            longbridge_symbol=_optional_text(row.get("longbridge_symbol")),
            source_names=aliases,
            ir_url=_optional_text(row.get("ir_url")),
        ))
    return companies


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
