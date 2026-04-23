"""Resumable Nifty 500 data pipeline for the Indian stock analytics project."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Iterator

import pandas as pd
from sqlalchemy import create_engine

from market_utils import engineer_features, fetch_history, normalize_ticker
from stock_universe import get_nifty500_metadata, get_ticker_list

DATA_DIR = Path(__file__).resolve().parent / "data"
SQLITE_PATH = DATA_DIR / "stocks.db"
RAW_CSV_PATH = DATA_DIR / "all_stocks_10yr.csv"
FEATURE_CSV_PATH = DATA_DIR / "all_stocks_features.csv"

NIFTY_500_METADATA = get_nifty500_metadata()
NIFTY_500_TICKERS = get_ticker_list()


def ensure_directories() -> None:
    """Ensure pipeline directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_engine():
    """Create a SQLite SQLAlchemy engine."""
    ensure_directories()
    return create_engine(f"sqlite:///{SQLITE_PATH}")


def init_db() -> None:
    """Initialize the stock_data table."""
    ensure_directories()
    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_data (
                Date TEXT,
                Ticker TEXT,
                Open REAL,
                High REAL,
                Low REAL,
                Close REAL,
                Volume REAL,
                SMA_20 REAL,
                SMA_50 REAL,
                SMA_200 REAL,
                EMA_12 REAL,
                EMA_26 REAL,
                MACD REAL,
                MACD_Signal REAL,
                MACD_Histogram REAL,
                RSI_14 REAL,
                BB_Upper REAL,
                BB_Middle REAL,
                BB_Lower REAL,
                ATR_14 REAL,
                OBV REAL,
                ROC_10 REAL,
                Stochastic_K REAL,
                Stochastic_D REAL,
                Daily_Return REAL,
                Volatility_20 REAL,
                Volume_SMA_20 REAL,
                Price_to_SMA50_ratio REAL,
                Target REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_stock_data (
                Date TEXT,
                Ticker TEXT,
                Open REAL,
                High REAL,
                Low REAL,
                Close REAL,
                Volume REAL
            )
            """
        )
        conn.commit()


def get_completed_tickers() -> set[str]:
    """Return the set of tickers already cached in SQLite."""
    if not SQLITE_PATH.exists():
        return set()
    with sqlite3.connect(SQLITE_PATH) as conn:
        try:
            rows = conn.execute("SELECT DISTINCT Ticker FROM stock_data").fetchall()
            return {row[0] for row in rows}
        except sqlite3.OperationalError:
            return set()


def fetch_single_stock(ticker: str, period: str = "10y") -> pd.DataFrame:
    """Fetch a single stock and return a clean feature-enriched DataFrame."""
    normalized = normalize_ticker(ticker)
    history = fetch_history(normalized, period=period, interval="1d")
    if history.empty:
        return pd.DataFrame()
    featured = engineer_features(history).dropna().reset_index(drop=True)
    return featured


def fetch_single_stock_raw(ticker: str, period: str = "10y") -> pd.DataFrame:
    """Fetch a single stock and return the raw OHLCV history."""
    normalized = normalize_ticker(ticker)
    history = fetch_history(normalized, period=period, interval="1d")
    if history.empty:
        return pd.DataFrame()
    return history.sort_values("Date").reset_index(drop=True)


def iter_pipeline_rows() -> Iterator[tuple[str, pd.DataFrame, pd.DataFrame]]:
    """Yield pending tickers with both raw and engineered data."""
    completed = get_completed_tickers()
    for ticker in NIFTY_500_TICKERS:
        if ticker in completed:
            continue
        try:
            raw_data = fetch_single_stock_raw(ticker, period="10y")
            if raw_data.empty:
                print(f"{ticker} | rows fetched: 0 | running total row count: skipped")
            else:
                featured = engineer_features(raw_data).dropna().reset_index(drop=True)
                if featured.empty:
                    print(f"{ticker} | rows fetched: 0 | running total row count: skipped")
                else:
                    yield ticker, raw_data, featured
        except Exception as exc:
            print(f"{ticker} | error: {exc}")
        time.sleep(0.3)


def rebuild_csv_exports() -> tuple[int, int]:
    """Rebuild raw and engineered CSV exports from SQLite."""
    with sqlite3.connect(SQLITE_PATH) as conn:
        raw_data = pd.read_sql_query("SELECT * FROM raw_stock_data", conn, parse_dates=["Date"])
        all_data = pd.read_sql_query("SELECT * FROM stock_data", conn, parse_dates=["Date"])
    if all_data.empty and raw_data.empty:
        return 0, 0

    if not raw_data.empty:
        raw_data.sort_values(["Ticker", "Date"], inplace=True)
        raw_data.to_csv(RAW_CSV_PATH, index=False)
    all_data.dropna(inplace=True)
    all_data.sort_values(["Ticker", "Date"], inplace=True)
    all_data.to_csv(FEATURE_CSV_PATH, index=False)
    return len(raw_data), all_data["Ticker"].nunique()


def run_pipeline() -> None:
    """Run the full resumable data pipeline."""
    ensure_directories()
    init_db()
    engine = get_engine()

    running_rows = 0
    for ticker, raw_data, featured in iter_pipeline_rows():
        raw_data.to_sql("raw_stock_data", engine, if_exists="append", index=False)
        featured.to_sql("stock_data", engine, if_exists="append", index=False)
        running_rows += len(raw_data)
        print(f"{ticker} | rows fetched: {len(raw_data)} | running total row count: {running_rows}")

    total_rows, total_tickers = rebuild_csv_exports()
    print(f"Total rows: {total_rows} | Tickers fetched: {total_tickers} | File saved.")


if __name__ == "__main__":
    run_pipeline()
