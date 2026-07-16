from __future__ import annotations


def efficiency_net(delta_net: float, capital_at_risk: float, rebalance_cost: float) -> float:
    denom = capital_at_risk + rebalance_cost
    if denom <= 0:
        return 0.0
    return delta_net / denom


def rebalance_cost_too_high(rebalance_cost: float, premium_total: float, ratio: float = 0.3) -> bool:
    if premium_total <= 0:
        return rebalance_cost > 0
    return rebalance_cost > ratio * premium_total
