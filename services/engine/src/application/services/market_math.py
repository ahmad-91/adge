from __future__ import annotations

import math
from datetime import date, timedelta

from scipy.stats import norm

from domain.entities.trade_inputs import Bias
from domain.policies.risk_limits import (
    EVENT_MULTIPLIER,
    K_CALL_SKEW,
    K_PUT_SKEW,
    POST_CRUSH_FACTOR,
)
from domain.entities.sigma_surface import SigmaSurface


def build_sigma_surface(sigma_base: float, has_earnings_in_tau: bool) -> SigmaSurface:
    return SigmaSurface(
        base=sigma_base,
        stress=sigma_base * 1.40,
        post_crush=sigma_base * POST_CRUSH_FACTOR,
        event=sigma_base * (EVENT_MULTIPLIER if has_earnings_in_tau else 1.0),
    )


def skewed_sigma(sigma_atm: float, k: float, s0: float, option_type: str) -> float:
    moneyness = abs(math.log(k / s0))
    if option_type == "call":
        return sigma_atm * (1 - K_CALL_SKEW * moneyness)
    return sigma_atm * (1 + K_PUT_SKEW * moneyness)


def round_to_standard_strike(k: float, s0: float) -> float:
    step = 0.5 if s0 < 25 else (1.0 if s0 < 100 else 2.5)
    return round(k / step) * step


def get_upcoming_fridays(today: date, weeks_ahead: int = 52) -> list[date]:
    days_until_friday = (4 - today.weekday()) % 7
    first_friday = today + timedelta(days=days_until_friday if days_until_friday > 0 else 7)
    return [first_friday + timedelta(weeks=i) for i in range(weeks_ahead)]


def prob_reach_target(
    s0: float,
    target: float,
    sigma: float,
    r: float,
    tau: float,
    bias: Bias,
) -> float:
    if tau <= 0:
        return 0.0
    d = (math.log(target / s0) - (r - 0.5 * sigma**2) * tau) / (sigma * math.sqrt(tau))
    p_above = 1.0 - float(norm.cdf(d))
    return p_above if bias == Bias.BULLISH else (1.0 - p_above)


def implied_strike(
    s0: float,
    sigma_atm: float,
    r: float,
    tau: float,
    target_delta: float,
    option_type: str = "call",
) -> float:
    if option_type == "call":
        z = float(norm.ppf(target_delta))
    else:
        z = float(norm.ppf(target_delta + 1))
    k_guess = s0 * math.exp(-(z * sigma_atm * math.sqrt(tau)) + (r - 0.5 * sigma_atm**2) * tau)
    sig_k = skewed_sigma(sigma_atm, k_guess, s0, option_type)
    k = s0 * math.exp(-(z * sig_k * math.sqrt(tau)) + (r - 0.5 * sig_k**2) * tau)
    return round_to_standard_strike(k, s0)
