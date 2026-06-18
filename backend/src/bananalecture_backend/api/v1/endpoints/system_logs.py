"""System-wide log access endpoints."""

from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query, status

from bananalecture_backend.api.v1.deps import (
    CurrentUserIdDep,
    LogReaderDep,
    SettingsDep,
    require_admin,
)
from bananalecture_backend.schemas.log import LogList

router = APIRouter()

LevelQuery = Annotated[str | None, Query(description="Filter by log level (DEBUG/INFO/WARNING/ERROR)")]
EventQuery = Annotated[str | None, Query(description="Filter by event name prefix")]
StartTimeQuery = Annotated[datetime | None, Query(description="Inclusive UTC start time")]
EndTimeQuery = Annotated[datetime | None, Query(description="Inclusive UTC end time")]
LimitQuery = Annotated[int, Query(ge=1, le=500, description="Maximum entries to return")]
OffsetQuery = Annotated[int, Query(ge=0, description="Number of entries to skip")]
OrderQuery = Annotated[str, Query(pattern="^(asc|desc)$", description="Sort order, newest first when desc")]


@router.get("/system/logs/global")
async def get_global_logs(  # noqa: PLR0913
    current_user_id: CurrentUserIdDep,
    settings: SettingsDep,
    reader: LogReaderDep,
    order: OrderQuery = "desc",
    level: LevelQuery = None,
    event: EventQuery = None,
    start_time: StartTimeQuery = None,
    end_time: EndTimeQuery = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> dict[str, object]:
    """Read global application logs.

    Restricted to configured admin users.
    """
    require_admin(current_user_id, settings)

    log_path = Path(settings.STORAGE.DATA_DIR).expanduser().resolve() / "global.log"  # noqa: ASYNC240
    items, total = reader.read(
        log_path,
        level=level,
        logger_name="bananalecture.global",
        event=event,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
        reverse=order == "desc",
    )

    log_list = LogList(total=total, offset=offset, limit=limit, items=items)
    return {
        "code": status.HTTP_200_OK,
        "message": "success",
        "data": log_list.model_dump(),
    }
