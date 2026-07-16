from __future__ import annotations

from dataclasses import dataclass


# Design constants (engineering decisions)
BETA_MAX = 0.08
GAMMA_MAX = 0.02
REDUNDANCY_LIMIT = 0.70
MAX_RISK_PCT_OF_PORTFOLIO = 0.25
P_FLOOR = 0.25

# UNCALIBRATED_PLACEHOLDER — calibrate later from independent data + sensitivity bands
EVENT_MULTIPLIER = 1.5
POST_CRUSH_FACTOR = 0.7
K_CALL_SKEW = 0.15
K_PUT_SKEW = 0.15
REBALANCE_TRIGGER = 0.15

SENSITIVITY_BANDS = {
    "EVENT_MULTIPLIER": (1.2, 1.8),
    "POST_CRUSH_FACTOR": (0.55, 0.85),
    "K_CALL_SKEW": (0.05, 0.25),
    "K_PUT_SKEW": (0.05, 0.30),
    "REBALANCE_TRIGGER": (0.10, 0.25),
}

UNCALIBRATED_PLACEHOLDERS = {
    "EVENT_MULTIPLIER": EVENT_MULTIPLIER,
    "POST_CRUSH_FACTOR": POST_CRUSH_FACTOR,
    "K_CALL_SKEW": K_CALL_SKEW,
    "K_PUT_SKEW": K_PUT_SKEW,
    "REBALANCE_TRIGGER": REBALANCE_TRIGGER,
}


@dataclass(frozen=True)
class RiskLimits:
    beta_max: float = BETA_MAX
    gamma_max: float = GAMMA_MAX
    redundancy_limit: float = REDUNDANCY_LIMIT
    max_risk_pct_of_portfolio: float = MAX_RISK_PCT_OF_PORTFOLIO
    p_floor: float = P_FLOOR
