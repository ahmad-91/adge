from __future__ import annotations

from domain.policies.risk_limits import MAX_RISK_PCT_OF_PORTFOLIO


def gap_loss_limit(total_portfolio_value: float, multiplier: float = 1.5) -> float:
    return multiplier * MAX_RISK_PCT_OF_PORTFOLIO * total_portfolio_value


def should_reject_gap_loss(worst_loss: float, total_portfolio_value: float) -> bool:
    """worst_loss is typically negative; reject if magnitude exceeds limit."""
    limit = gap_loss_limit(total_portfolio_value)
    return abs(min(worst_loss, 0.0)) > limit
