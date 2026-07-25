# ruff: noqa: D107

from collections.abc import AsyncIterator
from typing import Any, cast

from sqlalchemy import event
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bananalecture_backend.core.config import Settings
from bananalecture_backend.core.templates import DEFAULT_TEMPLATE_ID
from bananalecture_backend.models import Base


class DatabaseManager:
    """Owns the async SQLAlchemy engine and session factory."""

    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine = create_async_engine(
            settings.DATABASE.URL,
            future=True,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        if settings.DATABASE.URL.startswith("sqlite"):
            event.listen(self.engine.sync_engine, "connect", _set_sqlite_pragma)

    async def initialize(self) -> None:
        """Create database tables and apply schema migrations."""
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await self._ensure_template_column(connection)

    @staticmethod
    async def _ensure_template_column(connection: AsyncConnection) -> None:
        """Add ``template_id`` column if missing (e.g. existing databases)."""
        result = await connection.execute(sa_text("PRAGMA table_info(projects)"))
        column_names = {row[1] for row in result.fetchall()}
        if "template_id" not in column_names:
            await connection.execute(
                sa_text(f"ALTER TABLE projects ADD COLUMN template_id TEXT NOT NULL DEFAULT '{DEFAULT_TEMPLATE_ID}'")
            )

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
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA read_uncommitted=1")
    cursor.close()
