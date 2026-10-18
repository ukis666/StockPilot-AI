"""Atomic inventory operations shared by HTML, API and CSV routes.

Callers commit once per operation/batch and roll back on any exception.
"""

import math
from datetime import datetime, time, timedelta

from sqlalchemy import update
from werkzeug.exceptions import NotFound

from extensions import db
from models import Item, StockMovement, Supplier, utcnow


class InventoryError(ValueError):
    pass


def integer(value, name, minimum=0, maximum=1_000_000):
    if isinstance(value, bool):
        raise InventoryError(f"{name} must be an integer.")
    try:
        parsed = int(value)
        if float(value) != parsed or not minimum <= parsed <= maximum:
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        raise InventoryError(f"{name} must be between {minimum} and {maximum}.") from None
    return parsed


def validate_product(data, owner_id):
    if not isinstance(data, dict):
        raise InventoryError("A product object is required.")
    name = data.get("name", "")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120 or any(ord(char) < 32 for char in name):
        raise InventoryError("Name must contain 1–120 characters.")
    try:
        price = float(data.get("price", 0))
        if not math.isfinite(price) or not 0 <= price <= 1_000_000:
            raise ValueError
    except (ValueError, TypeError):
        raise InventoryError("Price must be a finite nonnegative number.") from None
    quantity = integer(data.get("quantity", 0), "Quantity")
    supplier_id = data.get("supplier_id") or None
    if supplier_id:
        supplier_id = integer(supplier_id, "Supplier", minimum=1)
        if not Supplier.query.filter_by(id=supplier_id, user_id=owner_id).first():
            raise InventoryError("Supplier is unavailable.")
    result = dict(name=name.strip(), price=price, quantity=quantity, supplier_id=supplier_id)
    for field, limit in (("description", 500), ("category", 80)):
        value = data.get(field) or ""
        if not isinstance(value, str) or len(value) > limit:
            raise InventoryError(f"Invalid {field}.")
        result[field] = value
    return result


def owned_item(item_id, owner_id, include_archived=False):
    query = Item.query.filter_by(id=item_id, user_id=owner_id)
    if not include_archived:
        query = query.filter(Item.archived_at.is_(None))
    item = query.first()
    if item is None:
        raise NotFound("Product unavailable.")
    return item


def stock_change(item, owner_id, delta, kind, note="", occurred_at=None):
    delta = integer(delta, "Stock change", minimum=-1_000_000)
    if delta == 0:
        raise InventoryError("Stock change cannot be zero.")
    if kind not in {"opening", "receipt", "consumption", "adjustment", "archive"}:
        raise InventoryError("Invalid movement type.")
    if (kind in {"receipt", "opening"} and delta < 0) or (kind == "consumption" and delta > 0):
        raise InventoryError("Movement direction does not match its type.")
    if not isinstance(note, str) or len(note) > 300:
        raise InventoryError("Note must contain at most 300 characters.")
    # Conditional SQL update prevents lost updates and negative balances across workers.
    result = db.session.execute(
        update(Item)
        .where(
            Item.id == item.id,
            Item.user_id == owner_id,
            Item.archived_at.is_(None),
            Item.quantity + delta >= 0,
            Item.quantity + delta <= 1_000_000,
        )
        .values(quantity=Item.quantity + delta)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise InventoryError("Insufficient stock, stock limit exceeded, or product unavailable.")
    db.session.refresh(item)
    movement = StockMovement(
        item_id=item.id,
        user_id=owner_id,
        delta=delta,
        balance_after=item.quantity,
        kind=kind,
        note=note,
        occurred_at=occurred_at or utcnow(),
    )
    db.session.add(movement)
    db.session.flush()
    return movement


def create_item(owner_id, data, created_at=None):
    values = validate_product(data, owner_id)
    quantity = values.pop("quantity")
    item = Item(user_id=owner_id, quantity=0, created_at=created_at or utcnow(), **values)
    db.session.add(item)
    db.session.flush()
    if quantity:
        stock_change(item, owner_id, quantity, "opening", "Opening balance", item.created_at)
    return item


def edit_item(item, owner_id, data):
    values = validate_product(data, owner_id)
    lock_item(item, owner_id)
    quantity = values.pop("quantity")
    # Lock/update the row before changing metadata, and audit absolute quantity edits.
    difference = quantity - item.quantity
    if difference:
        stock_change(item, owner_id, difference, "adjustment", "Quantity edited")
    for key, value in values.items():
        setattr(item, key, value)
    db.session.flush()
    return item


def archive_item(item, owner_id):
    lock_item(item, owner_id)
    if item.quantity:
        stock_change(item, owner_id, -item.quantity, "archive", "Product archived")
    item.archived_at = utcnow()
    db.session.flush()


def lock_item(item, owner_id):
    """Serialize absolute edits/archiving and reject stale quantities."""
    result = db.session.execute(
        update(Item)
        .where(
            Item.id == item.id,
            Item.user_id == owner_id,
            Item.archived_at.is_(None),
            Item.quantity == item.quantity,
        )
        .values(quantity=Item.quantity)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise InventoryError("Stock changed in another request. Reload the product and retry.")


def cutoff_end(day):
    return datetime.combine(day + timedelta(days=1), time.min)


def stock_at(item_id, owner_id, day):
    return (
        db.session.query(db.func.coalesce(db.func.sum(StockMovement.delta), 0))
        .filter(
            StockMovement.item_id == item_id,
            StockMovement.user_id == owner_id,
            StockMovement.occurred_at < cutoff_end(day),
        )
        .scalar()
    )


def items_at(owner_id, day):
    end = cutoff_end(day)
    return (
        Item.query.filter(
            Item.user_id == owner_id,
            Item.created_at < end,
            db.or_(Item.archived_at.is_(None), Item.archived_at >= end),
        )
        .order_by(Item.name)
        .all()
    )
