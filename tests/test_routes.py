from io import BytesIO

import pytest
from PIL import Image

from extensions import db
from models import Item, StockMovement, Supplier, User
from services.inventory import create_item


@pytest.mark.parametrize(
    "path", ["/", "/dashboard", "/dashboard/", "/add", "/suppliers", "/profile/", "/import/csv"]
)
def test_requires_login(client, path):
    assert client.get(path).status_code == 302


@pytest.mark.parametrize(
    "path",
    ["/", "/dashboard", "/dashboard/", "/add", "/suppliers", "/profile/", "/import/csv", "/search?q=mouse"],
)
def test_ui_smoke(logged_in, path):
    result = logged_in.get(path)
    assert result.status_code == 200
    assert b"StockPilot AI" in result.data
    assert b"Predictive Inventory Intelligence" in result.data
    assert b"2025" not in result.data


def test_product_crud_and_stock(logged_in, user):
    payload = {"name": "Mouse", "description": "Wireless", "quantity": 10, "price": "5.50", "supplier_id": 0}
    response = logged_in.post("/add", data=payload, follow_redirects=True)
    assert response.status_code == 200 and b"Mouse" in response.data
    item = Item.query.one()
    assert item.quantity == 10 and StockMovement.query.count() == 1
    response = logged_in.post(
        f"/edit/{item.id}", data=payload | {"name": "New Mouse", "quantity": 8}, follow_redirects=True
    )
    assert b"New Mouse" in response.data and item.quantity == 8
    response = logged_in.post(
        f"/item/{item.id}/stock", data={"kind": "consumption", "quantity": 3}, follow_redirects=True
    )
    assert b"recorded" in response.data and item.quantity == 5
    response = logged_in.post(
        f"/item/{item.id}/stock", data={"kind": "consumption", "quantity": 50}, follow_redirects=True
    )
    assert b"Insufficient stock" in response.data and item.quantity == 5
    assert logged_in.post(f"/delete/{item.id}").status_code == 302
    assert Item.query.one().archived_at is not None
    assert logged_in.get(f"/item/{item.id}").status_code == 404


def test_unauthorized_crud(logged_in, user):
    other = User(username="other", password_hash="hash")
    db.session.add(other)
    db.session.flush()
    item = create_item(other.id, {"name": "Secret", "quantity": 10})
    db.session.commit()
    for path, method in [
        (f"/item/{item.id}", "get"),
        (f"/edit/{item.id}", "post"),
        (f"/delete/{item.id}", "post"),
        (f"/item/{item.id}/stock", "post"),
    ]:
        assert getattr(logged_in, method)(path).status_code == 404
    assert b"Secret" not in logged_in.get("/").data
    assert b"Secret" not in logged_in.get("/dashboard").data
    assert item.quantity == 10


def test_suppliers_csv_and_search(logged_in, user):
    assert (
        logged_in.post(
            "/suppliers", data={"name": "Office supply", "email": "supply@example.com"}
        ).status_code
        == 302
    )
    assert Supplier.query.one().user_id == user.id
    csv = b"name,quantity,price\nPaper,20,2.5\nPen,10,1\n"
    response = logged_in.post(
        "/import/csv", data={"file": (BytesIO(csv), "items.csv")}, follow_redirects=True
    )
    assert b"Imported 2" in response.data and StockMovement.query.count() == 2
    assert b"Paper" in logged_in.get("/export/csv").data
    assert b"Paper" in logged_in.get("/search?q=Paper").data
    assert b">Pen<" not in logged_in.get("/search?q=Paper").data
    invalid = b"name,quantity,price\nValid,5,1\nInvalid,-10,2\n"
    assert (
        b"Import cancelled"
        in logged_in.post("/import/csv", data={"file": (BytesIO(invalid), "bad.csv")}).data
    )
    assert Item.query.count() == 2
    assert b"Import cancelled" in logged_in.post("/import/csv").data


def test_image_upload(logged_in, app):
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, "PNG")
    image.seek(0)
    payload = {
        "name": "With image",
        "quantity": 0,
        "price": 0,
        "supplier_id": 0,
        "image": (image, "valid.png"),
    }
    assert logged_in.post("/add", data=payload).status_code == 302
    item = Item.query.one()
    assert item.image_filename.endswith(".png")
    assert logged_in.get(f"/item/{item.id}").status_code == 200
    payload["image"] = (BytesIO(b"not an image"), "fake.png")
    assert b"valid PNG" in logged_in.post("/add", data=payload).data
    assert Item.query.count() == 1


def test_errors_and_dates(logged_in, client):
    assert logged_in.get("/missing").status_code == 404
    assert logged_in.get("/dashboard?as_of=bad").status_code == 400
    assert logged_in.get("/dashboard?as_of=2999-01-01").status_code == 400
    assert client.get("/health").json["status"] == "ok"


def test_uninitialized_db_explains_command(tmp_path):
    from app import create_app

    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'empty.db'}",
            "WTF_CSRF_ENABLED": False,
        }
    )
    result = application.test_client().post("/auth/login", data={"username": "x", "password": "x"})
    assert result.status_code == 503 and b"init-db" in result.data


def test_uploaded_images_are_private(logged_in, user, app):
    from pathlib import Path

    app.static_folder = str(Path(app.config["UPLOAD_FOLDER"]).parent)
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, "PNG")
    image.seek(0)
    assert (
        logged_in.post(
            "/add",
            data={
                "name": "Image",
                "quantity": 0,
                "price": 0,
                "supplier_id": 0,
                "image": (image, "image.png"),
            },
        ).status_code
        == 302
    )
    item = Item.query.one()
    filename = item.image_filename
    assert logged_in.get(f"/uploads/{filename}").status_code == 200
    assert logged_in.get(f"/static/uploads/{filename}").status_code == 200
    assert logged_in.get("/uploads/missing.png").status_code == 404
    logged_in.post("/auth/logout")
    assert logged_in.get(f"/uploads/{filename}").status_code == 302
    other = User(username="image-other", password_hash="hash")
    other.set_password("password123")
    db.session.add(other)
    db.session.commit()
    logged_in.post("/auth/login", data={"username": other.username, "password": "password123"})
    assert logged_in.get(f"/uploads/{filename}").status_code == 404
    assert logged_in.get(f"/static/uploads/{filename}").status_code == 404
    assert logged_in.get(f"/static/css/../uploads/{filename}").status_code == 404


def test_avatar_upload_and_display(logged_in, user):
    image = BytesIO()
    Image.new("RGB", (10, 10)).save(image, "PNG")
    image.seek(0)
    assert logged_in.post("/profile/avatar", data={"avatar": (image, "avatar.png")}).status_code == 302
    assert user.avatar.endswith(".png")
    assert logged_in.get("/profile/avatar/image").status_code == 200
    assert b"Your avatar" in logged_in.get("/profile/").data
