"""
Alembic environment configuration for SkyAlert.

Wires our SQLAlchemy Base metadata and DATABASE_URL into Alembic so that
`alembic revision --autogenerate` can diff models against the real database.

Run migrations:
    alembic upgrade head
    alembic downgrade -1
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Load application models so Alembic can see them in Base.metadata.
# These imports must come before target_metadata is set.
# Importing models.py registers all ORM classes onto Base.metadata.
# ---------------------------------------------------------------------------
from backend.infrastructure.persistence.database import Base
import backend.infrastructure.persistence.models  # noqa: F401

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to alembic.ini values.
# ---------------------------------------------------------------------------
config = context.config

# Inject DATABASE_URL from environment, overriding any value in alembic.ini.
_database_url = os.environ.get("DATABASE_URL")
if not _database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Copy .env.example to .env and fill in your database URL."
    )
config.set_main_option("sqlalchemy.url", _database_url)

# Set up Python logging from alembic.ini [loggers] section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which metadata to compare against the live database.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (generates SQL without a live connection).

    Useful for previewing SQL or applying migrations in restricted environments.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (applies changes to a live database connection).

    This is the mode used by `alembic upgrade head`.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
