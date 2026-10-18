"""Persistent inventory entities; all application timestamps are UTC."""

from datetime import datetime, timezone

from flask import current_app
from flask_login import UserMixin
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True)
    bio = db.Column(db.String(300))
    avatar = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    last_login = db.Column(db.DateTime)
    items = db.relationship("Item", back_populates="user")
    suppliers = db.relationship("Supplier", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_api_token(self):
        return URLSafeTimedSerializer(current_app.secret_key, salt="stockpilot-api").dumps(self.id)

    @staticmethod
    def verify_api_token(token):
        try:
            uid = URLSafeTimedSerializer(current_app.secret_key, salt="stockpilot-api").loads(
                token, max_age=3600
            )
            return db.session.get(User, uid)
        except (BadSignature, SignatureExpired):
            return None


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


class Supplier(db.Model):
    __table_args__ = (
        db.UniqueConstraint("user_id", "name"),
        db.UniqueConstraint("id", "user_id"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    user = db.relationship("User", back_populates="suppliers")
    items = db.relationship("Item", back_populates="supplier", foreign_keys="Item.supplier_id")


class Item(db.Model):
    __table_args__ = (
        db.CheckConstraint("quantity >= 0", name="quantity_nonnegative"),
        db.CheckConstraint("price >= 0", name="price_nonnegative"),
        db.UniqueConstraint("id", "user_id"),
        db.ForeignKeyConstraint(["supplier_id", "user_id"], ["supplier.id", "supplier.user_id"]),
        db.Index("ix_item_owner_created", "user_id", "created_at"),
    )
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    price = db.Column(db.Float, default=0, nullable=False)
    category = db.Column(db.String(80))
    image_filename = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    # Nullable only to preserve legacy unowned records. Services always require an owner.
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    archived_at = db.Column(db.DateTime)
    user = db.relationship("User", back_populates="items", foreign_keys=[user_id])
    supplier = db.relationship("Supplier", back_populates="items", foreign_keys=[supplier_id])
    movements = db.relationship("StockMovement", back_populates="item", foreign_keys="StockMovement.item_id")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "quantity": self.quantity,
            "price": self.price,
            "category": self.category,
            "supplier_id": self.supplier_id,
            "created_at": self.created_at.isoformat(),
        }


class StockMovement(db.Model):
    __table_args__ = (
        db.ForeignKeyConstraint(["item_id", "user_id"], ["item.id", "item.user_id"]),
        db.CheckConstraint("delta != 0", name="delta_nonzero"),
        db.CheckConstraint("balance_after >= 0", name="balance_nonnegative"),
        db.CheckConstraint(
            "kind IN ('opening','receipt','consumption','adjustment','archive')", name="kind_valid"
        ),
        db.CheckConstraint("kind != 'consumption' OR delta < 0", name="consumption_negative"),
        db.CheckConstraint("kind NOT IN ('opening','receipt') OR delta > 0", name="receipt_positive"),
        db.Index("ix_movement_owner_time", "user_id", "occurred_at"),
        db.Index("ix_movement_item_time", "item_id", "occurred_at"),
    )
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    delta = db.Column(db.Integer, nullable=False)
    balance_after = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    note = db.Column(db.String(300))
    occurred_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    item = db.relationship("Item", back_populates="movements", foreign_keys=[item_id])
    user = db.relationship("User", foreign_keys=[user_id])
