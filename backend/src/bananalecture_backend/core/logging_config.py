"""Centralized loguru-based logging configuration.

Provides:
- Global application logger writing to ``{DATA_DIR}/global.log``.
- Per-project logger writing to ``{DATA_DIR}/projects/{project_id}/logs/project.log``.
- Interception of standard-library logging so uvicorn/SQLAlchemy logs are unified.
"""

from __future__ import annotations

import contextlib
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    import types

    from loguru import Record

    from bananalecture_backend.core.config import Settings

LoguruLogger = Any


class InterceptHandler(logging.Handler):
    """Redirect standard-library logging records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Map the stdlib record to a loguru logger call."""
        level = record.levelno

        frame: types.FrameType | None = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


_project_sink_ids: dict[str, int] = {}


def setup_logging(settings: Settings) -> None:
    """Configure loguru sinks for the application.

    This should be called once during application lifespan startup.
    """
    data_dir = Path(settings.STORAGE.DATA_DIR).expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    log_level = settings.SYSTEM.LOG_LEVEL.upper()

    # Remove the default stderr sink so we can configure our own.
    logger.remove()

    # Console sink for development/operator visibility.
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        enqueue=True,
    )

    # Global application log file. All records go here; project-specific records
    # are additionally routed to their own files by the project sink factory.
    global_log_path = data_dir / "global.log"
    logger.add(
        str(global_log_path),
        level=log_level,
        serialize=True,
        rotation=settings.SYSTEM.LOG_ROTATION,
        retention=settings.SYSTEM.LOG_RETENTION,
        enqueue=True,
    )

    # Intercept standard-library loggers (uvicorn, sqlalchemy, etc.).
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in ("uvicorn", "uvicorn.access", "sqlalchemy.engine", "fastapi"):
        stdlib_logger = logging.getLogger(logger_name)
        stdlib_logger.handlers = [InterceptHandler()]
        stdlib_logger.propagate = False


def get_global_logger() -> LoguruLogger:
    """Return the global application logger."""
    return logger.bind(logger_name="bananalecture.global")


def get_project_logger(project_id: str, data_dir: Path | str) -> LoguruLogger:
    """Return a logger bound to ``project_id`` with a dedicated file sink.

    The sink is created lazily and cached for the process lifetime.
    """
    if project_id not in _project_sink_ids:
        _add_project_sink(project_id, Path(data_dir))
    return logger.bind(project_id=project_id)


def _add_project_sink(project_id: str, data_dir: Path) -> None:
    """Create a JSON-lines file sink for a single project."""
    log_path = data_dir / "projects" / project_id / "logs" / "project.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def _filter(record: Record, pid: str = project_id) -> bool:
        extra: dict[str, Any] = record["extra"]
        return extra.get("project_id") == pid

    sink_id = logger.add(
        str(log_path),
        serialize=True,
        rotation="10 MB",
        retention="30 days",
        enqueue=True,
        filter=_filter,
    )
    _project_sink_ids[project_id] = sink_id


def remove_project_sink(project_id: str) -> None:
    """Remove the dedicated sink for ``project_id`` if it exists.

    Called when a project is deleted to release file handles.
    """
    sink_id = _project_sink_ids.pop(project_id, None)
    if sink_id is not None:
        with contextlib.suppress(ValueError):  # pragma: no cover - sink may already be removed
            logger.remove(sink_id)
