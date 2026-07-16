from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GapIvScenarioResult:
    gap: float
    iv_scenario: str
    pnl: float
    accepted: bool
    reason: str | None = None


@dataclass(frozen=True)
class StressSummary:
    scenarios: tuple[GapIvScenarioResult, ...]
    worst_loss: float
    rejected: bool
    reject_reason: str | None = None
