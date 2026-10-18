"""Add supplier relationships, constraints and an opening audit ledger."""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"


def upgrade():
    bind = op.get_bind()
    # Fail before rebuilding if legacy data violates the new invariants.
    invalid = bind.execute(sa.text("SELECT count(*) FROM item WHERE quantity < 0 OR price < 0")).scalar()
    if invalid:
        raise RuntimeError("Legacy negative quantities/prices require manual correction; no records removed.")
    op.create_table(
        "supplier",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(120)),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "name"),
        sa.UniqueConstraint("id", "user_id"),
    )
    op.create_index("ix_supplier_user_id", "supplier", ["user_id"])
    bind.execute(sa.text("UPDATE item SET quantity = 0 WHERE quantity IS NULL"))
    bind.execute(sa.text("UPDATE item SET price = 0 WHERE price IS NULL"))
    bind.execute(sa.text("UPDATE item SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
    with op.batch_alter_table("item") as batch:
        batch.add_column(sa.Column("supplier_id", sa.Integer))
        batch.add_column(sa.Column("archived_at", sa.DateTime))
        batch.alter_column("quantity", existing_type=sa.Integer, nullable=False)
        batch.alter_column("price", existing_type=sa.Float, nullable=False)
        batch.alter_column("created_at", existing_type=sa.DateTime, nullable=False)
        batch.create_foreign_key("fk_item_supplier_id_supplier", "supplier", ["supplier_id"], ["id"])
        batch.create_foreign_key(
            "fk_item_supplier_owner", "supplier", ["supplier_id", "user_id"], ["id", "user_id"]
        )
        batch.create_unique_constraint("uq_item_id_user_id", ["id", "user_id"])
        batch.create_check_constraint("quantity_nonnegative", "quantity >= 0")
        batch.create_check_constraint("price_nonnegative", "price >= 0")
        batch.create_index("ix_item_owner_created", ["user_id", "created_at"])
    # Reuse entity table definitions for this revision; future revisions must not alter this schema.
    op.create_table(
        "stock_movement",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("item.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.Column("delta", sa.Integer, nullable=False),
        sa.Column("balance_after", sa.Integer, nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("note", sa.String(300)),
        sa.Column("occurred_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(["item_id", "user_id"], ["item.id", "item.user_id"]),
        sa.CheckConstraint("delta != 0", name="delta_nonzero"),
        sa.CheckConstraint("balance_after >= 0", name="balance_nonnegative"),
        sa.CheckConstraint(
            "kind IN ('opening','receipt','consumption','adjustment','archive')", name="kind_valid"
        ),
        sa.CheckConstraint("kind != 'consumption' OR delta < 0", name="consumption_negative"),
        sa.CheckConstraint("kind NOT IN ('opening','receipt') OR delta > 0", name="receipt_positive"),
    )
    op.create_index("ix_movement_owner_time", "stock_movement", ["user_id", "occurred_at"])
    op.create_index("ix_movement_item_time", "stock_movement", ["item_id", "occurred_at"])
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    bind.execute(
        sa.text("""INSERT INTO stock_movement
        (item_id,user_id,delta,balance_after,kind,note,occurred_at,created_at)
        SELECT id,user_id,quantity,quantity,'opening','Legacy balance at migration',:now,:now
        FROM item WHERE quantity > 0"""),
        {"now": now.isoformat(sep=" ")},
    )


def downgrade():
    raise RuntimeError("Destructive downgrades are disabled; restore a verified backup instead.")
