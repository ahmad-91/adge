from __future__ import annotations

from domain.entities.composition import Composition
from domain.policies.risk_limits import REDUNDANCY_LIMIT


def functional_redundancy(
    stock_delta: float,
    options_delta: float,
) -> float:
    """Overlap of stock vs options contribution in the same delta direction."""
    if stock_delta == 0 or options_delta == 0:
        return 0.0
    same_direction = (stock_delta > 0 and options_delta > 0) or (
        stock_delta < 0 and options_delta < 0
    )
    if not same_direction:
        return 0.0
    total = abs(stock_delta) + abs(options_delta)
    if total == 0:
        return 0.0
    return min(abs(stock_delta), abs(options_delta)) / total


def exceeds_redundancy(stock_delta: float, options_delta: float, limit: float = REDUNDANCY_LIMIT) -> bool:
    return functional_redundancy(stock_delta, options_delta) > limit


def short_allowed(composition: Composition, allow_short: bool) -> bool:
    if not allow_short and composition.stock_factor == -1:
        return False
    return True
