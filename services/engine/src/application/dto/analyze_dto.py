from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class AnalyzeRequestDTO:
    s0: float
    sigma_base: float
    r: float
    target: float
    bias: str
    capital: float
    total_portfolio_value: float
    allow_short: bool
    atr_14: float
    ticker: str | None = None
    sigma_is_historical_approx: bool = False


@dataclass
class AnalyzeResponseDTO:
    status: str
    warnings: list[str]
    dte_days: int | None
    expiry: str | None
    probabilities: dict[str, float]
    kc: float | None
    kp: float | None
    strike_note: str
    composition: dict | None
    greeks: dict | None
    efficiency_net: float | None
    rebalance_cost: float | None
    premium_total: float | None
    capital_at_risk: float | None
    gap_iv_scenarios: list[dict]
    simulation_grid: list[dict]
    rejections: list[str]
    uncalibrated_placeholders: dict
    disclaimer: str
    extras: dict = field(default_factory=dict)
