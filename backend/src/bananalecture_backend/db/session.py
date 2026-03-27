# ruff: noqa: D107

from collections.abc import AsyncIterator
from typing import Any, cast

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from bananalecture_backend.core.config import Settings
from bananalecture_backend.models import Base


class DatabaseManager:
    """Owns the async SQLAlchemy engine and session factory."""

    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine = create_async_engine(settings.DATABASE.URL, future=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        if settings.DATABASE.URL.startswith("sqlite"):
            event.listen(self.engine.sync_engine, "connect", _set_sqlite_pragma)

    async def initialize(self) -> None:
        """Create database tables."""
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        """Close the database engine."""
        await self.engine.dispose()

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield an async session."""
        async with self.session_factory() as session:
            yield session


def _set_sqlite_pragma(dbapi_connection: object, _: object) -> None:
    connection = cast("Any", dbapi_connection)
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
