from __future__ import annotations

from adapters.outbound.pricing.black_scholes_adapter import BlackScholesAdapter


def test_call_atm_positive():
    bs = BlackScholesAdapter()
    px = bs.price_call(100, 100, 0.25, 0.2, 0.05)
    assert px > 0
    d = bs.delta_call(100, 100, 0.25, 0.2, 0.05)
    assert 0.4 < d < 0.7


def test_put_call_parity_approx():
    bs = BlackScholesAdapter()
    s, k, tau, sigma, r = 100.0, 100.0, 1.0, 0.2, 0.05
    c = bs.price_call(s, k, tau, sigma, r)
    p = bs.price_put(s, k, tau, sigma, r)
    # C - P ≈ S - K e^{-rT}
    lhs = c - p
    rhs = s - k * __import__("math").exp(-r * tau)
    assert abs(lhs - rhs) < 1e-6
