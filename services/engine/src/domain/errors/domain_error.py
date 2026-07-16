from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RejectionReason:
    code: str
    message: str


class DomainError(Exception):
    def __init__(self, reason: RejectionReason):
        self.reason = reason
        super().__init__(reason.message)
