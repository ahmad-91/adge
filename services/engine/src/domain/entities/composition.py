from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Composition:
    stock_factor: int  # -1, 0, +1
    nc: int
    np: int

    def __post_init__(self) -> None:
        if self.stock_factor not in (-1, 0, 1):
            raise ValueError("stock_factor must be -1, 0, or 1")
