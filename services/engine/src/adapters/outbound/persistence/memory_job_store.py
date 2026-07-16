from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any


class InMemoryJobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, dict[str, Any]] = {}

    def create(self, job_type: str, payload: dict) -> str:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "type": job_type,
                "status": "PENDING",
                "payload": payload,
                "result": None,
                "error": None,
                "created_at": now,
                "updated_at": now,
            }
        return job_id

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.update(fields)
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
