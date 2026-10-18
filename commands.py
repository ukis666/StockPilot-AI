"""Explicit administration commands; nothing destructive runs at application startup."""

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import click
from alembic import command
from alembic.config import Config as AlembicConfig
from flask import current_app
from sqlalchemy import inspect

from extensions import db
from models import User, utcnow


def initialize_database():
    if db.engine.dialect.name != "sqlite":
        raise click.ClickException("StockPilot supports SQLite only.")
    path = Path(db.engine.url.database)
    path.parent.mkdir(parents=True, exist_ok=True)
    tables = inspect(db.engine).get_table_names()
    with db.engine.connect() as conn:
        version = (
            conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
            if "alembic_version" in tables
            else None
        )
    if version == "002":
        return None
    backup = None
    if path.exists():
        backup = path.with_name(
            path.name + "." + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak"
        )
        with sqlite3.connect(path) as source, sqlite3.connect(backup) as target:
            source.backup(target)
    cfg = AlembicConfig()
    cfg.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    # Explicit BEGIN makes SQLite DDL and version tracking one atomic transaction.
    with db.engine.connect() as conn:
        conn.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, "head")
            violations = conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError("Foreign key violations in legacy database; migration rolled back.")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return backup


def parse_day(value):
    try:
        day = date.fromisoformat(value)
        if day >= utcnow().date():
            raise ValueError
        return day
    except (ValueError, TypeError):
        raise click.BadParameter("Use a past, completed UTC date (YYYY-MM-DD).") from None


def register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Create missing tables or safely upgrade a legacy SQLite database."""
        backup = initialize_database()
        click.echo("Database ready (schema 002)." + (f" Backup: {backup}" if backup else ""))

    @app.cli.command("demo-data")
    @click.option("--username", default="demo", show_default=True)
    @click.option(
        "--password",
        envvar="DEMO_PASSWORD",
        required=True,
        help="Password for a NEW demo account (or DEMO_PASSWORD).",
    )
    @click.option("--end-date", default=lambda: str(utcnow().date() - timedelta(days=1)))
    @click.option("--days", default=180, type=click.IntRange(30, 730))
    @click.option("--seed", default=42, type=int)
    def demo_data(username, password, end_date, days, seed):
        """Create a separate demo account; refuse to touch existing usernames."""
        from services.demo import generate_demo

        end = parse_day(end_date)
        if len(password) < 8:
            raise click.BadParameter("Password requires at least 8 characters.")
        try:
            user = generate_demo(username, password, end, days, seed)
            click.echo(f"Created demo user {user.username}: 30 products, {days} days, seed {seed}.")
        except ValueError as error:
            db.session.rollback()
            raise click.ClickException(str(error)) from error

    @app.cli.command("train-models")
    @click.option("--username", required=True)
    @click.option("--as-of", required=True, help="Completed UTC date, YYYY-MM-DD.")
    def train_models(username, as_of):
        """Train CPU models outside requests and write local versioned artifacts."""
        from services.ml import train_models as train

        day = parse_day(as_of)
        user = User.query.filter_by(username=username).first()
        if not user:
            raise click.ClickException("User not found.")
        report = train(user.id, day, current_app.config["MODEL_DIR"])
        click.echo(json.dumps(report, indent=2))
