import sqlite3
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app
from commands import initialize_database
from extensions import db
from models import Item, StockMovement, Supplier, User
from services.inventory import (
    InventoryError,
    archive_item,
    create_item,
    edit_item,
    integer,
    stock_at,
    stock_change,
    validate_product,
)


def test_database_init_idempotent_persistence(app, user):
    item = create_item(user.id, {"name": "Persistent", "quantity": 12})
    db.session.commit()
    uid, iid = user.id, item.id
    initialize_database()
    config = {k: app.config[k] for k in ["SQLALCHEMY_DATABASE_URI", "SECRET_KEY", "TESTING"]}
    restarted = create_app(config)
    with restarted.app_context():
        assert db.session.get(User, uid).username == "student"
        assert db.session.get(Item, iid).quantity == 12
        assert StockMovement.query.count() == 1
        assert db.session.execute(db.text("PRAGMA foreign_keys")).scalar() == 1


def test_legacy_migration_preserves_records(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
        CREATE TABLE user (id INTEGER PRIMARY KEY, username VARCHAR(64) UNIQUE NOT NULL,
        password_hash VARCHAR(256) NOT NULL, email VARCHAR(120) UNIQUE, bio VARCHAR(300),
        avatar VARCHAR(120), created_at DATETIME, last_login DATETIME);
        CREATE TABLE item (id INTEGER PRIMARY KEY, name VARCHAR(120) NOT NULL, description TEXT,
        quantity INTEGER, price FLOAT, category VARCHAR(80), image_filename VARCHAR(200),
        created_at DATETIME, user_id INTEGER REFERENCES user(id));
        INSERT INTO user VALUES(1,'legacy','preserved-hash','old@example.com',NULL,NULL,'2025-01-01',NULL);
        INSERT INTO item VALUES(1,'Legacy product',NULL,8,2.5,NULL,'saved.png','2025-01-02',1);
        INSERT INTO item VALUES(2,'Unowned product',NULL,3,1,NULL,NULL,'2025-01-02',NULL);
        """)
    application = create_app(
        {"TESTING": True, "SECRET_KEY": "test", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{path}"}
    )
    with application.app_context():
        backup = initialize_database()
        assert backup.exists()
        assert db.session.get(User, 1).password_hash == "preserved-hash"
        assert db.session.get(Item, 1).image_filename == "saved.png"
        assert db.session.get(Item, 2).user_id is None
        assert StockMovement.query.count() == 2
        assert initialize_database() is None
        assert not db.session.execute(db.text("PRAGMA foreign_key_check")).all()


def test_failed_migration_is_atomic(tmp_path):
    application = create_app(
        {"TESTING": True, "SECRET_KEY": "test", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'bad.db'}"}
    )
    with application.app_context():
        with db.engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE item (id INTEGER PRIMARY KEY, quantity INTEGER, price FLOAT)")
            conn.exec_driver_sql("INSERT INTO item VALUES(1,-2,0)")
        with pytest.raises(RuntimeError, match="negative"):
            initialize_database()
        assert db.session.execute(db.text("SELECT quantity FROM item")).scalar() == -2
        assert "supplier" not in db.inspect(db.engine).get_table_names()
        assert "user" not in db.inspect(db.engine).get_table_names()


def test_stock_ledger_and_rollback(user):
    item = create_item(user.id, {"name": "Mouse", "quantity": 10})
    db.session.commit()
    stock_change(item, user.id, -4, "consumption")
    stock_change(item, user.id, 8, "receipt")
    db.session.commit()
    assert item.quantity == 14
    assert [m.balance_after for m in item.movements] == [10, 6, 14]
    with pytest.raises(InventoryError):
        stock_change(item, user.id, -15, "consumption")
    db.session.rollback()
    assert item.quantity == 14 and StockMovement.query.count() == 3
    stock_change(item, user.id, 1, "receipt")
    with pytest.raises(InventoryError):
        stock_change(item, user.id, -100, "consumption")
    db.session.rollback()
    assert item.quantity == 14 and StockMovement.query.count() == 3


def test_edit_archive_preserves_history(user):
    item = create_item(user.id, {"name": "Mouse", "quantity": 5})
    edit_item(item, user.id, {"name": "Updated", "quantity": 9, "price": 0})
    db.session.commit()
    assert item.quantity == 9 and item.movements[-1].kind == "adjustment"
    archive_item(item, user.id)
    db.session.commit()
    assert item.archived_at and item.quantity == 0
    assert sum(m.delta for m in item.movements) == 0
    assert StockMovement.query.count() == 3


def test_foreign_keys_and_owner_constraints(user):
    other = User(username="other", password_hash="hash")
    db.session.add(other)
    db.session.flush()
    supplier = Supplier(user_id=other.id, name="Private")
    db.session.add(supplier)
    db.session.commit()
    with pytest.raises(InventoryError):
        create_item(user.id, {"name": "Bad", "supplier_id": supplier.id})
    db.session.add(Item(user_id=user.id, name="Bad", quantity=1, price=1, supplier_id=supplier.id))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    db.session.add(Item(user_id=9999, name="Orphan", quantity=1, price=1))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    item = create_item(user.id, {"name": "Valid", "quantity": 1})
    db.session.commit()
    db.session.add(StockMovement(item_id=item.id, user_id=other.id, delta=2, balance_after=3, kind="receipt"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    db.session.delete(item)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        {"name": " "},
        {"name": "a" * 121},
        {"name": "X", "price": "nan"},
        {"name": "X", "price": -1},
        {"name": "X", "quantity": -1},
        {"name": "X", "quantity": True},
        {"name": "X", "quantity": 1.5},
        {"name": "X", "description": 3},
        {"name": "X", "category": "a" * 81},
    ],
)
def test_invalid_products(user, data):
    with pytest.raises(InventoryError):
        validate_product(data, user.id)


@pytest.mark.parametrize(
    "delta,kind,note",
    [
        (0, "receipt", ""),
        (-1, "receipt", ""),
        (1, "consumption", ""),
        (1, "bad", ""),
        (1, "receipt", "a" * 301),
        (True, "receipt", ""),
    ],
)
def test_invalid_movements(user, delta, kind, note):
    item = create_item(user.id, {"name": "X", "quantity": 5})
    with pytest.raises(InventoryError):
        stock_change(item, user.id, delta, kind, note)
    db.session.rollback()


def test_zero_quantity_and_historical_stock(user):
    item = create_item(user.id, {"name": "Zero", "quantity": 0, "price": 0})
    db.session.commit()
    assert item.quantity == 0 and not item.movements
    assert stock_at(item.id, user.id, date(2020, 1, 1)) == 0
    assert integer("12", "Number") == 12


def test_database_rejects_negative_quantity(user):
    item = create_item(user.id, {"name": "Nonnegative", "quantity": 5})
    db.session.commit()
    item.quantity = -1
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert item.quantity == 5


def test_stale_absolute_edit_rejected(user):
    from sqlalchemy.orm import Session

    item = create_item(user.id, {"name": "Concurrent", "quantity": 10})
    db.session.commit()
    # Simulate a different worker committing after this request loaded its item.
    with Session(db.engine) as worker:
        worker.execute(db.update(Item).where(Item.id == item.id).values(quantity=12))
        worker.commit()
    with pytest.raises(InventoryError, match="another request"):
        edit_item(item, user.id, {"name": "Concurrent", "quantity": 8})
    db.session.rollback()
    assert item.quantity == 12
