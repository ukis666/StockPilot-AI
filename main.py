"""Server-rendered inventory pages and dashboard."""

import csv
import math
from datetime import date, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func

from extensions import db
from forms import ItemForm, MovementForm, SupplierForm
from models import Item, StockMovement, Supplier, utcnow
from services.inventory import (
    InventoryError,
    archive_item,
    create_item,
    cutoff_end,
    edit_item,
    items_at,
    owned_item,
    stock_change,
)
from services.llm import commentary
from services.ml import anomalies, daily_consumption, forecast, load_models

bp = Blueprint("main", __name__)


@bp.get("/uploads/<filename>")
@login_required
def uploaded_image(filename):
    owns_product = Item.query.filter_by(user_id=current_user.id, image_filename=filename).first()
    if not owns_product and current_user.avatar != filename:
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


def save_image(upload):
    if not upload or not upload.filename:
        return None
    try:
        image = Image.open(upload.stream)
        if image.format not in {"JPEG", "PNG", "GIF"} or image.width * image.height > 16_000_000:
            raise ValueError
        image.load()
        image.thumbnail((1200, 1200))
        directory = Path(current_app.config["UPLOAD_FOLDER"])
        directory.mkdir(parents=True, exist_ok=True)
        filename = uuid4().hex + ".png"
        image.convert("RGB").save(directory / filename, "PNG")
        return filename
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise InventoryError("Upload a valid PNG, JPEG or GIF image (up to 16 megapixels).") from None


@bp.get("/")
@bp.get("/search")
@login_required
def index():
    query = Item.query.filter_by(user_id=current_user.id, archived_at=None)
    q = request.args.get("q", "").strip()[:120]
    if q:
        query = query.filter(Item.name.ilike(f"%{q}%"))
    items = query.order_by(Item.name).paginate(
        page=request.args.get("page", 1, type=int),
        per_page=current_app.config["ITEMS_PER_PAGE"],
        error_out=False,
    )
    return render_template("index.html", items=items, q=q)


@bp.get("/item/<int:item_id>")
@login_required
def view(item_id):
    item = owned_item(item_id, current_user.id)
    movements = (
        StockMovement.query.filter_by(item_id=item.id, user_id=current_user.id)
        .order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc())
        .limit(100)
        .all()
    )
    return render_template("view.html", item=item, movements=movements, form=MovementForm())


