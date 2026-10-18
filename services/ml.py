"""CPU models with chronological validation and cutoff-specific local artifacts.

Only train_models() fits estimators. Web requests load artifacts and predict.
"""

import json
import math
import os
import tempfile
from datetime import timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, IsolationForest
from sklearn.metrics import mean_absolute_error

from models import StockMovement
from services.inventory import cutoff_end, items_at, stock_at

MIN_DAYS = 45
HORIZON = 90


def daily_consumption(item, owner_id, cutoff):
    """Fill zero-consumption days, never include events after the selected day."""
    start = item.created_at.date()
    if start > cutoff:
        return [], np.array([], dtype=float)
    days = [start + timedelta(days=i) for i in range((cutoff - start).days + 1)]
    values = np.zeros(len(days), dtype=float)
    rows = StockMovement.query.filter(
        StockMovement.item_id == item.id,
        StockMovement.user_id == owner_id,
        StockMovement.kind == "consumption",
        StockMovement.occurred_at < cutoff_end(cutoff),
    ).all()
    for row in rows:
        index = (row.occurred_at.date() - start).days
        if index >= 0:
            values[index] += -row.delta
    return days, values


def features(history, target_day):
    """All lag/rolling features refer strictly to times before the target."""
    history = np.asarray(history, dtype=float)
    return [
        history[-1],
        history[-7],
        float(np.mean(history[-7:])),
        float(np.mean(history[-14:])),
        math.sin(2 * math.pi * target_day.weekday() / 7),
        math.cos(2 * math.pi * target_day.weekday() / 7),
    ]


def supervised(days, values):
    x = [features(values[:i], days[i]) for i in range(14, len(values))]
    return np.asarray(x), np.asarray(values[14:])


def fit_forecast(days, values):
    if len(values) < MIN_DAYS or np.count_nonzero(values) < 14:
        return None
    x, y = supervised(days, values)
    split = int(len(y) * 0.8)
    model = GradientBoostingRegressor(n_estimators=70, max_depth=2, loss="huber", random_state=42)
    model.fit(x[:split], y[:split])
    # Rolling one-step holdout: previous actual observations are available at each origin.
    ml_mae = mean_absolute_error(y[split:], np.maximum(0, model.predict(x[split:])))
    baseline = [np.mean(values[i - 7 : i]) for i in range(14 + split, len(values))]
    baseline_mae = mean_absolute_error(y[split:], baseline)
    model.fit(x, y)
    return {
        "model": model,
        "mae": float(ml_mae),
        "baseline_mae": float(baseline_mae),
        "train_days": len(values),
        "test_days": len(y) - split,
        "evaluation": "chronological rolling one-step holdout",
    }


def movement_features(rows, scales=None):
    """Scale movement magnitudes within each product/type; never use notes as labels."""
    if scales is None:
        groups = {}
        for row in rows:
            groups.setdefault((row.item_id, row.kind), []).append(abs(row.delta))
        scales = {key: max(1.0, float(np.median(values))) for key, values in groups.items()}
    matrix = []
    for row in rows:
        scale = scales.get((row.item_id, row.kind), 1.0)
        matrix.append(
            [
                abs(row.delta) / scale,
                math.log1p(abs(row.delta) / scale),
                1 if row.delta > 0 else 0,
                row.occurred_at.weekday() / 6,
            ]
        )
    return np.asarray(matrix), scales


