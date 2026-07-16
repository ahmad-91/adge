from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Bias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True)
class TradeInputs:
    s0: float
    sigma_base: float
    r: float
    target: float
    bias: Bias
    capital: float
    total_portfolio_value: float
    allow_short: bool
    atr_14: float
    ticker: str | None = None

    def __post_init__(self) -> None:
        if self.s0 <= 0:
            raise ValueError("S0 must be positive")
        if self.sigma_base <= 0:
            raise ValueError("sigma_base must be positive")
        if self.capital <= 0:
            raise ValueError("Capital must be positive")
        if self.total_portfolio_value <= 0:
            raise ValueError("Total_Portfolio_Value must be positive")
        if self.target <= 0:
            raise ValueError("Target must be positive")
