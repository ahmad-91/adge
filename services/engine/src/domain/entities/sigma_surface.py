from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SigmaSurface:
    base: float
    stress: float
    post_crush: float
    event: float
