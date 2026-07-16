from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class HistoricalOptionQuote:
    quote_date: date
    ticker: str
    expiration: date
    strike: float
    option_type: str  # call | put
    bid: float
    ask: float
    mark: float
    implied_volatility: float
    delta: float | None = None
    open_interest: float | None = None


@dataclass(frozen=True)
class HistoricalUnderlyingBar:
    quote_date: date
    ticker: str
    close: float


@dataclass(frozen=True)
class PaperTradeResult:
    ticker: str
    entry_date: date
    exit_date: date
    pnl: float
    capital_at_risk: float
    notes: str = ""


class PricingPort(ABC):
    @abstractmethod
    def price_call(self, s: float, k: float, tau: float, sigma: float, r: float) -> float: ...

    @abstractmethod
    def price_put(self, s: float, k: float, tau: float, sigma: float, r: float) -> float: ...

    @abstractmethod
    def delta_call(self, s: float, k: float, tau: float, sigma: float, r: float) -> float: ...

    @abstractmethod
    def delta_put(self, s: float, k: float, tau: float, sigma: float, r: float) -> float: ...

    @abstractmethod
    def gamma(self, s: float, k: float, tau: float, sigma: float, r: float) -> float: ...

    @abstractmethod
    def vega(self, s: float, k: float, tau: float, sigma: float, r: float) -> float: ...

    @abstractmethod
    def theta_call(self, s: float, k: float, tau: float, sigma: float, r: float) -> float: ...

    @abstractmethod
    def theta_put(self, s: float, k: float, tau: float, sigma: float, r: float) -> float: ...


class MarketDataPort(ABC):
    @abstractmethod
    def next_earnings_date(self, ticker: str | None) -> date | None: ...


class OptionsHistoryPort(ABC):
    """Independent options/IV history. MUST NOT be derived from internal BS pricing."""

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def derived_from_internal_bs(self) -> bool: ...

    @abstractmethod
    def available_tickers(self) -> Sequence[str]: ...

    @abstractmethod
    def load_underlying(self, ticker: str) -> Sequence[HistoricalUnderlyingBar]: ...

    @abstractmethod
    def load_option_quotes(
        self,
        ticker: str,
        start: date | None = None,
        end: date | None = None,
    ) -> Sequence[HistoricalOptionQuote]: ...


class ClockPort(ABC):
    @abstractmethod
    def today(self) -> date: ...


class JobStorePort(ABC):
    @abstractmethod
    def create(self, job_type: str, payload: dict) -> str: ...

    @abstractmethod
    def get(self, job_id: str) -> dict | None: ...

    @abstractmethod
    def update(self, job_id: str, **fields) -> None: ...
