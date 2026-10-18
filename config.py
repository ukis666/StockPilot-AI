"""Environment configuration. The default database path preserves upstream data."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'inventory.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 30}}
    MODEL_DIR = os.environ.get("MODEL_DIR", str(BASE_DIR / "instance/models"))
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "static/uploads"))
    LLM_URL = os.environ.get("LLM_URL", "")
    LLM_TIMEOUT = 5
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    WTF_CSRF_TIME_LIMIT = 3600
    ITEMS_PER_PAGE = 20
