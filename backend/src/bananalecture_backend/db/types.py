# ruff: noqa: D102, ANN401, ARG002

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

from bananalecture_backend.core.time import ensure_utc


class UTCDateTime(TypeDecorator[datetime]):
    """Persist datetimes and always restore them as UTC-aware values."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        return ensure_utc(value)
