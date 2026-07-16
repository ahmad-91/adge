from __future__ import annotations

import math

from scipy.stats import norm

from application.ports import PricingPort


class BlackScholesAdapter(PricingPort):
    def _d1(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        return (math.log(s / k) + (r + 0.5 * sigma**2) * tau) / (sigma * math.sqrt(tau))

    def _d2(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        return self._d1(s, k, tau, sigma, r) - sigma * math.sqrt(tau)

    def price_call(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        if tau <= 0:
            return max(s - k, 0.0)
        d1, d2 = self._d1(s, k, tau, sigma, r), self._d2(s, k, tau, sigma, r)
        return float(s * norm.cdf(d1) - k * math.exp(-r * tau) * norm.cdf(d2))

    def price_put(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        if tau <= 0:
            return max(k - s, 0.0)
        d1, d2 = self._d1(s, k, tau, sigma, r), self._d2(s, k, tau, sigma, r)
        return float(k * math.exp(-r * tau) * norm.cdf(-d2) - s * norm.cdf(-d1))

    def delta_call(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        if tau <= 0:
            return 1.0 if s > k else 0.0
        return float(norm.cdf(self._d1(s, k, tau, sigma, r)))

    def delta_put(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        if tau <= 0:
            return -1.0 if s < k else 0.0
        return float(norm.cdf(self._d1(s, k, tau, sigma, r)) - 1.0)

    def gamma(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        if tau <= 0:
            return 0.0
        return float(norm.pdf(self._d1(s, k, tau, sigma, r)) / (s * sigma * math.sqrt(tau)))

    def vega(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        if tau <= 0:
            return 0.0
        return float(s * norm.pdf(self._d1(s, k, tau, sigma, r)) * math.sqrt(tau))

    def theta_call(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        if tau <= 0:
            return 0.0
        d1, d2 = self._d1(s, k, tau, sigma, r), self._d2(s, k, tau, sigma, r)
        return float(
            -s * norm.pdf(d1) * sigma / (2 * math.sqrt(tau))
            - r * k * math.exp(-r * tau) * norm.cdf(d2)
        )

    def theta_put(self, s: float, k: float, tau: float, sigma: float, r: float) -> float:
        if tau <= 0:
            return 0.0
        d1, d2 = self._d1(s, k, tau, sigma, r), self._d2(s, k, tau, sigma, r)
        return float(
            -s * norm.pdf(d1) * sigma / (2 * math.sqrt(tau))
            + r * k * math.exp(-r * tau) * norm.cdf(-d2)
        )
