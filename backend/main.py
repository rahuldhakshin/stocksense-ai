"""FastAPI backend for the Indian Stock Market Analytics platform."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
from cachetools import TTLCache
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from market_utils import compute_support_resistance, engineer_features, fetch_featured_history, fetch_history, safe_float
from ml_model import load_training_metrics, model_artifacts_ready, predict_next_price
from stock_universe import get_stock_lookup

app = FastAPI(title="Indian Stock Market Analytics API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stock_lookup = get_stock_lookup()
market_cache: TTLCache[str, Any] = TTLCache(maxsize=128, ttl=1800)

INDEX_MAP = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Nifty Bank": "^NSEBANK",
    "Nifty IT": "^CNXIT",
    "Nifty Pharma": "^CNXPHARMA",
}


class Holding(BaseModel):
    ticker: str
    quantity: int
    avg_buy_price: float


class PortfolioRequest(BaseModel):
    holdings: list[Holding]


def _cached_get(key: str) -> Any:
    return market_cache.get(key)


def _cached_set(key: str, value: Any) -> None:
    market_cache[key] = value


def _history_or_404(ticker: str, period: str = "1y") -> pd.DataFrame:
    history = fetch_featured_history(ticker, period=period, dropna=True)
    if history.empty:
        raise HTTPException(status_code=404, detail={"error": f"No data found for {ticker}"})
    return history


def _analysis_payload(ticker: str) -> dict[str, Any]:
    history = _history_or_404(ticker, period="1y")
    latest = history.iloc[-1]
    last_week = history.iloc[max(0, len(history) - 6)]
    last_month = history.iloc[max(0, len(history) - 22)]

    current = safe_float(latest["Close"])
    day_change_pct = safe_float(latest["Daily_Return"])
    week_change_pct = ((current - safe_float(last_week["Close"])) / safe_float(last_week["Close"], 1.0)) * 100
    month_change_pct = ((current - safe_float(last_month["Close"])) / safe_float(last_month["Close"], 1.0)) * 100

    rsi = safe_float(latest["RSI_14"])
    rsi_state = "overbought" if rsi >= 70 else "oversold" if rsi <= 30 else "neutral"
    macd_signal = "bullish crossover" if safe_float(latest["MACD"]) > safe_float(latest["MACD_Signal"]) else "bearish crossover"
    bb_position = (
        "above bands"
        if current > safe_float(latest["BB_Upper"])
        else "below bands"
        if current < safe_float(latest["BB_Lower"])
        else "within bands"
    )

    volume_avg = safe_float(latest["Volume_SMA_20"], 1.0)
    volume_status = "above average" if safe_float(latest["Volume"]) > volume_avg else "below average"
    support_resistance = compute_support_resistance(history)

    bull_score = 0
    bull_score += 1 if day_change_pct > 0 else -1
    bull_score += 1 if macd_signal.startswith("bullish") else -1
    bull_score += 1 if rsi_state == "neutral" else -1 if rsi_state == "overbought" else 1
    bull_score += 1 if volume_status == "above average" and day_change_pct > 0 else 0

    sentiment = "Bullish" if bull_score >= 2 else "Bearish" if bull_score <= -2 else "Neutral"
    confidence = max(0, min(100, 55 + bull_score * 10 + min(abs(day_change_pct), 8) * 3))

    return {
        "ticker": ticker.upper(),
        "current_price": round(current, 2),
        "day_change_pct": round(day_change_pct, 2),
        "week_change_pct": round(week_change_pct, 2),
        "month_change_pct": round(month_change_pct, 2),
        "fifty_two_week_high": round(safe_float(history["High"].max()), 2),
        "fifty_two_week_low": round(safe_float(history["Low"].min()), 2),
        "rsi": {"value": round(rsi, 2), "interpretation": rsi_state},
        "macd": {"value": round(safe_float(latest["MACD"]), 2), "signal": macd_signal},
        "bollinger_position": bb_position,
        "volume_analysis": {
            "status": volume_status,
            "current": round(safe_float(latest["Volume"]), 2),
            "average_20d": round(volume_avg, 2),
        },
        "support_resistance": support_resistance,
        "overall_sentiment": sentiment,
        "confidence_score": round(confidence, 2),
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "models_loaded": model_artifacts_ready(), "total_stocks": len(stock_lookup)}


@app.get("/api/stocks/list")
def stock_list() -> list[dict[str, Any]]:
    return list(stock_lookup.values())


@app.get("/api/stock/{ticker}/history")
def stock_history(ticker: str, period: str = Query("1y", pattern="^(1mo|3mo|6mo|1y|3y|5y|10y)$")) -> dict[str, Any]:
    try:
        raw_history = fetch_history(ticker, period=period)
        if raw_history.empty:
            raise HTTPException(status_code=404, detail={"error": f"No data found for {ticker}"})
        history = engineer_features(raw_history)
        data = [
            {
                "date": row["Date"].strftime("%Y-%m-%d"),
                "open": safe_float(row["Open"]),
                "high": safe_float(row["High"]),
                "low": safe_float(row["Low"]),
                "close": safe_float(row["Close"]),
                "volume": safe_float(row["Volume"]),
                "sma_20": safe_float(row["SMA_20"]),
                "sma_50": safe_float(row["SMA_50"]),
                "bb_upper": safe_float(row["BB_Upper"]),
                "bb_lower": safe_float(row["BB_Lower"]),
                "rsi": safe_float(row["RSI_14"]),
            }
            for _, row in history.iterrows()
        ]
        latest_valid = history.dropna(subset=["RSI_14", "MACD", "SMA_20", "SMA_50", "BB_Upper", "BB_Lower"])
        latest = latest_valid.iloc[-1] if not latest_valid.empty else history.iloc[-1]
        return {
            "ticker": ticker.upper(),
            "data": data,
            "indicators": {
                "rsi": safe_float(latest["RSI_14"]),
                "macd": safe_float(latest["MACD"]),
                "sma_20": safe_float(latest["SMA_20"]),
                "sma_50": safe_float(latest["SMA_50"]),
                "bb_upper": safe_float(latest["BB_Upper"]),
                "bb_lower": safe_float(latest["BB_Lower"]),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


@app.get("/api/stock/{ticker}/predict")
def stock_predict(ticker: str, model: str = Query("rf", pattern="^(rf|gb)$")) -> dict[str, Any]:
    try:
        if not model_artifacts_ready():
            return {"error": "Models not ready", "models_loaded": False}
        return predict_next_price(ticker, model_type=model)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


@app.get("/api/stock/{ticker}/analysis")
def stock_analysis(ticker: str) -> dict[str, Any]:
    try:
        return _analysis_payload(ticker)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


@app.get("/api/market/overview")
def market_overview() -> dict[str, Any]:
    try:
        cached = _cached_get("market_overview")
        if cached is not None:
            return cached

        payload: dict[str, Any] = {}
        for name, ticker in INDEX_MAP.items():
            history = fetch_history(ticker, period="1y")
            if history.empty:
                continue
            latest = history.iloc[-1]
            previous = history.iloc[-2] if len(history) > 1 else latest
            day_change = safe_float(latest["Close"]) - safe_float(previous["Close"])
            day_change_pct = (day_change / safe_float(previous["Close"], 1.0)) * 100
            payload[name] = {
                "ticker": ticker,
                "current_value": round(safe_float(latest["Close"]), 2),
                "day_change": round(day_change, 2),
                "day_change_pct": round(day_change_pct, 2),
                "fifty_two_week_high": round(safe_float(history["High"].max()), 2),
                "fifty_two_week_low": round(safe_float(history["Low"].min()), 2),
            }
        _cached_set("market_overview", payload)
        return payload
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


def _compute_top_movers() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for ticker in list(stock_lookup.keys())[: min(len(stock_lookup), 500)]:
        history = fetch_history(ticker, period="5d")
        if len(history) < 2:
            continue
        latest = history.iloc[-1]
        previous = history.iloc[-2]
        previous_close = safe_float(previous["Close"], 1.0)
        change_pct = ((safe_float(latest["Close"]) - previous_close) / previous_close) * 100
        rows.append(
            {
                "ticker": ticker,
                "name": stock_lookup.get(ticker, {}).get("company_name", ticker),
                "close": round(safe_float(latest["Close"]), 2),
                "change_pct": round(change_pct, 2),
            }
        )
    sorted_rows = sorted(rows, key=lambda item: item["change_pct"], reverse=True)
    return {"gainers": sorted_rows[:5], "losers": list(reversed(sorted_rows[-5:]))}


@app.get("/api/market/top-movers")
def market_top_movers(background_tasks: BackgroundTasks) -> dict[str, Any]:
    try:
        cached = _cached_get("top_movers")
        if cached is None:
            cached = _compute_top_movers()
            _cached_set("top_movers", cached)
            background_tasks.add_task(_cached_set, "top_movers", cached)
        return cached
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


@app.get("/api/market/sector-performance")
def sector_performance() -> list[dict[str, Any]]:
    try:
        cached = _cached_get("sector_performance")
        if cached is not None:
            return cached

        sector_map: dict[str, list[float]] = {}
        for ticker, meta in stock_lookup.items():
            history = fetch_history(ticker, period="5d")
            if len(history) < 2:
                continue
            previous = safe_float(history.iloc[-2]["Close"], 1.0)
            today = safe_float(history.iloc[-1]["Close"])
            change_pct = ((today - previous) / previous) * 100
            sector_map.setdefault(meta.get("sector", "Unknown"), []).append(change_pct)

        ranked = sorted(
            [{"sector": sector, "avg_return_pct": round(sum(values) / len(values), 2), "count": len(values)} for sector, values in sector_map.items()],
            key=lambda item: item["avg_return_pct"],
            reverse=True,
        )
        _cached_set("sector_performance", ranked)
        return ranked
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


@app.get("/api/stock/{ticker}/compare")
def compare_stocks(ticker: str, with_: str = Query(..., alias="with")) -> dict[str, Any]:
    try:
        tickers = [ticker] + [item.strip() for item in with_.split(",") if item.strip()]
        result: dict[str, list[dict[str, Any]]] = {}
        for symbol in tickers:
            history = fetch_history(symbol, period="1y")
            if history.empty:
                continue
            base = safe_float(history.iloc[0]["Close"], 1.0)
            result[symbol.upper()] = [
                {"date": row["Date"].strftime("%Y-%m-%d"), "value": round((safe_float(row["Close"]) / base) * 100, 2)}
                for _, row in history.iterrows()
            ]
        return {"base": 100, "series": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


@app.post("/api/portfolio/analyze")
def analyze_portfolio(payload: PortfolioRequest) -> dict[str, Any]:
    try:
        holdings_data: list[dict[str, Any]] = []
        allocation: list[dict[str, Any]] = []
        total_invested = 0.0
        current_value = 0.0
        volatilities: list[float] = []

        for holding in payload.holdings:
            history = _history_or_404(holding.ticker, period="1y")
            latest = history.iloc[-1]
            cmp_price = safe_float(latest["Close"])
            invested = holding.quantity * holding.avg_buy_price
            current = holding.quantity * cmp_price
            pnl = current - invested
            total_invested += invested
            current_value += current
            volatilities.append(safe_float(latest["Volatility_20"]))

            prediction = {"direction": "HOLD", "confidence": 0.0}
            if model_artifacts_ready():
                try:
                    prediction = predict_next_price(holding.ticker)
                except Exception:
                    pass

            holdings_data.append(
                {
                    "ticker": holding.ticker.upper(),
                    "quantity": holding.quantity,
                    "avg_buy_price": round(holding.avg_buy_price, 2),
                    "cmp": round(cmp_price, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round((pnl / invested) * 100, 2) if invested else 0.0,
                    "signal": prediction["direction"],
                }
            )
            allocation.append({"name": holding.ticker.upper(), "value": round(current, 2)})

        pnl_total = current_value - total_invested
        pnl_pct = (pnl_total / total_invested) * 100 if total_invested else 0.0
        avg_vol = sum(volatilities) / len(volatilities) if volatilities else 0.0
        risk_label = "Low" if avg_vol < 1.5 else "Medium" if avg_vol < 3.0 else "High"

        return {
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "pnl": round(pnl_total, 2),
            "pnl_pct": round(pnl_pct, 2),
            "allocation": allocation,
            "risk_score": {"label": risk_label, "volatility": round(avg_vol, 2)},
            "holdings": holdings_data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)}) from exc


@app.get("/api/models/metrics")
def model_metrics() -> dict[str, Any]:
    return load_training_metrics()
