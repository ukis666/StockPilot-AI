"""Dashboard regressions for date windows, disclosure and bounded records."""

from datetime import date, datetime, timedelta

from flask import template_rendered

from extensions import db
from models import StockMovement
from services.inventory import create_item, stock_change


def capture_dashboard(app, client, path):
    contexts = []

    def received(sender, template, context, **extra):
        contexts.append(context)

    with template_rendered.connected_to(received, app):
        response = client.get(path)
    assert response.status_code == 200
    return response, contexts[-1]


def test_dashboard_selected_window_and_live_empty_state(app, logged_in, user):
    item = create_item(
        user.id, {"name": "Historical product", "quantity": 1000}, created_at=datetime(2026, 1, 1)
    )
    # May 31 is outside June's 30-day window; July 1 is beyond its cutoff.
    for when, units in [
        (datetime(2026, 5, 31), 99),
        (datetime(2026, 6, 1), 4),
        (datetime(2026, 6, 30, 23, 59), 7),
        (datetime(2026, 7, 1), 200),
    ]:
        stock_change(item, user.id, -units, "consumption", occurred_at=when)
    db.session.commit()
    response, context = capture_dashboard(app, logged_in, "/dashboard?as_of=2026-06-30")
    chart = dict(context["chart"])
    assert len(chart) == 30
    assert min(chart) == date(2026, 6, 1) and max(chart) == date(2026, 6, 30)
    assert sum(chart.values()) == 11
    assert context["total_units"] == 890
    assert all(row.occurred_at.date() <= date(2026, 6, 30) for row in context["history"])
    assert b"Rule-based fallback commentary" in response.data
    assert b"no local model output was used" in response.data
    response, context = capture_dashboard(app, logged_in, "/dashboard?as_of=2026-09-30")
    assert not context["has_consumption"]
    assert b"No consumption recorded" in response.data
    assert b"as_of=2026-07-01" in response.data


def test_dashboard_demand_dates_metrics_and_limits(app, logged_in, user, monkeypatch):
    cutoff = date(2026, 6, 30)
    item = create_item(user.id, {"name": "Demand product", "quantity": 1000}, created_at=datetime(2026, 1, 1))
    for offset in range(15):
        stock_change(
            item, user.id, -2, "consumption", occurred_at=datetime(2026, 6, 1) + timedelta(days=offset)
        )
    db.session.commit()
    movements = StockMovement.query.filter_by(item_id=item.id).all()
    monkeypatch.setattr(
        "main.load_models",
        lambda *args: {
            "cutoff": "2026-06-30",
            "isolation": True,
            "report": {"forecast_mae": 2.345, "baseline_mae": 1.234, "products_trained": 1},
        },
    )
    monkeypatch.setattr("main.anomalies", lambda *args, **kwargs: movements)
    monkeypatch.setattr(
        "main.forecast",
        lambda *args: {
            "stock": 970,
            "days_left": 10,
            "stockout_date": "2026-07-10",
            "daily_predictions": [3.25] * 90,
            "consumption_7_days": 22.75,
        },
    )
    response, context = capture_dashboard(app, logged_in, "/dashboard?as_of=2026-06-30")
    assert len(context["history"]) == len(context["alerts"]) == 10
    assert context["alert_count"] == len(movements)
    assert context["risk_count"] == 1
    assert max(point[1] for point in context["demand_actual"]) == "2026-06-30"
    assert [point[1] for point in context["demand_predicted"]] == [
        (cutoff + timedelta(days=i)).isoformat() for i in range(1, 8)
    ]
    assert all(point[2] == 3.25 for point in context["demand_predicted"])
    assert b"2.345" in response.data and b"1.234" in response.data
    assert b"2026-07-10" in response.data
