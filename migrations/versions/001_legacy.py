"""Create or adopt the original upstream schema without deleting records."""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None


def upgrade():
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "user" not in tables:
        op.create_table(
            "user",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("username", sa.String(64), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(256), nullable=False),
            sa.Column("email", sa.String(120), unique=True),
            sa.Column("bio", sa.String(300)),
            sa.Column("avatar", sa.String(120)),
            sa.Column("created_at", sa.DateTime, nullable=False),
            sa.Column("last_login", sa.DateTime),
        )
    if "item" not in tables:
        op.create_table(
            "item",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("description", sa.Text),
            sa.Column("quantity", sa.Integer),
            sa.Column("price", sa.Float),
            sa.Column("category", sa.String(80)),
            sa.Column("image_filename", sa.String(200)),
            sa.Column("created_at", sa.DateTime),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
        )


def downgrade():
    raise RuntimeError("Destructive downgrades are disabled; restore a verified backup instead.")
