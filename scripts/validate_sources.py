"""Fetch and parse registered sources without writing to the database."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from trade_calendar.source_registry import adapter_registry


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="*")
    args = parser.parse_args()
    registry = adapter_registry()
    selected = args.source or list(registry)
    failed = False
    for source_key in selected:
        adapter = registry.get(source_key)
        if adapter is None:
            print(json.dumps({"source": source_key, "error": "adapter_unavailable"}))
            failed = True
            continue
        try:
            payload = await adapter.fetch()
            parsed = adapter.parse(payload)
            normalized = [adapter.normalize(event) for event in parsed]
            health = adapter.health_check(normalized)
            result = {
                "source": source_key,
                "status": "healthy" if health.healthy else "degraded",
                "events": len(normalized),
                "url": payload.url,
                "content_type": payload.content_type,
                "warnings": health.warnings,
            }
        except Exception as exc:  # noqa: BLE001 - report each adapter and continue the sweep
            failed = True
            result = {
                "source": source_key,
                "status": "failed",
                "error_type": getattr(exc, "code", type(exc).__name__),
                "error": str(exc),
            }
        print(json.dumps(result, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