def train_models(owner_id, cutoff, model_dir):
    items = items_at(owner_id, cutoff)
    forecasts = {}
    for item in items:
        days, values = daily_consumption(item, owner_id, cutoff)
        trained = fit_forecast(days, values)
        if trained:
            forecasts[item.id] = trained
    rows = (
        StockMovement.query.filter(
            StockMovement.user_id == owner_id,
            StockMovement.occurred_at < cutoff_end(cutoff),
            StockMovement.kind.in_(["receipt", "consumption", "adjustment"]),
        )
        .order_by(StockMovement.id)
        .all()
    )
    isolation = None
    scales = {}
    if len(rows) >= 30:
        x, scales = movement_features(rows)
        isolation = IsolationForest(n_estimators=100, contamination=0.025, random_state=42, n_jobs=1)
        isolation.fit(x)
    report = {
        "owner_id": owner_id,
        "cutoff": cutoff.isoformat(),
        "products_trained": len(forecasts),
        "forecast_mae": float(np.mean([v["mae"] for v in forecasts.values()])) if forecasts else None,
        "baseline_mae": float(np.mean([v["baseline_mae"] for v in forecasts.values()]))
        if forecasts
        else None,
        "anomaly_training_movements": len(rows),
        "anomaly_alerts": 0,
        "controlled_anomalies": 0,
        "controlled_anomalies_detected": 0,
        "evaluation": "Mean per-product MAE, chronological final 20%, rolling one-step predictions",
    }
    if isolation is not None:
        flags = isolation.predict(x) == -1
        report["anomaly_alerts"] = int(np.sum(flags))
        controlled = [i for i, r in enumerate(rows) if r.note == "Controlled demo anomaly"]
        report["controlled_anomalies"] = len(controlled)
        report["controlled_anomalies_detected"] = sum(bool(flags[i]) for i in controlled)
    bundle = {
        "version": 1,
        "owner_id": owner_id,
        "cutoff": cutoff.isoformat(),
        "forecasts": forecasts,
        "isolation": isolation,
        "scales": scales,
        "report": report,
    }
    directory = Path(model_dir) / str(owner_id)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{cutoff.isoformat()}.joblib"
    fd, name = tempfile.mkstemp(dir=directory, suffix=".tmp")
    os.close(fd)
    try:
        joblib.dump(bundle, name)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)
    target.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def load_models(owner_id, cutoff, model_dir):
    directory = Path(model_dir) / str(owner_id)
    candidates = sorted(p for p in directory.glob("????-??-??.joblib") if p.stem <= cutoff.isoformat())
    if not candidates:
        return None
    # Only trusted local artifacts generated by CLI may be stored in MODEL_DIR.
    try:
        bundle = joblib.load(candidates[-1])
        if bundle["version"] != 1 or bundle["owner_id"] != owner_id or bundle["cutoff"] > cutoff.isoformat():
            return None
        return bundle
    except (ValueError, KeyError, EOFError, OSError):
        return None


def forecast(item, owner_id, cutoff, bundle):
    stock = int(stock_at(item.id, owner_id, cutoff))
    result = {
        "stock": stock,
        "days_left": None,
        "stockout_date": None,
        "consumption_7_days": None,
        "method": "Insufficient history / model not trained",
        "mae": None,
        "baseline_mae": None,
        "daily_predictions": [],
    }
    days, values = daily_consumption(item, owner_id, cutoff)
    trained = bundle["forecasts"].get(item.id) if bundle else None
    if not trained or len(values) < MIN_DAYS:
        return result
    history = list(values)
    for offset in range(1, HORIZON + 1):
        target = cutoff + timedelta(days=offset)
        prediction = max(0.0, float(trained["model"].predict([features(history, target)])[0]))
        history.append(prediction)
        result["daily_predictions"].append(round(prediction, 3))
    predictions = result["daily_predictions"]
    result.update(
        method="Gradient Boosting",
        consumption_7_days=round(sum(predictions[:7]), 1),
        mae=round(trained["mae"], 3),
        baseline_mae=round(trained["baseline_mae"], 3),
    )
    if stock == 0:
        left = 0
    else:
        crossing = np.flatnonzero(np.cumsum(predictions) >= stock)
        left = int(crossing[0] + 1) if len(crossing) else None
    if left is not None:
        result.update(days_left=left, stockout_date=(cutoff + timedelta(days=left)).isoformat())
    return result


def anomalies(owner_id, cutoff, bundle, limit=30):
    if not bundle or bundle["isolation"] is None:
        return []
    rows = (
        StockMovement.query.filter(
            StockMovement.user_id == owner_id,
            StockMovement.occurred_at < cutoff_end(cutoff),
            StockMovement.kind.in_(["receipt", "consumption", "adjustment"]),
        )
        .order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc())
        .all()
    )
    if not rows:
        return []
    x, _ = movement_features(rows, bundle["scales"])
    flags = bundle["isolation"].predict(x)
    return [row for row, flag in zip(rows, flags, strict=True) if flag == -1][:limit]
