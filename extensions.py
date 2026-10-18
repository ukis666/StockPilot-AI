from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine

# Stable names allow Alembic to alter SQLite constraints safely.
db = SQLAlchemy(
    metadata=MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def sqlite_foreign_keys(connection, _):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
