import pytest

from app import create_app
from commands import initialize_database
from extensions import db
from models import User


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "isolated-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
            "WTF_CSRF_ENABLED": False,
            "MODEL_DIR": str(tmp_path / "models"),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "LLM_URL": "",
        }
    )
    with application.app_context():
        initialize_database()
        yield application
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    user = User(username="student", email="student@example.com")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def logged_in(client, user):
    response = client.post("/auth/login", data={"username": user.username, "password": "password123"})
    assert response.status_code == 302
    return client


@pytest.fixture
def auth_headers(user):
    return {"Authorization": "Bearer " + user.generate_api_token()}


@pytest.fixture
def demo(app):
    from datetime import date

    from services.demo import generate_demo

    return generate_demo("demo", "demo-password", date(2026, 6, 30), days=90)
