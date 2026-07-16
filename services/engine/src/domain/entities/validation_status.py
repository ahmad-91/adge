from __future__ import annotations

from enum import Enum


class ValidationStatus(str, Enum):
    UNVALIDATABLE = "UNVALIDATABLE"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    VALIDATED = "VALIDATED"
    UNVALIDATED = "UNVALIDATED - DO NOT USE WITH REAL CAPITAL"
