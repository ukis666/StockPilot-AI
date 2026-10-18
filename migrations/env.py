from alembic import context

from extensions import db

connection = context.config.attributes["connection"]
context.configure(
    connection=connection, target_metadata=db.metadata, render_as_batch=True, transactional_ddl=True
)
with context.begin_transaction():
    context.run_migrations()
