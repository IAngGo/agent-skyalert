"""
Database engine and session factory for SkyAlert.

Reads DATABASE_URL from environment. Provides a SessionLocal factory
and a get_db() dependency for FastAPI route injection.

Never import application or domain modules here — this is pure infrastructure.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _require_env(key: str) -> str:
    """
    Read a required environment variable or raise at startup.

    Args:
        key: The environment variable name.

    Returns:
        The variable's string value.

    Raises:
        RuntimeError: If the variable is not set.
    """
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{key}' is not set. "
            "Add it to your .env file."
        )
    return value


DATABASE_URL: str = _require_env("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # reconnect silently after idle timeout
    echo=False,           # set to True locally to log SQL queries
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """
    Shared declarative base for all SQLAlchemy ORM models.

    All models in models.py inherit from this class.
    """


def get_db():
    """
    FastAPI dependency that yields a database session and ensures cleanup.

    Usage:
        @router.get("/")
        def endpoint(db: Session = Depends(get_db)): ...

    Yields:
        An active SQLAlchemy Session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
