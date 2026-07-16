# ADGE — Adaptive Delta-Gamma Engine v3.1

Monorepo: Clean Architecture · Next.js web + Python engine · both on **Fly.io**.

## Structure

```
adge/
├── apps/web                 # Next.js UI (Fly: adge-web)
└── services/engine          # FastAPI ADGE engine (Fly: adge-engine)
    └── src/
        ├── domain/
        ├── application/     # AnalyzeTrade + RunValidationProtocol
        ├── adapters/        # HTTP, BS, Parquet history, job store
        └── infrastructure/
```

## Local run

### 1) Engine

```powershell
cd C:\Users\urr\adge\services\engine
python -m pip install -r requirements.txt
$env:PYTHONPATH="src"
# Optional — required for VALIDATED path:
$env:DATA_SOURCE_URL="https://static.philippdubach.com/data/options/{ticker}/options.parquet"
$env:OPTIONS_TICKERS="SPY,QQQ,AAPL"
python -m uvicorn adapters.inbound.http.fastapi_app:app --host 127.0.0.1 --port 8080
```

- Health: `GET /health`
- Analyze: `POST /v1/analyze`
- Validation job: `POST /v1/validation/jobs` then `GET /v1/validation/jobs/{id}`

Validation jobs persist in SQLite (`JOB_STORE_PATH`, default `./data/jobs.sqlite`).
Set `JOB_STORE_BACKEND=memory` only for ephemeral local tests.
Jobs left `PENDING`/`RUNNING` across a process restart are marked `FAILED` (resubmit).

Without `DATA_SOURCE_URL` → `status = UNVALIDATABLE`.

### 2) Web

```powershell
cd C:\Users\urr\adge\apps\web
copy .env.example .env.local
npm install
npm run dev
```

Open `http://127.0.0.1:3000`

## Validation protocol

Uses **independent** option marks/IV from Parquet (philippdubach / R2 / local).

- Phase A: BS unit identities
- Phase B: ≥ `min_trades` paper trades from historical marks (not internal BS prices)
- Phase C: walk-forward + sensitivity
- Phase D: COVID 2020 / 2022 stress windows
- Accept only if bootstrap CI95 expectancy lower bound > 0 and stress MaxDD within limit

Circular validation is rejected if history claims derivation from internal BS.

## Fly.io

```powershell
cd services/engine
fly apps create adge-engine
fly volumes create adge_engine_data --region ams --size 1
fly secrets set API_KEY=secret DATA_SOURCE_URL="https://static.philippdubach.com/data/options/{ticker}/options.parquet"
fly deploy

cd ../../apps/web
fly apps create adge-web
fly secrets set ENGINE_URL=http://adge-engine.internal:8080 ENGINE_API_KEY=secret
fly deploy
```

## Disclaimer

Educational quantitative tool only. Not investment advice.
