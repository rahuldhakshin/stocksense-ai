"""Shared stock universe metadata helpers for the Indian market app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests

DATA_DIR = Path(__file__).resolve().parent / "data"
UNIVERSE_CACHE_PATH = DATA_DIR / "nifty500_metadata.json"
RAW_CACHE_PATH = DATA_DIR / "all_stocks_10yr.csv"
FEATURE_CACHE_PATH = DATA_DIR / "all_stocks_features.csv"
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/NIFTY_500"

BOOTSTRAP_UNIVERSE: list[dict[str, str]] = [
    {"symbol": "RELIANCE", "ticker": "RELIANCE.NS", "company_name": "Reliance Industries Ltd.", "sector": "Oil Gas & Consumable Fuels"},
    {"symbol": "TCS", "ticker": "TCS.NS", "company_name": "Tata Consultancy Services Ltd.", "sector": "Information Technology"},
    {"symbol": "INFY", "ticker": "INFY.NS", "company_name": "Infosys Ltd.", "sector": "Information Technology"},
    {"symbol": "HDFCBANK", "ticker": "HDFCBANK.NS", "company_name": "HDFC Bank Ltd.", "sector": "Financial Services"},
    {"symbol": "ICICIBANK", "ticker": "ICICIBANK.NS", "company_name": "ICICI Bank Ltd.", "sector": "Financial Services"},
    {"symbol": "SBIN", "ticker": "SBIN.NS", "company_name": "State Bank of India", "sector": "Financial Services"},
    {"symbol": "BHARTIARTL", "ticker": "BHARTIARTL.NS", "company_name": "Bharti Airtel Ltd.", "sector": "Telecommunication"},
    {"symbol": "ITC", "ticker": "ITC.NS", "company_name": "ITC Ltd.", "sector": "Fast Moving Consumer Goods"},
    {"symbol": "LT", "ticker": "LT.NS", "company_name": "Larsen & Toubro Ltd.", "sector": "Construction"},
    {"symbol": "AXISBANK", "ticker": "AXISBANK.NS", "company_name": "Axis Bank Ltd.", "sector": "Financial Services"},
    {"symbol": "KOTAKBANK", "ticker": "KOTAKBANK.NS", "company_name": "Kotak Mahindra Bank Ltd.", "sector": "Financial Services"},
    {"symbol": "SUNPHARMA", "ticker": "SUNPHARMA.NS", "company_name": "Sun Pharmaceutical Industries Ltd.", "sector": "Healthcare"},
]


def _fetch_nifty500_from_wikipedia(timeout: int = 30) -> list[dict[str, str]]:
    """Fetch Nifty 500 constituents from Wikipedia."""
    response = requests.get(WIKIPEDIA_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
    response.raise_for_status()
    tables = pd.read_html(response.text)
    table = next((df for df in tables if df.shape[0] >= 500 and df.shape[1] >= 6), None)
    if table is None:
        raise ValueError("Constituent table not found.")

    table.columns = table.iloc[0]
    table = table.iloc[1:].reset_index(drop=True)
    metadata: list[dict[str, str]] = []
    for _, row in table.iterrows():
        symbol = str(row["Symbol"]).strip()
        metadata.append(
            {
                "symbol": symbol,
                "ticker": symbol.replace("&", "%26") + ".NS",
                "company_name": str(row["Company Name"]).strip(),
                "sector": str(row["Industry"]).strip(),
            }
        )
    return metadata


def get_nifty500_metadata(refresh: bool = False) -> list[dict[str, str]]:
    """Return stock-universe metadata from cache, web, or bootstrap fallback."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if UNIVERSE_CACHE_PATH.exists() and not refresh:
        try:
            return json.loads(UNIVERSE_CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    try:
        metadata = _fetch_nifty500_from_wikipedia()
        UNIVERSE_CACHE_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return metadata
    except Exception:
        if UNIVERSE_CACHE_PATH.exists():
            return json.loads(UNIVERSE_CACHE_PATH.read_text(encoding="utf-8"))
        for csv_path in [FEATURE_CACHE_PATH, RAW_CACHE_PATH]:
            if csv_path.exists():
                try:
                    frame = pd.read_csv(csv_path, usecols=["Ticker"])
                    tickers = sorted({str(value).strip() for value in frame["Ticker"].dropna().tolist()})
                    if tickers:
                        return [
                            {
                                "symbol": ticker.replace(".NS", ""),
                                "ticker": ticker,
                                "company_name": ticker.replace(".NS", ""),
                                "sector": "Unknown",
                            }
                            for ticker in tickers
                        ]
                except Exception:
                    continue
        return BOOTSTRAP_UNIVERSE


def get_ticker_list() -> list[str]:
    """Return yfinance-formatted tickers."""
    return [item["ticker"] for item in get_nifty500_metadata()]


def get_stock_lookup() -> dict[str, dict[str, Any]]:
    """Return a ticker lookup with a simple cap bucket."""
    lookup: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(get_nifty500_metadata()):
        cap = "Large Cap" if index < 100 else "Mid Cap" if index < 250 else "Small Cap"
        lookup[item["ticker"]] = {**item, "market_cap_category": cap}
    return lookup
