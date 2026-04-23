"""Shared market data utilities."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
from ta.momentum import ROCIndicator, RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands
from ta.volume import OnBalanceVolumeIndicator

DATA_DIR = Path(__file__).resolve().parent / "data"
RAW_CACHE_PATH = DATA_DIR / "all_stocks_10yr.csv"
FEATURE_CACHE_PATH = DATA_DIR / "all_stocks_features.csv"


def normalize_ticker(ticker: str) -> str:
    """Normalize a ticker to yfinance NSE format."""
    value = ticker.strip().upper()
    if value.startswith("^"):
        return value
    if "." not in value:
        return f"{value}.NS"
    return value


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer technical indicators on top of OHLCV data."""
    frame = df.copy().sort_values("Date").reset_index(drop=True)
    if frame.empty:
        return frame

    frame["SMA_20"] = SMAIndicator(close=frame["Close"], window=20).sma_indicator()
    frame["SMA_50"] = SMAIndicator(close=frame["Close"], window=50).sma_indicator()
    frame["SMA_200"] = SMAIndicator(close=frame["Close"], window=200).sma_indicator()
    frame["EMA_12"] = EMAIndicator(close=frame["Close"], window=12).ema_indicator()
    frame["EMA_26"] = EMAIndicator(close=frame["Close"], window=26).ema_indicator()

    macd = MACD(close=frame["Close"], window_fast=12, window_slow=26, window_sign=9)
    frame["MACD"] = macd.macd()
    frame["MACD_Signal"] = macd.macd_signal()
    frame["MACD_Histogram"] = macd.macd_diff()

    frame["RSI_14"] = RSIIndicator(close=frame["Close"], window=14).rsi()
    bands = BollingerBands(close=frame["Close"], window=20, window_dev=2)
    frame["BB_Upper"] = bands.bollinger_hband()
    frame["BB_Middle"] = bands.bollinger_mavg()
    frame["BB_Lower"] = bands.bollinger_lband()
    frame["ATR_14"] = AverageTrueRange(high=frame["High"], low=frame["Low"], close=frame["Close"], window=14).average_true_range()
    frame["OBV"] = OnBalanceVolumeIndicator(close=frame["Close"], volume=frame["Volume"]).on_balance_volume()
    frame["ROC_10"] = ROCIndicator(close=frame["Close"], window=10).roc()

    stochastic = StochasticOscillator(high=frame["High"], low=frame["Low"], close=frame["Close"], window=14, smooth_window=3)
    frame["Stochastic_K"] = stochastic.stoch()
    frame["Stochastic_D"] = stochastic.stoch_signal()
    frame["Daily_Return"] = frame["Close"].pct_change() * 100
    frame["Volatility_20"] = frame["Daily_Return"].rolling(20).std()
    frame["Volume_SMA_20"] = frame["Volume"].rolling(20).mean()
    frame["Price_to_SMA50_ratio"] = frame["Close"] / frame["SMA_50"]
    frame["Gap_Pct"] = ((frame["Open"] - frame["Close"].shift(1)) / frame["Close"].shift(1)) * 100
    frame["Intraday_Range_Pct"] = ((frame["High"] - frame["Low"]) / frame["Close"].replace(0, np.nan)) * 100
    frame["Return_Lag_1"] = frame["Daily_Return"].shift(1)
    frame["Return_Lag_3"] = frame["Daily_Return"].shift(3)
    frame["Return_Lag_5"] = frame["Daily_Return"].shift(5)
    frame["Return_Lag_10"] = frame["Daily_Return"].shift(10)
    frame["Close_Lag_1"] = frame["Close"].shift(1)
    frame["Close_Lag_3"] = frame["Close"].shift(3)
    frame["Close_Lag_5"] = frame["Close"].shift(5)
    frame["Momentum_21"] = ((frame["Close"] / frame["Close"].shift(21)) - 1) * 100
    frame["Volume_Ratio_20"] = frame["Volume"] / frame["Volume_SMA_20"]
    frame["Trend_Strength"] = (frame["SMA_20"] - frame["SMA_50"]) / frame["SMA_50"]
    frame["RSI_Slope_3"] = frame["RSI_14"] - frame["RSI_14"].shift(3)
    frame["Target"] = frame["Close"].shift(-1)
    frame.replace([np.inf, -np.inf], np.nan, inplace=True)
    return frame


def _flatten_download(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Flatten yfinance responses into a standard schema."""
    frame = df.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.reset_index().rename(columns={"index": "Date"})
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize(None)
    frame["Ticker"] = ticker
    return frame[["Date", "Ticker", "Open", "High", "Low", "Close", "Volume"]]


def load_cached_stock_from_csv(ticker: str) -> pd.DataFrame:
    """Load a ticker from local CSV cache."""
    normalized = normalize_ticker(ticker)
    for path in [FEATURE_CACHE_PATH, RAW_CACHE_PATH]:
        if path.exists():
            try:
                frame = pd.read_csv(path, parse_dates=["Date"])
                cached = frame[frame["Ticker"] == normalized].copy()
                if not cached.empty:
                    return cached.sort_values("Date").reset_index(drop=True)
            except Exception:
                continue
    return pd.DataFrame()


def fetch_history(ticker: str, period: str = "1y", interval: str = "1d", prefer_cache: bool = True) -> pd.DataFrame:
    """Fetch history from yfinance with CSV fallback."""
    normalized = normalize_ticker(ticker)
    try:
        downloaded = yf.download(normalized, period=period, interval=interval, progress=False, auto_adjust=False, threads=False)
        if downloaded is not None and not downloaded.empty:
            return _flatten_download(downloaded, normalized)
    except Exception:
        pass
    return load_cached_stock_from_csv(normalized) if prefer_cache else pd.DataFrame()


def fetch_featured_history(ticker: str, period: str = "1y", dropna: bool = True) -> pd.DataFrame:
    """Fetch and feature-engineer a ticker history."""
    history = fetch_history(ticker=ticker, period=period)
    if history.empty:
        return history
    featured = engineer_features(history)
    if dropna:
        featured = featured.dropna()
    return featured.reset_index(drop=True)


def compute_support_resistance(df: pd.DataFrame, window: int = 5) -> dict[str, list[float]]:
    """Return recent swing supports and resistances."""
    if df.empty or len(df) < window * 2 + 1:
        return {"support": [], "resistance": []}
    highs: list[float] = []
    lows: list[float] = []
    for idx in range(window, len(df) - window):
        if df["High"].iloc[idx] == df["High"].iloc[idx - window : idx + window + 1].max():
            highs.append(round(float(df["High"].iloc[idx]), 2))
        if df["Low"].iloc[idx] == df["Low"].iloc[idx - window : idx + window + 1].min():
            lows.append(round(float(df["Low"].iloc[idx]), 2))
    return {"support": lows[-3:], "resistance": highs[-3:]}


def directional_accuracy(actual: pd.Series, predicted: pd.Series, previous_close: pd.Series) -> float:
    """Calculate directional prediction accuracy."""
    actual_direction = np.sign(actual.to_numpy() - previous_close.to_numpy())
    predicted_direction = np.sign(predicted.to_numpy() - previous_close.to_numpy())
    return float((actual_direction == predicted_direction).mean() * 100) if len(actual_direction) else 0.0


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert values to finite floats safe for JSON serialization."""
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except Exception:
        return default
