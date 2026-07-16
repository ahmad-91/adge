from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Sequence
from urllib.parse import urljoin

import pandas as pd

from application.ports import (
    HistoricalOptionQuote,
    HistoricalUnderlyingBar,
    OptionsHistoryPort,
)


class NullOptionsHistory(OptionsHistoryPort):
    """No independent options/IV history → forces UNVALIDATABLE."""

    def is_available(self) -> bool:
        return False

    def derived_from_internal_bs(self) -> bool:
        return False

    def available_tickers(self) -> Sequence[str]:
        return []

    def load_underlying(self, ticker: str) -> Sequence[HistoricalUnderlyingBar]:
        return []

    def load_option_quotes(
        self,
        ticker: str,
        start: date | None = None,
        end: date | None = None,
    ) -> Sequence[HistoricalOptionQuote]:
        return []


class ParquetOptionsHistory(OptionsHistoryPort):
    """
    Independent historical options/IV from Parquet.

    DATA_SOURCE_URL examples:
      - https://static.philippdubach.com/data/options/{ticker}/options.parquet
      - https://static.philippdubach.com/data/options/   (base; appends {ticker}/...)
      - C:\\data\\options\\{ticker}\\options.parquet
      - file:///C:/data/options/{ticker}/options.parquet

    Companion underlying file is resolved by replacing options.parquet → underlying.parquet
    or {ticker}/options.parquet → {ticker}/underlying.parquet.
    """

    DEFAULT_TICKERS = ("SPY", "QQQ", "IWM", "AAPL", "MSFT", "TSLA", "AMD", "NVDA")

    def __init__(
        self,
        path_or_url_template: str,
        tickers: Sequence[str] | None = None,
        derived_from_internal_bs: bool = False,
    ):
        if derived_from_internal_bs:
            raise ValueError("Options history must not be derived from internal BS")
        self.template = path_or_url_template.strip().rstrip("/")
        self._tickers = [t.upper() for t in (tickers or self.DEFAULT_TICKERS)]
        self._cache_options: dict[str, pd.DataFrame] = {}
        self._cache_underlying: dict[str, pd.DataFrame] = {}
        self._available = bool(self.template)

    def is_available(self) -> bool:
        return self._available

    def derived_from_internal_bs(self) -> bool:
        return False

    def available_tickers(self) -> Sequence[str]:
        return list(self._tickers)

    def _resolve(self, ticker: str, kind: str) -> str:
        """kind: options | underlying"""
        t = ticker.upper()
        tmpl = self.template
        filename = "options.parquet" if kind == "options" else "underlying.parquet"

        if "{ticker}" in tmpl:
            path = tmpl.replace("{ticker}", t)
            if path.endswith("options.parquet") and kind == "underlying":
                path = path.replace("options.parquet", "underlying.parquet")
            elif not path.endswith(".parquet"):
                path = f"{path.rstrip('/')}/{filename}"
            return path

        # Base directory / URL
        if tmpl.endswith(".parquet"):
            # Single-file mode: only options path given
            if kind == "options":
                return tmpl
            return tmpl.replace("options.parquet", "underlying.parquet")

        # Treat as folder/base
        if tmpl.startswith("http://") or tmpl.startswith("https://") or tmpl.startswith("file:"):
            return urljoin(tmpl.rstrip("/") + "/", f"{t}/{filename}")
        return str(Path(tmpl) / t / filename)

    def _read_parquet(self, path: str) -> pd.DataFrame:
        # pandas + pyarrow can read http(s) and local paths
        return pd.read_parquet(path)

    def _get_options_df(self, ticker: str) -> pd.DataFrame:
        key = ticker.upper()
        if key not in self._cache_options:
            path = self._resolve(key, "options")
            df = self._read_parquet(path)
            df = self._normalize_options(df, key)
            self._cache_options[key] = df
        return self._cache_options[key]

    def _get_underlying_df(self, ticker: str) -> pd.DataFrame:
        key = ticker.upper()
        if key not in self._cache_underlying:
            path = self._resolve(key, "underlying")
            try:
                df = self._read_parquet(path)
                df = self._normalize_underlying(df, key)
            except Exception:
                # Fallback: infer rough spot from option chain mid strikes later
                df = pd.DataFrame(columns=["quote_date", "ticker", "close"])
            self._cache_underlying[key] = df
        return self._cache_underlying[key]

    @staticmethod
    def _normalize_options(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        cols = {c.lower(): c for c in df.columns}
        rename = {}
        mapping = {
            "date": "quote_date",
            "quote_date": "quote_date",
            "expiration": "expiration",
            "expiry": "expiration",
            "strike": "strike",
            "type": "option_type",
            "option_type": "option_type",
            "bid": "bid",
            "ask": "ask",
            "mark": "mark",
            "last": "last",
            "implied_volatility": "implied_volatility",
            "iv": "implied_volatility",
            "delta": "delta",
            "open_interest": "open_interest",
            "symbol": "symbol",
        }
        for src, dst in mapping.items():
            if src in cols:
                rename[cols[src]] = dst
        out = df.rename(columns=rename).copy()
        if "mark" not in out.columns:
            if "bid" in out.columns and "ask" in out.columns:
                out["mark"] = (out["bid"].fillna(0) + out["ask"].fillna(0)) / 2.0
            elif "last" in out.columns:
                out["mark"] = out["last"]
            else:
                out["mark"] = 0.0
        out["quote_date"] = pd.to_datetime(out["quote_date"]).dt.date
        out["expiration"] = pd.to_datetime(out["expiration"]).dt.date
        out["option_type"] = out["option_type"].astype(str).str.lower()
        out["option_type"] = out["option_type"].replace(
            {"c": "call", "p": "put", "calls": "call", "puts": "put"}
        )
        out["ticker"] = ticker.upper()
        for col in ("bid", "ask", "mark", "strike", "implied_volatility"):
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce")
        out = out.dropna(subset=["quote_date", "expiration", "strike", "option_type", "mark"])
        return out

    @staticmethod
    def _normalize_underlying(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        cols = {c.lower(): c for c in df.columns}
        date_col = cols.get("date") or cols.get("quote_date")
        close_col = cols.get("close") or cols.get("adj_close") or cols.get("adjclose")
        if not date_col or not close_col:
            return pd.DataFrame(columns=["quote_date", "ticker", "close"])
        out = pd.DataFrame(
            {
                "quote_date": pd.to_datetime(df[date_col]).dt.date,
                "close": pd.to_numeric(df[close_col], errors="coerce"),
                "ticker": ticker.upper(),
            }
        ).dropna()
        return out

    def load_underlying(self, ticker: str) -> Sequence[HistoricalUnderlyingBar]:
        df = self._get_underlying_df(ticker)
        return [
            HistoricalUnderlyingBar(quote_date=r.quote_date, ticker=r.ticker, close=float(r.close))
            for r in df.itertuples(index=False)
        ]

    def load_option_quotes(
        self,
        ticker: str,
        start: date | None = None,
        end: date | None = None,
    ) -> Sequence[HistoricalOptionQuote]:
        df = self._get_options_df(ticker)
        if start is not None:
            df = df[df["quote_date"] >= start]
        if end is not None:
            df = df[df["quote_date"] <= end]
        rows: list[HistoricalOptionQuote] = []
        for r in df.itertuples(index=False):
            iv = getattr(r, "implied_volatility", None)
            if iv is None or pd.isna(iv) or float(iv) <= 0:
                continue
            bid = float(getattr(r, "bid", 0) or 0)
            ask = float(getattr(r, "ask", 0) or 0)
            mark = float(r.mark)
            delta = getattr(r, "delta", None)
            oi = getattr(r, "open_interest", None)
            rows.append(
                HistoricalOptionQuote(
                    quote_date=r.quote_date,
                    ticker=r.ticker,
                    expiration=r.expiration,
                    strike=float(r.strike),
                    option_type=str(r.option_type),
                    bid=bid,
                    ask=ask,
                    mark=mark,
                    implied_volatility=float(iv),
                    delta=None if delta is None or pd.isna(delta) else float(delta),
                    open_interest=None if oi is None or pd.isna(oi) else float(oi),
                )
            )
        return rows
