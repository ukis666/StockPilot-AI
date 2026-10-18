from extensions import db
from models import User
from services.inventory import create_item


def test_api_auth_and_token(client, user, auth_headers):
    assert client.get("/api/items").status_code == 401
    assert client.post("/api/token", json=[]).status_code == 400
    assert client.post("/api/token", json={}).status_code == 400
    assert client.post("/api/token", json={"username": user.username, "password": "bad"}).status_code == 401
    result = client.post("/api/token", json={"username": user.username, "password": "password123"})
    assert result.status_code == 200 and result.json["expires_in"] == 3600
    assert client.get("/api/items", headers={"Authorization": "Bearer bad"}).status_code == 401
    assert client.get("/api/items", headers=auth_headers).json["items"] == []


def test_api_crud_movements(client, user, auth_headers):
    result = client.post("/api/items", headers=auth_headers, json={"name": "API product", "quantity": 10})
    assert result.status_code == 201
    iid = result.json["id"]
    assert client.get(f"/api/items/{iid}", headers=auth_headers).json["quantity"] == 10
    assert (
        client.patch(f"/api/items/{iid}", headers=auth_headers, json={"name": "Updated"}).json["name"]
        == "Updated"
    )
    assert (
        client.post(
            f"/api/items/{iid}/movements", headers=auth_headers, json={"delta": -4, "kind": "consumption"}
        ).json["quantity"]
        == 6
    )
    assert (
        client.post(
            f"/api/items/{iid}/movements", headers=auth_headers, json={"delta": -100, "kind": "consumption"}
        ).status_code
        == 400
    )
    assert client.get(f"/api/items/{iid}", headers=auth_headers).json["quantity"] == 6
    assert (
        client.post(
            f"/api/items/{iid}/movements", headers=auth_headers, json={"delta": 1, "kind": "archive"}
        ).status_code
        == 400
    )
    assert client.delete(f"/api/items/{iid}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/items/{iid}", headers=auth_headers).status_code == 404


def test_api_ownership_and_session_rejected(logged_in, user, auth_headers):
    other = User(username="other", password_hash="hash")
    db.session.add(other)
    db.session.flush()
    item = create_item(other.id, {"name": "Private", "quantity": 4})
    db.session.commit()
    assert logged_in.get("/api/items").status_code == 401
    assert logged_in.get(f"/api/items/{item.id}", headers=auth_headers).status_code == 404
    assert (
        logged_in.patch(f"/api/items/{item.id}", headers=auth_headers, json={"quantity": 0}).status_code
        == 404
    )
    assert logged_in.delete(f"/api/items/{item.id}", headers=auth_headers).status_code == 404
    assert logged_in.get("/api/items", headers=auth_headers).json["total"] == 0
