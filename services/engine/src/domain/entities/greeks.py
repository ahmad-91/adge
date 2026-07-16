from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NetGreeks:
    delta_net: float
    gamma_net: float
    vega_net: float
    theta_net: float
