"""Model training and inference for next-day stock prediction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from data_pipeline import fetch_single_stock
from market_utils import directional_accuracy, safe_float

try:
    from xgboost import XGBClassifier, XGBRegressor
except Exception:  # pragma: no cover - optional at runtime
    XGBClassifier = None
    XGBRegressor = None

MODELS_DIR = Path(__file__).resolve().parent / "models"
DATA_PATH = Path(__file__).resolve().parent / "data" / "all_stocks_features.csv"
RF_MODEL_PATH = MODELS_DIR / "rf_model.pkl"
GB_MODEL_PATH = MODELS_DIR / "gb_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.json"
TRAINING_METRICS_PATH = MODELS_DIR / "training_metrics.json"

FEATURE_COLUMNS = [
    "Open", "High", "Low", "Close", "Volume", "SMA_20", "SMA_50", "SMA_200",
    "EMA_12", "EMA_26", "MACD", "MACD_Signal", "RSI_14", "BB_Upper", "BB_Lower",
    "ATR_14", "OBV", "ROC_10", "Stochastic_K", "Daily_Return", "Volatility_20",
    "Volume_SMA_20", "Price_to_SMA50_ratio", "Gap_Pct", "Intraday_Range_Pct",
    "Return_Lag_1", "Return_Lag_3", "Return_Lag_5", "Return_Lag_10",
    "Close_Lag_1", "Close_Lag_3", "Close_Lag_5", "Momentum_21",
    "Volume_Ratio_20", "Trend_Strength", "RSI_Slope_3",
]
TARGET_COLUMN = "Target"
MODEL_CONFIG_PATH = MODELS_DIR / "model_config.json"


def load_training_data() -> pd.DataFrame:
    """Load and sort the engineered training data."""
    if not DATA_PATH.exists():
        raise FileNotFoundError("Training dataset not found. Run data_pipeline.py first.")
    frame = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    frame = frame.sort_values(["Date", "Ticker"]).dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN]).reset_index(drop=True)
    return frame


def _build_metrics(actual: pd.Series, predicted: np.ndarray, previous_close: pd.Series) -> dict[str, float]:
    """Compute regression metrics and directional accuracy."""
    return {
        "RMSE": float(np.sqrt(mean_squared_error(actual, predicted))),
        "MAE": float(mean_absolute_error(actual, predicted)),
        "R2": float(r2_score(actual, predicted)),
        "directional_accuracy": directional_accuracy(actual, pd.Series(predicted, index=actual.index), previous_close),
    }


def _actionable_accuracy(
    actual: pd.Series,
    predicted: pd.Series,
    current_close: pd.Series,
    probabilities: np.ndarray,
    fixed_threshold: float | None = None,
) -> dict[str, float]:
    """Measure signal accuracy only on high-confidence actionable predictions."""
    actual_move = ((actual - current_close) / current_close.replace(0, np.nan)) * 100
    predicted_move = ((predicted - current_close) / current_close.replace(0, np.nan)) * 100
    confidence = np.max(probabilities, axis=1) * 100 if probabilities.size else np.zeros(len(actual))

    thresholds = [int(fixed_threshold)] if fixed_threshold is not None else list(range(55, 91))
    best_threshold = float(fixed_threshold or 60.0)
    best_accuracy = 0.0
    best_coverage = 0.0
    for threshold in thresholds:
        mask = confidence >= threshold
        signal_mask = mask & (predicted_move.abs() >= 1.0)
        if fixed_threshold is None and signal_mask.sum() < max(25, int(len(actual) * 0.03)):
            continue
        actual_dir = np.sign(actual_move[signal_mask].to_numpy())
        predicted_dir = np.sign(predicted_move[signal_mask].to_numpy())
        accuracy = float((actual_dir == predicted_dir).mean() * 100) if len(actual_dir) else 0.0
        coverage = float(signal_mask.mean() * 100)
        score = accuracy + min(coverage, 35.0) * 0.1
        if fixed_threshold is not None or score > best_accuracy + best_coverage * 0.1:
            best_threshold = float(threshold)
            best_accuracy = accuracy
            best_coverage = coverage
    return {
        "actionable_accuracy": round(best_accuracy, 2),
        "actionable_coverage": round(best_coverage, 2),
        "confidence_threshold": round(best_threshold, 2),
    }


def _build_regressor(model_type: str):
    """Build the requested regressor."""
    if model_type == "rf":
        return RandomForestRegressor(n_estimators=300, max_depth=18, min_samples_leaf=2, n_jobs=-1, random_state=42)
    if XGBRegressor is not None:
        return XGBRegressor(
            n_estimators=350,
            max_depth=6,
            learning_rate=0.03,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.1,
            reg_lambda=1.0,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=4,
        )
    return GradientBoostingRegressor(n_estimators=250, learning_rate=0.04, max_depth=5, random_state=42)


def _build_classifier(model_type: str):
    """Build the requested direction classifier."""
    if model_type == "rf":
        return RandomForestClassifier(
            n_estimators=300,
            max_depth=14,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=42,
        )
    if XGBClassifier is not None:
        return XGBClassifier(
            n_estimators=320,
            max_depth=5,
            learning_rate=0.04,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            random_state=42,
            n_jobs=4,
        )
    return RandomForestClassifier(
        n_estimators=220,
        max_depth=12,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )


def fit_models() -> dict[str, dict[str, float]]:
    """Train both models, evaluate them, and save artifacts."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    frame = load_training_data()
    X = frame[FEATURE_COLUMNS]
    y = frame[TARGET_COLUMN]
    previous_close = frame["Close"]
    y_direction = (y > previous_close).astype(int)

    split_index = int(len(frame) * 0.8)
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]
    close_test = previous_close.iloc[split_index:]
    y_direction_train, y_direction_test = y_direction.iloc[:split_index], y_direction.iloc[split_index:]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    rf_model = _build_regressor("rf")
    gb_model = _build_regressor("gb")
    rf_classifier = _build_classifier("rf")
    gb_classifier = _build_classifier("gb")

    cv_store = {
        "rf": {"pred": pd.Series(index=y_train.index, dtype=float), "prob": {}},
        "gb": {"pred": pd.Series(index=y_train.index, dtype=float), "prob": {}},
    }

    tscv = TimeSeriesSplit(n_splits=5)
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X_train_scaled), start=1):
        for key, regressor, classifier in [("rf", rf_model, rf_classifier), ("gb", gb_model, gb_classifier)]:
            regressor.fit(X_train_scaled[train_idx], y_train.iloc[train_idx])
            classifier.fit(X_train_scaled[train_idx], y_direction_train.iloc[train_idx])
            cv_store[key]["pred"].iloc[val_idx] = regressor.predict(X_train_scaled[val_idx])
            probabilities = classifier.predict_proba(X_train_scaled[val_idx])
            for offset, frame_index in enumerate(y_train.iloc[val_idx].index):
                cv_store[key]["prob"][frame_index] = probabilities[offset]
        print(f"Completed CV fold {fold}/5")

    rf_model.fit(X_train_scaled, y_train)
    gb_model.fit(X_train_scaled, y_train)
    rf_classifier.fit(X_train_scaled, y_direction_train)
    gb_classifier.fit(X_train_scaled, y_direction_train)

    rf_predictions = rf_model.predict(X_test_scaled)
    gb_predictions = gb_model.predict(X_test_scaled)
    rf_probabilities = rf_classifier.predict_proba(X_test_scaled)
    gb_probabilities = gb_classifier.predict_proba(X_test_scaled)
    rf_cv_probabilities = np.array([cv_store["rf"]["prob"][index] for index in y_train.index if index in cv_store["rf"]["prob"]])
    gb_cv_probabilities = np.array([cv_store["gb"]["prob"][index] for index in y_train.index if index in cv_store["gb"]["prob"]])
    rf_cv_actual = y_train.loc[cv_store["rf"]["pred"].dropna().index]
    gb_cv_actual = y_train.loc[cv_store["gb"]["pred"].dropna().index]
    rf_cv_close = previous_close.loc[rf_cv_actual.index]
    gb_cv_close = previous_close.loc[gb_cv_actual.index]
    rf_signal_profile = _actionable_accuracy(rf_cv_actual, cv_store["rf"]["pred"].dropna(), rf_cv_close, rf_cv_probabilities)
    gb_signal_profile = _actionable_accuracy(gb_cv_actual, cv_store["gb"]["pred"].dropna(), gb_cv_close, gb_cv_probabilities)

    metrics = {
        "random_forest": {
            **_build_metrics(y_test, rf_predictions, close_test),
            **_actionable_accuracy(
                y_test,
                pd.Series(rf_predictions, index=y_test.index),
                close_test,
                rf_probabilities,
                fixed_threshold=rf_signal_profile["confidence_threshold"],
            ),
            "direction_classifier_accuracy": round(float((rf_classifier.predict(X_test_scaled) == y_direction_test).mean() * 100), 2),
            "cv_confidence_threshold": rf_signal_profile["confidence_threshold"],
            "cv_actionable_accuracy": rf_signal_profile["actionable_accuracy"],
            "cv_actionable_coverage": rf_signal_profile["actionable_coverage"],
        },
        "gradient_boosting": {
            **_build_metrics(y_test, gb_predictions, close_test),
            **_actionable_accuracy(
                y_test,
                pd.Series(gb_predictions, index=y_test.index),
                close_test,
                gb_probabilities,
                fixed_threshold=gb_signal_profile["confidence_threshold"],
            ),
            "direction_classifier_accuracy": round(float((gb_classifier.predict(X_test_scaled) == y_direction_test).mean() * 100), 2),
            "cv_confidence_threshold": gb_signal_profile["confidence_threshold"],
            "cv_actionable_accuracy": gb_signal_profile["actionable_accuracy"],
            "cv_actionable_coverage": gb_signal_profile["actionable_coverage"],
        },
    }

    joblib.dump(rf_model, RF_MODEL_PATH)
    joblib.dump(gb_model, GB_MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(rf_classifier, MODELS_DIR / "rf_classifier.pkl")
    joblib.dump(gb_classifier, MODELS_DIR / "gb_classifier.pkl")
    FEATURE_COLUMNS_PATH.write_text(json.dumps(FEATURE_COLUMNS, indent=2), encoding="utf-8")
    TRAINING_METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    MODEL_CONFIG_PATH.write_text(
        json.dumps(
            {
                "rf": {"confidence_threshold": metrics["random_forest"]["cv_confidence_threshold"]},
                "gb": {"confidence_threshold": metrics["gradient_boosting"]["cv_confidence_threshold"]},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2))
    return metrics


def model_artifacts_ready() -> bool:
    """Return whether prediction artifacts are available."""
    return all(
        path.exists()
        for path in [RF_MODEL_PATH, GB_MODEL_PATH, SCALER_PATH, FEATURE_COLUMNS_PATH, MODELS_DIR / "rf_classifier.pkl", MODELS_DIR / "gb_classifier.pkl"]
    )


def _load_model_bundle(model_type: str = "rf") -> tuple[Any, Any, StandardScaler, list[str], dict[str, Any]]:
    """Load model, classifier, scaler, feature columns, and config."""
    if not model_artifacts_ready():
        raise FileNotFoundError("Models not trained yet.")
    model = joblib.load(RF_MODEL_PATH if model_type == "rf" else GB_MODEL_PATH)
    classifier = joblib.load(MODELS_DIR / ("rf_classifier.pkl" if model_type == "rf" else "gb_classifier.pkl"))
    scaler: StandardScaler = joblib.load(SCALER_PATH)
    features = json.loads(FEATURE_COLUMNS_PATH.read_text(encoding="utf-8"))
    config = json.loads(MODEL_CONFIG_PATH.read_text(encoding="utf-8")) if MODEL_CONFIG_PATH.exists() else {}
    return model, classifier, scaler, features, config


def load_training_metrics() -> dict[str, Any]:
    """Load persisted training metrics."""
    if not TRAINING_METRICS_PATH.exists():
        return {}
    return json.loads(TRAINING_METRICS_PATH.read_text(encoding="utf-8"))


def predict_next_price(ticker: str, model_type: str = "rf") -> dict[str, Any]:
    """Predict the next day's close price for a ticker."""
    model_key = "rf" if model_type != "gb" else "gb"
    model, classifier, scaler, features, config = _load_model_bundle(model_key)
    latest_df = fetch_single_stock(ticker, period="10y")
    if latest_df.empty:
        raise ValueError(f"No price history available for {ticker}")

    current_price = safe_float(latest_df.iloc[-1]["Close"])
    X_scaled = scaler.transform(latest_df[features].iloc[[-1]])
    predicted_price = safe_float(model.predict(X_scaled)[0])
    predicted_change_pct = ((predicted_price - current_price) / current_price * 100) if current_price else 0.0
    class_probabilities = classifier.predict_proba(X_scaled)[0]
    class_confidence = safe_float(np.max(class_probabilities) * 100)
    threshold = safe_float(config.get(model_key, {}).get("confidence_threshold"), 60.0)

    if class_confidence < threshold or abs(predicted_change_pct) < 1.0:
        direction = "HOLD"
    else:
        direction = "BUY" if predicted_change_pct > 0 else "SELL"
    metrics = load_training_metrics()
    saved = metrics.get("random_forest" if model_key == "rf" else "gradient_boosting", {})
    actionable_acc = safe_float(saved.get("actionable_accuracy"), safe_float(saved.get("directional_accuracy"), 50.0))
    confidence = max(0.0, min(100.0, class_confidence * 0.7 + actionable_acc * 0.3))

    feature_importance: dict[str, float] = {}
    if hasattr(model, "feature_importances_"):
        pairs = sorted(zip(features, getattr(model, "feature_importances_")), key=lambda item: item[1], reverse=True)[:8]
        feature_importance = {name: round(float(value), 4) for name, value in pairs}

    return {
        "ticker": ticker.upper(),
        "current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "predicted_change_pct": round(predicted_change_pct, 2),
        "direction": direction,
        "confidence": round(confidence, 2),
        "model": "Random Forest" if model_key == "rf" else "Gradient Boosting",
        "feature_importance": feature_importance,
        "signal_threshold": round(threshold, 2),
    }


if __name__ == "__main__":
    fit_models()
