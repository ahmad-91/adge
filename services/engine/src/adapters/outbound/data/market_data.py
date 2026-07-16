from __future__ import annotations

from datetime import date

from application.ports import MarketDataPort


class StaticMarketData(MarketDataPort):
    """No external earnings feed by default (keeps engine offline-capable)."""

    def __init__(self, earnings: dict[str, date] | None = None):
        self._earnings = earnings or {}

    def next_earnings_date(self, ticker: str | None) -> date | None:
        if not ticker:
            return None
        return self._earnings.get(ticker.upper())
