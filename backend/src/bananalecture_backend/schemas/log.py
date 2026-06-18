"""Schemas for log entry responses."""

from typing import Any

from bananalecture_backend.schemas.common import APIModel


class LogEntry(APIModel):
    """A single structured log entry returned by the logs API."""

    timestamp: str
    level: str
    logger: str
    message: str
    event: str | None
    context: dict[str, Any]
    file: str | None
    function: str | None
    line: int | None


class LogList(APIModel):
    """Paginated list of log entries."""

    total: int
    offset: int
    limit: int
    items: list[LogEntry]
