from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SqliteJobStore:
    """Durable job store. Survives process restarts when path is on persistent disk."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._ensure_schema()
        self._recover_interrupted()

    def _ensure_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _recover_interrupted(self) -> None:
        """Background threads die on restart; mark in-flight jobs as failed."""
        now = self._now()
        with self._lock:
            self._conn.execute(
                """
                UPDATE jobs
                SET status = ?, error = ?, updated_at = ?
                WHERE status IN ('PENDING', 'RUNNING')
                """,
                (
                    "FAILED",
                    "Interrupted by process restart — resubmit the job",
                    now,
                ),
            )
            self._conn.commit()

    def create(self, job_type: str, payload: dict) -> str:
        job_id = str(uuid.uuid4())
        now = self._now()
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO jobs (id, type, status, payload, result, error, created_at, updated_at)
                VALUES (?, ?, ?, ?, NULL, NULL, ?, ?)
                """,
                (job_id, job_type, "PENDING", json.dumps(payload), now, now),
            )
            self._conn.commit()
        return job_id

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def update(self, job_id: str, **fields: Any) -> None:
        allowed = {"status", "payload", "result", "error", "type"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        updates["updated_at"] = self._now()
        cols: list[str] = []
        values: list[Any] = []
        for key, value in updates.items():
            cols.append(f"{key} = ?")
            if key in ("payload", "result") and value is not None and not isinstance(value, str):
                values.append(json.dumps(value))
            else:
                values.append(value)
        values.append(job_id)
        with self._lock:
            self._conn.execute(
                f"UPDATE jobs SET {', '.join(cols)} WHERE id = ?",
                values,
            )
            self._conn.commit()

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> dict[str, Any]:
        result_raw = row["result"]
        payload_raw = row["payload"]
        return {
            "id": row["id"],
            "type": row["type"],
            "status": row["status"],
            "payload": json.loads(payload_raw) if payload_raw else {},
            "result": json.loads(result_raw) if result_raw else None,
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()
