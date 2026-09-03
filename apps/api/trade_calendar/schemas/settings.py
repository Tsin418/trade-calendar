from datetime import time
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MarketCode = Literal["US", "JP", "KR", "CN", "TW", "HK", "GLOBAL"]


def default_markets() -> list[MarketCode]:
    return ["US", "JP", "KR", "CN", "TW", "HK", "GLOBAL"]


class WebSettings(BaseModel):
    timezone: Literal["Asia/Shanghai", "Asia/Tokyo", "America/New_York"] = "Asia/Shanghai"
    language: Literal["zh-CN"] = "zh-CN"
    markets: list[MarketCode] = Field(default_factory=default_markets)
    critical_lead_minutes: list[int] = Field(default_factory=lambda: [120, 60, 15])
    high_lead_minutes: list[int] = Field(default_factory=lambda: [60, 15])
    daily_summary: time = time(7, 30)
    evening_preview: time = time(20, 30)
    snapshot_retention_days: Literal[30, 90, 180] = 90
    auto_translation: Literal["off", "review"] = "off"

    @field_validator("markets")
    @classmethod
    def unique_markets(cls, value: list[MarketCode]) -> list[MarketCode]:
        return list(dict.fromkeys(value))

    @field_validator("critical_lead_minutes", "high_lead_minutes")
    @classmethod
    def valid_lead_minutes(cls, value: list[int]) -> list[int]:
        if not value or any(item < 1 or item > 10_080 for item in value):
            raise ValueError("提醒时间必须介于 1 分钟和 7 天之间")
        return sorted(set(value), reverse=True)
