from __future__ import annotations

from pathlib import Path

from adapters.outbound.persistence.sqlite_job_store import SqliteJobStore


def test_job_survives_reopen(tmp_path: Path):
    db = tmp_path / "jobs.sqlite"
    store = SqliteJobStore(db)
    job_id = store.create("validation", {"tickers": ["SPY"], "min_trades": 10})
    store.update(job_id, status="DONE", result={"status": "VALIDATED"}, error=None)
    store.close()

    again = SqliteJobStore(db)
    job = again.get(job_id)
    assert job is not None
    assert job["status"] == "DONE"
    assert job["result"]["status"] == "VALIDATED"
    assert job["payload"]["tickers"] == ["SPY"]
    again.close()


def test_interrupted_jobs_marked_failed_on_start(tmp_path: Path):
    db = tmp_path / "jobs.sqlite"
    store = SqliteJobStore(db)
    pending_id = store.create("validation", {"min_trades": 10})
    running_id = store.create("validation", {"min_trades": 20})
    store.update(running_id, status="RUNNING")
    store.close()

    again = SqliteJobStore(db)
    pending = again.get(pending_id)
    running = again.get(running_id)
    assert pending is not None and pending["status"] == "FAILED"
    assert running is not None and running["status"] == "FAILED"
    assert "restart" in (pending["error"] or "").lower()
    again.close()


def test_get_missing_returns_none(tmp_path: Path):
    store = SqliteJobStore(tmp_path / "jobs.sqlite")
    assert store.get("does-not-exist") is None
    store.close()
