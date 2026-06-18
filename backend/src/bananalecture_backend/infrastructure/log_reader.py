"""Reader for structured JSON-lines log files produced by loguru."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Any

from bananalecture_backend.schemas.log import LogEntry

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import datetime


class LogReader:
    """Read, filter, and paginate JSON-lines log files."""

    def read(  # noqa: PLR0913
        self,
        log_path: Path,
        *,
        level: str | None = None,
        logger_name: str | None = None,
        event: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
        reverse: bool = True,
    ) -> tuple[list[LogEntry], int]:
        """Return a page of matching log entries and the total match count.

        Args:
            log_path: Path to the JSON-lines log file.
            level: Optional level name filter (e.g. ``INFO``).
            logger_name: Optional logger name filter.
            event: Optional event name prefix filter.
            start_time: Optional inclusive start timestamp (UTC).
            end_time: Optional inclusive end timestamp (UTC).
            limit: Maximum entries to return.
            offset: Number of matching entries to skip.
            reverse: If ``True``, newest entries first.
        """
        if not log_path.exists():
            return [], 0

        start_ts = start_time.timestamp() if start_time else None
        end_ts = end_time.timestamp() if end_time else None
        matcher = self._build_matcher(level, logger_name, event, start_ts, end_ts)

        if reverse:
            matches = self._read_reverse(log_path, matcher, limit + offset)
            matches.reverse()
        else:
            matches = self._read_forward(log_path, matcher, limit + offset)

        total = len(matches)
        page = matches[offset : offset + limit]
        return page, total

    def _build_matcher(
        self,
        level: str | None,
        logger_name: str | None,
        event: str | None,
        start_ts: float | None,
        end_ts: float | None,
    ) -> Callable[[dict[str, Any]], bool]:
        """Build a filter predicate from query parameters."""

        def matcher(record: dict[str, Any]) -> bool:
            log_record = record.get("record", {})

            if level is not None and log_record.get("level", {}).get("name", "").upper() != level.upper():
                return False

            if logger_name is not None and log_record.get("name") != logger_name:
                return False

            if event is not None:
                message = log_record.get("message", "")
                if not isinstance(message, str) or not message.startswith(event):
                    return False

            timestamp = log_record.get("time", {}).get("timestamp")
            return not (
                timestamp is not None
                and ((start_ts is not None and timestamp < start_ts) or (end_ts is not None and timestamp > end_ts))
            )

        return matcher

    def _read_forward(
        self,
        log_path: Path,
        matcher: Callable[[dict[str, Any]], bool],
        max_matches: int,
    ) -> list[LogEntry]:
        """Read log entries from oldest to newest until enough match."""
        matches: list[LogEntry] = []
        with log_path.open(encoding="utf-8") as file:
            for line in file:
                entry = self._parse_line(line)
                if entry is None:
                    continue
                if matcher(entry):
                    matches.append(self._to_schema(entry))
                    if len(matches) >= max_matches:
                        break
        return matches

    def _read_reverse(
        self,
        log_path: Path,
        matcher: Callable[[dict[str, Any]], bool],
        max_matches: int,
    ) -> list[LogEntry]:
        """Read log entries from newest to oldest until enough match."""
        matches: deque[LogEntry] = deque(maxlen=max_matches)
        for line in _read_lines_reverse(log_path):
            entry = self._parse_line(line)
            if entry is None:
                continue
            if matcher(entry):
                matches.append(self._to_schema(entry))
                if len(matches) >= max_matches:
                    break
        return list(matches)

    def _parse_line(self, line: str) -> dict[str, Any] | None:
        """Parse a single JSON log line, returning ``None`` on failure."""
        stripped = line.strip()
        if not stripped:
            return None
        try:
            parsed: dict[str, Any] = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        else:
            return parsed

    def _to_schema(self, entry: dict[str, Any]) -> LogEntry:
        """Convert a parsed loguru JSON entry into a ``LogEntry`` schema."""
        record = entry.get("record", {})
        extra = record.get("extra", {})
        message = record.get("message", "")
        event = extra.get("event") or (message if isinstance(message, str) else None)

        return LogEntry(
            timestamp=record.get("time", {}).get("repr", ""),
            level=record.get("level", {}).get("name", "UNKNOWN"),
            logger=record.get("name", ""),
            message=message if isinstance(message, str) else str(message),
            event=event if isinstance(event, str) else None,
            context={k: v for k, v in extra.items() if k != "event"},
            file=record.get("file", {}).get("name"),
            function=record.get("function"),
            line=record.get("line"),
        )


def _read_lines_reverse(path: Path) -> Iterator[str]:
    """Yield non-empty lines from ``path`` starting at the end.

    This uses fixed-size chunks so large files are not loaded into memory.
    """
    chunk_size = 4096
    with path.open("rb") as file:
        file.seek(0, 2)
        position = file.tell()
        leftover = b""

        while position > 0:
            read_size = min(chunk_size, position)
            position -= read_size
            file.seek(position)
            chunk = file.read(read_size) + leftover
            lines = chunk.split(b"\n")
            leftover = lines.pop(0) if position > 0 else b""

            for line in reversed(lines):
                decoded = line.decode("utf-8", errors="replace")
                if decoded:
                    yield decoded

        if leftover:
            decoded = leftover.decode("utf-8", errors="replace")
            if decoded:
                yield decoded
