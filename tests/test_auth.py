import pytest

from extensions import db
from models import User, load_user


def test_registration_login_logout(client):
    assert client.get("/auth/register").status_code == 200
    response = client.post(
        "/auth/register",
        data={
            "username": "newstudent",
            "email": "new@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=True,
    )
    assert b"Account created" in response.data
    user = User.query.one()
    assert user.password_hash != "password123" and user.check_password("password123")
    response = client.post(
        "/auth/login", data={"username": "newstudent", "password": "password123"}, follow_redirects=True
    )
    assert response.status_code == 200 and b"Dashboard" in response.data
    assert user.last_login is not None
    assert client.post("/auth/logout").status_code == 302
    assert client.get("/").status_code == 302


def test_duplicate_registration(client, user):
    data = {
        "username": user.username,
        "email": "other@example.com",
        "password": "password123",
        "confirm_password": "password123",
    }
    assert b"already in use" in client.post("/auth/register", data=data).data
    data.update(username="different", email=user.email)
    assert b"already in use" in client.post("/auth/register", data=data).data
    assert User.query.count() == 1


@pytest.mark.parametrize("password", ["wrong", ""])
def test_invalid_login(client, user, password):
    assert (
        client.post("/auth/login", data={"username": user.username, "password": password}).status_code == 200
    )
    assert client.get("/").status_code == 302


@pytest.mark.parametrize("target", ["https://example.com", "//example.com", "/\\example.com"])
def test_open_redirect_prevented(client, user, target):
    result = client.post(
        "/auth/login",
        query_string={"next": target},
        data={"username": user.username, "password": "password123"},
    )
    assert result.location in {"/dashboard", "/dashboard/"}


def test_local_next_and_loader(client, user):
    result = client.post(
        "/auth/login?next=/suppliers", data={"username": user.username, "password": "password123"}
    )
    assert result.location == "/suppliers"
    assert load_user("invalid") is None and load_user(None) is None
    assert load_user(str(user.id)).id == user.id


def test_csrf_protection(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    assert client.post("/auth/register", data={"username": "new"}).status_code == 400
    assert client.get("/auth/logout").status_code == 405
    assert client.get("/auth/login").headers["X-Content-Type-Options"] == "nosniff"


def test_profile_and_password(logged_in, user):
    for path in ["/profile/", "/profile/edit", "/profile/change-password"]:
        assert logged_in.get(path).status_code == 200
    assert (
        logged_in.post(
            "/profile/edit",
            data={"username": "updated", "email": "updated@example.com", "bio": "Inventory student"},
        ).status_code
        == 302
    )
    assert db.session.get(User, user.id).username == "updated"
    data = {"current_password": "wrong", "new_password": "nextpassword", "confirm_password": "nextpassword"}
    assert b"incorrect" in logged_in.post("/profile/change-password", data=data).data
    data["current_password"] = "password123"
    assert logged_in.post("/profile/change-password", data=data).status_code == 302
    assert user.check_password("nextpassword")
