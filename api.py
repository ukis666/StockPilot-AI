"""Bearer-only API. Session cookies never grant API access."""

from functools import wraps

from flask import Blueprint, g, jsonify, request

from extensions import db
from models import Item, User
from services.inventory import InventoryError, archive_item, create_item, edit_item, owned_item, stock_change

bp = Blueprint("api", __name__)


def token_auth_required(function):
    @wraps(function)
    def decorated(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        user = User.verify_api_token(header[7:]) if header.startswith("Bearer ") else None
        if user is None:
            return jsonify(error="A valid bearer token is required."), 401
        g.api_user = user
        return function(*args, **kwargs)

    return decorated


@bp.errorhandler(InventoryError)
def invalid_inventory(error):
    db.session.rollback()
    return jsonify(error=str(error)), 400


def json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise InventoryError("A JSON object is required.")
    return data


@bp.post("/token")
def get_token():
    data = json_object()
    if not isinstance(data.get("username"), str) or not isinstance(data.get("password"), str):
        return jsonify(error="Username and password are required."), 400
    user = User.query.filter_by(username=data["username"]).first()
    if not user or not user.check_password(data["password"]):
        return jsonify(error="Invalid username or password."), 401
    return jsonify(token=user.generate_api_token(), expires_in=3600)


@bp.get("/items")
@token_auth_required
def list_items():
    items = (
        Item.query.filter_by(user_id=g.api_user.id, archived_at=None)
        .order_by(Item.id)
        .paginate(page=request.args.get("page", 1, type=int), per_page=20, error_out=False)
    )
    return jsonify(items=[i.to_dict() for i in items], total=items.total, page=items.page, pages=items.pages)


@bp.get("/items/<int:item_id>")
@token_auth_required
def get_item(item_id):
    return jsonify(owned_item(item_id, g.api_user.id).to_dict())


@bp.post("/items")
@token_auth_required
def add_item():
    item = create_item(g.api_user.id, json_object())
    db.session.commit()
    return jsonify(item.to_dict()), 201


@bp.route("/items/<int:item_id>", methods=["PUT", "PATCH"])
@token_auth_required
def update_item(item_id):
    item = owned_item(item_id, g.api_user.id)
    data = item.to_dict() | json_object()
    edit_item(item, g.api_user.id, data)
    db.session.commit()
    return jsonify(item.to_dict())


@bp.delete("/items/<int:item_id>")
@token_auth_required
def delete_item(item_id):
    archive_item(owned_item(item_id, g.api_user.id), g.api_user.id)
    db.session.commit()
    return "", 204


@bp.post("/items/<int:item_id>/movements")
@token_auth_required
def add_movement(item_id):
    item = owned_item(item_id, g.api_user.id)
    data = json_object()
    # Internal opening/archive/adjustment kinds cannot be submitted through the API.
    if data.get("kind") not in ("receipt", "consumption"):
        raise InventoryError("Choose receipt or consumption.")
    movement = stock_change(item, g.api_user.id, data.get("delta"), data["kind"], data.get("note", ""))
    db.session.commit()
    return jsonify(id=movement.id, quantity=item.quantity), 201
