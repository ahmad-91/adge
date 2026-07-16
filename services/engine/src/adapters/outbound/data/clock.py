from __future__ import annotations

from datetime import date

from application.ports import ClockPort


class SystemClock(ClockPort):
    def today(self) -> date:
        return date.today()
