from __future__ import annotations

import os
from dataclasses import asdict

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from application.dto.analyze_dto import AnalyzeRequestDTO
from infrastructure.di.container import (
    build_analyze_trade,
    build_options_history,
    get_job_store,
    start_validation_job,
)


class AnalyzeBody(BaseModel):
    S0: float = Field(..., gt=0)
    sigma_base: float = Field(..., gt=0)
    r: float = Field(0.045, ge=0)
    Target: float = Field(..., gt=0)
    Bias: str
    Capital: float = Field(..., gt=0)
    Total_Portfolio_Value: float = Field(..., gt=0)
    allow_short: bool = False
    ATR_14: float = Field(..., gt=0)
    ticker: str | None = None
    sigma_is_historical_approx: bool = False


class ValidationJobBody(BaseModel):
    tickers: list[str] = Field(default_factory=lambda: ["SPY", "QQQ", "AAPL"])
    min_trades: int = Field(300, ge=10, le=5000)
    r: float = 0.045
    capital: float = 10_000
    total_portfolio_value: float = 50_000
    hold_days: int = 21
    sample_every_n_days: int = 5


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_KEY", "").strip()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


def create_app() -> FastAPI:
    app = FastAPI(title="ADGE Engine", version="3.1.0")

    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    analyze_uc = build_analyze_trade()

    @app.get("/health")
    def health():
        hist = build_options_history()
        return {
            "ok": True,
            "service": "adge-engine",
            "version": "3.1.0",
            "options_history_available": hist.is_available(),
            "validation_gate": (
                "PENDING_VALIDATION" if hist.is_available() else "UNVALIDATABLE"
            ),
        }

    @app.post("/v1/analyze", dependencies=[Depends(verify_api_key)])
    def analyze(body: AnalyzeBody):
        bias = body.Bias.lower().strip()
        if bias not in ("bullish", "bearish"):
            raise HTTPException(status_code=400, detail="Bias must be bullish or bearish")
        req = AnalyzeRequestDTO(
            s0=body.S0,
            sigma_base=body.sigma_base,
            r=body.r,
            target=body.Target,
            bias=bias,
            capital=body.Capital,
            total_portfolio_value=body.Total_Portfolio_Value,
            allow_short=body.allow_short,
            atr_14=body.ATR_14,
            ticker=body.ticker,
            sigma_is_historical_approx=body.sigma_is_historical_approx,
        )
        result = analyze_uc.execute(req)
        return asdict(result)

    @app.post("/v1/validation/jobs", dependencies=[Depends(verify_api_key)])
    def create_validation_job(body: ValidationJobBody):
        hist = build_options_history()
        if not hist.is_available():
            raise HTTPException(
                status_code=400,
                detail=(
                    "UNVALIDATABLE: set DATA_SOURCE_URL to independent options Parquet "
                    "(e.g. https://static.philippdubach.com/data/options/{ticker}/options.parquet)"
                ),
            )
        job_id = start_validation_job(body.model_dump())
        return {"job_id": job_id, "status": "PENDING"}

    @app.get("/v1/validation/jobs/{job_id}", dependencies=[Depends(verify_api_key)])
    def get_validation_job(job_id: str):
        job = get_job_store().get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    return app


app = create_app()
