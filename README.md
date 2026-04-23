# StockSense AI

Production-style Indian Stock Market Analytics & Prediction platform built with FastAPI, scikit-learn, React, Vite, Recharts, TailwindCSS, SQLite, and yfinance.

## Features

- Nifty 500 stock universe with metadata caching and offline bootstrap fallback
- Resumable 10-year OHLCV pipeline with SQLite persistence and CSV exports
- Technical indicators: SMA, EMA, MACD, RSI, Bollinger Bands, ATR, OBV, ROC, stochastic, volatility
- Dual ML models for next-day price prediction with saved metrics and artifacts
- FastAPI endpoints for market overview, history, predictions, analysis, sector performance, comparisons, and portfolio analytics
- Dark trading-terminal frontend with dashboard, stock analysis, prediction panel, portfolio analysis, and sector heatmap
- Demo mode via CSV cache when live yfinance calls fail

## Setup

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
mkdir -p data models
python data_pipeline.py
python ml_model.py
cd backend && uvicorn main:app --reload --port 8000
cd frontend && npm run dev
```

You can also run:

```bash
bash setup.sh
bash run.sh
```

## Data Pipeline

- `data_pipeline.py` fetches 10 years of daily OHLCV data for the stock universe
- Saves raw combined data to `data/all_stocks_10yr.csv`
- Saves engineered features to `data/all_stocks_features.csv`
- Saves full data cache to `data/stocks.db` in table `stock_data`
- Skips already-cached tickers in SQLite for resumability

## Machine Learning

- `ml_model.py` trains:
  - `RandomForestRegressor`
  - `GradientBoostingRegressor`
- Uses `TimeSeriesSplit(n_splits=5)`
- Saves:
  - `models/rf_model.pkl`
  - `models/gb_model.pkl`
  - `models/scaler.pkl`
  - `models/feature_columns.json`
  - `models/training_metrics.json`

## API Endpoints

- `GET /api/health`
- `GET /api/stocks/list`
- `GET /api/stock/{ticker}/history?period=1y`
- `GET /api/stock/{ticker}/predict?model=rf`
- `GET /api/stock/{ticker}/analysis`
- `GET /api/market/overview`
- `GET /api/market/top-movers`
- `GET /api/market/sector-performance`
- `GET /api/stock/{ticker}/compare?with=TCS.NS,INFY.NS`
- `POST /api/portfolio/analyze`

## Architecture

```text
                 +----------------------+
                 |   React + Vite UI    |
                 | Recharts + Tailwind  |
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |    FastAPI Backend   |
                 |  cachetools + CORS   |
                 +----+-----------+-----+
                      |           |
                      v           v
            +----------------+  +-------------------+
            | ML Artifacts   |  | Market Utilities  |
            | RF / GB / Scaler| | yfinance + ta     |
            +-------+--------+  +---------+---------+
                    |                     |
                    v                     v
               +-----------------------------------+
               | SQLite + CSV cache + Data Pipeline|
               | 10y OHLCV + engineered indicators |
               +-----------------------------------+
```

## Screenshots

- Dashboard screenshot placeholder
- Stock analysis screenshot placeholder
- Portfolio screenshot placeholder

## Tech Stack

- Backend: FastAPI, Uvicorn, SQLAlchemy
- ML: scikit-learn, pandas, numpy, ta, xgboost
- Frontend: React 18, Vite, Recharts, TailwindCSS
- Data: yfinance, SQLite
