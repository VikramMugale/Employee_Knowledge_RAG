"""
SQLAlchemy database session management and engine initialization.
Neon-compatible. Redis is not used.
"""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base
from backend.config.settings import settings
from backend.config.logging import logger

Base = declarative_base()

engine: Optional[AsyncEngine] = None
AsyncSessionLocal = None


def _build_engine() -> Optional[AsyncEngine]:
    if not settings.uses_postgres():
        return None
    connect_args = {}
    url = settings.async_database_url()
    if "neon.tech" in url or "ssl" in settings.database_url:
        connect_args["ssl"] = True
    return create_async_engine(
        url,
        echo=settings.debug,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


async def init_database() -> bool:
    """Create tables when Neon/Postgres is configured."""
    global engine, AsyncSessionLocal
    if not settings.uses_postgres():
        logger.info("[DB] DATABASE_URL not set; skipping Postgres.")
        return False
    try:
        from backend.db.models import entities as _entities  # noqa: F401

        engine = _build_engine()
        AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        logger.info("[DB] Connected to Postgres/Neon and ensured tables exist.")
        return True
    except Exception as exc:
        engine = None
        AsyncSessionLocal = None
        logger.error("[DB] Postgres/Neon unavailable, using in-memory registries: %s", exc)
        return False


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database session to requests."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Postgres is not configured.")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