@bp.route("/add", methods=["GET", "POST"])
@bp.route("/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def product_form(item_id=None):
    item = owned_item(item_id, current_user.id) if item_id else None
    form = ItemForm(obj=item)
    form.supplier_id.choices = [(0, "No supplier")] + [
        (s.id, s.name) for s in Supplier.query.filter_by(user_id=current_user.id).order_by(Supplier.name)
    ]
    if request.method == "GET":
        form.supplier_id.data = item.supplier_id or 0 if item else 0
    if form.validate_on_submit():
        filename = None
        try:
            data = {
                field: getattr(form, field).data
                for field in ("name", "description", "quantity", "price", "category", "supplier_id")
            }
            filename = save_image(form.image.data)
            item = edit_item(item, current_user.id, data) if item else create_item(current_user.id, data)
            if filename:
                item.image_filename = filename
            db.session.commit()
            return redirect(url_for("main.view", item_id=item.id))
        except InventoryError as error:
            db.session.rollback()
            if filename:
                (Path(current_app.config["UPLOAD_FOLDER"]) / filename).unlink(missing_ok=True)
            flash(str(error), "danger")
        except Exception:
            db.session.rollback()
            if filename:
                (Path(current_app.config["UPLOAD_FOLDER"]) / filename).unlink(missing_ok=True)
            raise
    return render_template("form.html", title="Edit product" if item else "Add product", form=form)


@bp.post("/delete/<int:item_id>")
@login_required
def delete(item_id):
    item = owned_item(item_id, current_user.id)
    try:
        archive_item(item, current_user.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    flash("Product archived. Its movement history is preserved.", "success")
    return redirect(url_for("main.index"))


@bp.post("/item/<int:item_id>/stock")
@login_required
def movement(item_id):
    item = owned_item(item_id, current_user.id)
    form = MovementForm()
    if form.validate_on_submit():
        try:
            delta = form.quantity.data * (-1 if form.kind.data == "consumption" else 1)
            stock_change(item, current_user.id, delta, form.kind.data, form.note.data or "")
            db.session.commit()
            flash("Stock movement recorded.", "success")
        except InventoryError as error:
            db.session.rollback()
            flash(str(error), "danger")
    else:
        flash("Invalid movement. Check type, quantity and note.", "danger")
    return redirect(url_for("main.view", item_id=item.id))


@bp.route("/suppliers", methods=["GET", "POST"])
@login_required
def suppliers():
    form = SupplierForm()
    if form.validate_on_submit():
        db.session.add(
            Supplier(user_id=current_user.id, name=form.name.data.strip(), email=form.email.data or None)
        )
        db.session.commit()
        return redirect(url_for("main.suppliers"))
    return render_template(
        "suppliers.html",
        form=form,
        suppliers=Supplier.query.filter_by(user_id=current_user.id).order_by(Supplier.name).all(),
    )


@bp.get("/dashboard")
@bp.get("/dashboard/")
@login_required
def dashboard():
    try:
        day = date.fromisoformat(request.args.get("as_of", str(utcnow().date())))
        if day > utcnow().date():
            raise ValueError
    except ValueError:
        abort(400, "Select a valid date no later than today (UTC).")
    owner = current_user.id
    items = items_at(owner, day)
    bundle = load_models(owner, day, current_app.config["MODEL_DIR"])
    alerts = anomalies(owner, day, bundle, limit=None)
    anomalous_ids = {row.item_id for row in alerts}
    rows = [
        {"item": item, "forecast": forecast(item, owner, day, bundle), "anomaly": item.id in anomalous_ids}
        for item in items
    ]
    total_units = sum(row["forecast"]["stock"] for row in rows)
    total_value = sum(row["forecast"]["stock"] * row["item"].price for row in rows)
    history = (
        StockMovement.query.filter(
            StockMovement.user_id == owner, StockMovement.occurred_at < cutoff_end(day)
        )
        .order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc())
        .limit(10)
        .all()
    )
    summary = None
    focus = request.args.get("product", type=int)
    selected = next((row for row in rows if row["item"].id == focus), rows[0] if rows else None)
    if selected:
        values = selected["forecast"]
        reorder = min(1_000_000, max(0, math.ceil((values["consumption_7_days"] or 0) * 2 - values["stock"])))
        summary = commentary(
            {
                "product": selected["item"].name,
                "current_stock": values["stock"],
                "estimated_days_left": values["days_left"],
                "anomaly_detected": selected["anomaly"],
                "recommended_order": reorder,
            },
            current_app.config["LLM_URL"],
            current_app.config["LLM_TIMEOUT"],
        )
    # Thirty daily bars, aggregated from consumption only and bounded by selected cutoff.
    chart = {day - timedelta(days=i): 0 for i in range(29, -1, -1)}
    for item in items:
        dates, consumption = daily_consumption(item, owner, day)
        for when, units in zip(dates, consumption, strict=True):
            if when in chart:
                chart[when] += int(units)
    latest_consumption = (
        db.session.query(func.max(StockMovement.occurred_at))
        .filter(
            StockMovement.user_id == owner,
            StockMovement.kind == "consumption",
            StockMovement.occurred_at < cutoff_end(day),
        )
        .scalar()
    )
    at_risk = [
        row
        for row in rows
        if row["forecast"]["stock"] == 0
        or (row["forecast"]["days_left"] is not None and row["forecast"]["days_left"] <= 14)
    ]
    risk_rows = sorted(
        (row for row in rows if row["forecast"]["days_left"] is not None or row["forecast"]["stock"] == 0),
        key=lambda row: (row["forecast"]["days_left"] or 0, row["item"].name),
    )[:5]
    # Compare observed history with forward predictions only. A model fitted at
    # the selected cutoff must never be used to back-predict its training days.
    demand_actual, demand_predicted = [], []
    if selected:
        dates, values = daily_consumption(selected["item"], owner, day)
        start = day - timedelta(days=29)
        demand_actual = [
            ((when - start).days, when.isoformat(), float(value))
            for when, value in zip(dates, values, strict=True)
            if when >= start
        ]
        demand_predicted = [
            (30 + offset, (day + timedelta(days=offset + 1)).isoformat(), value)
            for offset, value in enumerate(selected["forecast"]["daily_predictions"][:7])
        ]
    demand_max = max([point[2] for point in demand_actual + demand_predicted] + [1])
    report = bundle.get("report", {}) if bundle else {}
    metric_max = max(report.get("forecast_mae") or 0, report.get("baseline_mae") or 0, 0.001)
    return render_template(
        "dashboard.html",
        rows=rows,
        day=day,
        today=utcnow().date(),
        total_units=total_units,
        total_value=total_value,
        history=history,
        alerts=alerts[:10],
        alert_count=len(alerts),
        risk_count=len(at_risk),
        risk_rows=risk_rows,
        latest_consumption=latest_consumption.date() if latest_consumption else None,
        has_consumption=any(chart.values()),
        demand_actual=demand_actual,
        demand_predicted=demand_predicted,
        demand_max=demand_max,
        demand_end=day + timedelta(days=7),
        report=report,
        metric_max=metric_max,
        summary=summary,
        selected=selected,
        chart=list(chart.items()),
        chart_max=max(max(chart.values()), 1),
        bundle=bundle,
    )


@bp.get("/export/csv")
@login_required
def export_csv():
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(["name", "description", "quantity", "price", "category"])
    for item in Item.query.filter_by(user_id=current_user.id, archived_at=None).order_by(Item.id):
        # Prefix spreadsheet formulas in free text; exports are safe to open locally.
        def safe(value):
            text = str(value or "")
            return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text

        writer.writerow(
            [safe(item.name), safe(item.description), item.quantity, item.price, safe(item.category)]
        )
    return send_file(
        BytesIO(stream.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="stockpilot-inventory.csv",
    )


@bp.route("/import/csv", methods=["GET", "POST"])
@login_required
def import_csv():
    if request.method == "POST":
        upload = request.files.get("file")
        try:
            if not upload:
                raise InventoryError("Select a CSV file.")
            reader = csv.DictReader(StringIO(upload.read().decode("utf-8-sig")))
            if not reader.fieldnames or "name" not in reader.fieldnames:
                raise InventoryError("CSV requires a name column.")
            count = 0
            for row in reader:
                if count >= 1000:
                    raise InventoryError("Import at most 1000 products per file.")
                create_item(current_user.id, row)
                count += 1
            db.session.commit()
            flash(f"Imported {count} products.", "success")
            return redirect(url_for("main.index"))
        except (InventoryError, UnicodeDecodeError, csv.Error) as error:
            db.session.rollback()
            flash(f"Import cancelled; no products added. {error}", "danger")
    return render_template("import_csv.html")
