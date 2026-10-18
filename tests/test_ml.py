from datetime import date, datetime, timedelta

import numpy as np
import pytest

from extensions import db
from models import Item, StockMovement, User
from services.demo import generate_demo
from services.inventory import create_item, items_at, stock_at, stock_change
from services.ml import (
    anomalies,
    daily_consumption,
    features,
    fit_forecast,
    forecast,
    load_models,
    supervised,
    train_models,
)


def test_demo_invariants_and_no_overwrite(demo):
    items = Item.query.filter_by(user_id=demo.id).all()
    assert len(items) == 30 and len(demo.suppliers) == 4
    assert StockMovement.query.filter_by(user_id=demo.id, kind="consumption").count() == 30 * 90
    assert StockMovement.query.filter_by(note="Controlled demo anomaly").count() == 10
    assert all(
        item.quantity >= 0 and item.quantity == sum(row.delta for row in item.movements) for item in items
    )
    with pytest.raises(ValueError, match="already exists"):
        generate_demo(demo.username, "password123", date(2026, 6, 30))
    assert User.query.count() == 1
    assert not items_at(demo.id, date(2020, 1, 1))


def test_demo_reproducibility_and_preservation(app, demo, user):
    other = generate_demo("second-demo", "password123", date(2026, 6, 30), days=90)
    first = StockMovement.query.filter_by(user_id=demo.id).order_by(StockMovement.id).all()
    second = StockMovement.query.filter_by(user_id=other.id).order_by(StockMovement.id).all()
    assert [(r.delta, r.kind, r.occurred_at) for r in first] == [
        (r.delta, r.kind, r.occurred_at) for r in second
    ]
    assert User.query.filter_by(username="student").one().id == user.id


def test_preprocessing_and_cutoff(user):
    item = create_item(user.id, {"name": "Cutoff", "quantity": 100}, created_at=datetime(2026, 1, 1))
    stock_change(item, user.id, -4, "consumption", occurred_at=datetime(2026, 1, 2, 17))
    stock_change(item, user.id, -50, "consumption", occurred_at=datetime(2026, 1, 4, 17))
    db.session.commit()
    days, values = daily_consumption(item, user.id, date(2026, 1, 3))
    assert values.tolist() == [0, 4, 0]
    assert stock_at(item.id, user.id, date(2026, 1, 3)) == 96
    assert daily_consumption(item, user.id, date(2025, 1, 1))[0] == []
    assert stock_at(item.id, user.id, date(2026, 1, 4)) == 46
    historical_features = features(np.arange(14), date(2026, 1, 15))
    assert historical_features[:4] == [13, 7, 10, 6.5]
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(40)]
    values = np.arange(40, dtype=float)
    x, y = supervised(days, values)
    changed = values.copy()
    changed[30:] = 10000
    xx, _ = supervised(days, changed)
    np.testing.assert_array_equal(x[:16], xx[:16])
    assert y[0] == 14


def test_forecasting_and_anomalies(app, demo):
    cutoff = date(2026, 6, 30)
    report = train_models(demo.id, cutoff, app.config["MODEL_DIR"])
    assert report["products_trained"] == 30
    assert report["forecast_mae"] >= 0 and report["baseline_mae"] >= 0
    assert report["controlled_anomalies_detected"] >= 8
    bundle = load_models(demo.id, cutoff, app.config["MODEL_DIR"])
    assert bundle["isolation"].n_jobs == 1
    item = Item.query.filter_by(user_id=demo.id).first()
    result = forecast(item, demo.id, cutoff, bundle)
    assert result["method"] == "Gradient Boosting"
    assert len(result["daily_predictions"]) == 90
    assert all(v >= 0 for v in result["daily_predictions"])
    assert result["consumption_7_days"] > 0
    if result["days_left"] is not None:
        assert result["stockout_date"] >= cutoff.isoformat()
    alerts = anomalies(demo.id, cutoff, bundle, limit=1000)
    assert alerts and all(row.user_id == demo.id and row.occurred_at.date() <= cutoff for row in alerts)
    assert load_models(demo.id, cutoff - timedelta(days=1), app.config["MODEL_DIR"]) is None
    assert load_models(demo.id + 100, cutoff, app.config["MODEL_DIR"]) is None
    # Inference never changes balances or ledger entries.
    assert result["stock"] == item.quantity
    count = StockMovement.query.count()
    anomalies(demo.id, cutoff, bundle)
    assert StockMovement.query.count() == count


def test_historical_model_ignores_future(app, demo):
    cutoff = date(2026, 6, 1)
    report = train_models(demo.id, cutoff, app.config["MODEL_DIR"])
    item = Item.query.filter_by(user_id=demo.id).first()
    bundle = load_models(demo.id, cutoff, app.config["MODEL_DIR"])
    before = forecast(item, demo.id, cutoff, bundle)
    stock_change(item, demo.id, 1234, "receipt", occurred_at=datetime(2026, 7, 1))
    stock_change(item, demo.id, -1000, "consumption", occurred_at=datetime(2026, 7, 1, 17))
    db.session.commit()
    after = forecast(item, demo.id, cutoff, bundle)
    assert before == after
    again = train_models(demo.id, cutoff, app.config["MODEL_DIR"])
    assert report == again
    train_models(demo.id, date(2026, 6, 30), app.config["MODEL_DIR"])
    assert load_models(demo.id, cutoff, app.config["MODEL_DIR"])["cutoff"] == "2026-06-01"


def test_insufficient_history_and_empty_anomalies(app, user):
    item = create_item(user.id, {"name": "New", "quantity": 0})
    db.session.commit()
    cutoff = item.created_at.date()
    report = train_models(user.id, cutoff, app.config["MODEL_DIR"])
    bundle = load_models(user.id, cutoff, app.config["MODEL_DIR"])
    assert report["products_trained"] == 0
    assert forecast(item, user.id, cutoff, bundle)["days_left"] is None
    assert anomalies(user.id, cutoff, bundle) == []
    assert anomalies(user.id, cutoff, None) == []
    assert fit_forecast([cutoff] * 45, np.zeros(45)) is None


def test_demo_dashboard_renders(app, client, demo):
    train_models(demo.id, date(2026, 6, 30), app.config["MODEL_DIR"])
    client.post("/auth/login", data={"username": demo.username, "password": "demo-password"})
    result = client.get("/dashboard?as_of=2026-06-30")
    assert result.status_code == 200
    for text in [
        b"Gradient Boosting",
        b"Deterministic summary",
        b"ML anomaly alerts",
        b"2026-06-30",
        b"Model cutoff",
    ]:
        assert text in result.data
    result = client.get("/dashboard?as_of=2026-05-01")
    assert b"No eligible trained model" in result.data
