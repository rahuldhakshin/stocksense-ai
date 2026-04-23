# StockSense AI

StockSense AI is an Indian stock market analytics project I built to explore the full pipeline from market-data ingestion to feature engineering, model training, API development, and frontend visualization.

It combines FastAPI, scikit-learn, React, Vite, Recharts, TailwindCSS, SQLite, and yfinance in one end-to-end app.

## Why I Built This

I wanted to build something that was more than just a notebook model. The goal was to put together:

- a resumable market-data pipeline
- a feature engineering workflow with technical indicators
- a simple but usable prediction layer
- a frontend that makes the analysis easier to explore

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

## Notes

- The repo does not include generated datasets, SQLite caches, or trained model artifacts.
- You need to run the data pipeline and model training locally before prediction endpoints will return model outputs.
- This project is for learning and exploration, not financial advice.

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

I have not added screenshots yet. I plan to add:

- dashboard view
- stock analysis screen
- portfolio analysis screen

## Known Limitations

- Market data depends on `yfinance`, so live fetches can fail or be rate-limited.
- The prediction system is a learning project and should not be treated as a real trading signal.
- Some market endpoints can be slow on first load because they compute live summaries across many tickers.

## Tech Stack

- Backend: FastAPI, Uvicorn, SQLAlchemy
- ML: scikit-learn, pandas, numpy, ta, xgboost
- Frontend: React 18, Vite, Recharts, TailwindCSS
- Data: yfinance, SQLite
