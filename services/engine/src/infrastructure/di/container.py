from __future__ import annotations

import os
import threading
from dataclasses import asdict

from adapters.outbound.data.clock import SystemClock
from adapters.outbound.data.market_data import StaticMarketData
from adapters.outbound.data.options_history import NullOptionsHistory, ParquetOptionsHistory
from adapters.outbound.persistence.memory_job_store import InMemoryJobStore
from adapters.outbound.persistence.sqlite_job_store import SqliteJobStore
from adapters.outbound.pricing.black_scholes_adapter import BlackScholesAdapter
from application.ports import JobStorePort
from application.use_cases.analyze_trade import AnalyzeTrade
from application.use_cases.run_validation import RunValidationProtocol, ValidationRequestDTO

_job_store: JobStorePort | None = None
_job_store_lock = threading.Lock()


def build_options_history():
    data_url = os.getenv("DATA_SOURCE_URL", "").strip()
    tickers_env = os.getenv("OPTIONS_TICKERS", "").strip()
    tickers = [t.strip().upper() for t in tickers_env.split(",") if t.strip()] or None
    if data_url:
        return ParquetOptionsHistory(data_url, tickers=tickers)
    return NullOptionsHistory()


def build_analyze_trade() -> AnalyzeTrade:
    return AnalyzeTrade(
        pricing=BlackScholesAdapter(),
        market_data=StaticMarketData(),
        options_history=build_options_history(),
        clock=SystemClock(),
        mc_paths=int(os.getenv("MC_PATHS", "80")),
    )


def build_validation() -> RunValidationProtocol:
    return RunValidationProtocol(
        options_history=build_options_history(),
        pricing=BlackScholesAdapter(),
    )


def _build_job_store() -> JobStorePort:
    backend = os.getenv("JOB_STORE_BACKEND", "sqlite").strip().lower()
    if backend in ("memory", "mem", "inmemory"):
        return InMemoryJobStore()
    path = os.getenv("JOB_STORE_PATH", "./data/jobs.sqlite").strip() or "./data/jobs.sqlite"
    return SqliteJobStore(path)


def get_job_store() -> JobStorePort:
    global _job_store
    if _job_store is None:
        with _job_store_lock:
            if _job_store is None:
                _job_store = _build_job_store()
    return _job_store


def start_validation_job(payload: dict) -> str:
    store = get_job_store()
    job_id = store.create("validation", payload)

    def _run() -> None:
        store.update(job_id, status="RUNNING")
        try:
            uc = build_validation()
            req = ValidationRequestDTO(
                tickers=payload.get("tickers") or ["SPY", "QQQ", "AAPL"],
                min_trades=int(payload.get("min_trades", 300)),
                r=float(payload.get("r", 0.045)),
                capital=float(payload.get("capital", 10_000)),
                total_portfolio_value=float(payload.get("total_portfolio_value", 50_000)),
                hold_days=int(payload.get("hold_days", 21)),
                sample_every_n_days=int(payload.get("sample_every_n_days", 5)),
            )
            report = uc.execute(req)
            store.update(job_id, status="DONE", result=asdict(report), error=None)
        except Exception as exc:  # noqa: BLE001
            store.update(job_id, status="FAILED", error=str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return job_id
