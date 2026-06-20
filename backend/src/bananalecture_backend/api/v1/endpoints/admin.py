"""Admin management endpoints for dashboard, user list, and project overview."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from bananalecture_backend.api.v1.deps import (
    CurrentUserIdDep,
    DBSessionDep,
    SettingsDep,
    require_admin,
)
from bananalecture_backend.db.repositories import (
    DialogueRepository,
    ProjectRepository,
    SlideRepository,
    TaskRepository,
)
from bananalecture_backend.schemas.admin import AdminUserItem, AdminUserList, DashboardStats, TaskStats
from bananalecture_backend.schemas.common import Pagination
from bananalecture_backend.schemas.project import ProjectSummary

router = APIRouter()

PageQuery = Annotated[int, Query(ge=1)]
PageSizeQuery = Annotated[int, Query(ge=1, le=100)]
SortByUserQuery = Annotated[str, Query(pattern="^(user_id|project_count|last_active_at)$")]
SortByProjectQuery = Annotated[str, Query(pattern="^(created_at|updated_at|name)$")]
OrderQuery = Annotated[str, Query(pattern="^(asc|desc)$")]
UserIdFilterQuery = Annotated[str | None, Query(description="Optional filter by user_id")]


@router.get("/system/admin/dashboard")
async def get_dashboard_stats(
    current_user_id: CurrentUserIdDep,
    session: DBSessionDep,
    settings: SettingsDep,
) -> dict[str, object]:
    """Get aggregate dashboard statistics.

    Restricted to configured admin users.
    """
    require_admin(current_user_id, settings)

    projects = ProjectRepository(session)
    slides = SlideRepository(session)
    dialogues = DialogueRepository(session)
    tasks = TaskRepository(session)

    total_users = await projects.count_distinct_users()
    total_projects = await projects.count_all()
    total_slides = await slides.count_all()
    total_dialogues = await dialogues.count_all()
    total_tasks = await tasks.count_all()
    tasks_by_status = await tasks.count_by_status()

    task_stats = TaskStats(
        total=total_tasks,
        pending=tasks_by_status.get("pending", 0),
        running=tasks_by_status.get("running", 0),
        completed=tasks_by_status.get("completed", 0),
        failed=tasks_by_status.get("failed", 0),
        cancelled=tasks_by_status.get("cancelled", 0),
    )

    stats = DashboardStats(
        total_users=total_users,
        total_projects=total_projects,
        total_slides=total_slides,
        total_dialogues=total_dialogues,
        tasks=task_stats,
    )
    return {"code": status.HTTP_200_OK, "message": "success", "data": stats.model_dump()}


@router.get("/system/admin/users")
async def list_admin_users(  # noqa: PLR0913
    current_user_id: CurrentUserIdDep,
    session: DBSessionDep,
    settings: SettingsDep,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 20,
    sort_by: SortByUserQuery = "last_active_at",
    order: OrderQuery = "desc",
) -> dict[str, object]:
    """List all distinct users with project counts.

    Restricted to configured admin users.
    """
    require_admin(current_user_id, settings)

    projects = ProjectRepository(session)
    rows, total = await projects.list_distinct_users(
        page,
        page_size,
        sort_by,
        descending=order == "desc",
    )

    items = [AdminUserItem(user_id=row[0], project_count=row[1], last_active_at=row[2]) for row in rows]
    total_pages = max(1, (total + page_size - 1) // page_size)
    pagination = Pagination(page=page, page_size=page_size, total=total, total_pages=total_pages)
    result = AdminUserList(items=items, pagination=pagination)
    return {"code": status.HTTP_200_OK, "message": "success", "data": result.model_dump()}


@router.get("/system/admin/projects")
async def list_admin_projects(  # noqa: PLR0913
    current_user_id: CurrentUserIdDep,
    session: DBSessionDep,
    settings: SettingsDep,
    user_id: UserIdFilterQuery = None,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 20,
    sort_by: SortByProjectQuery = "created_at",
    order: OrderQuery = "desc",
) -> dict[str, object]:
    """List all projects across all users.

    Restricted to configured admin users.
    """
    require_admin(current_user_id, settings)

    projects = ProjectRepository(session)
    rows, total = await projects.list_all(
        page,
        page_size,
        user_id,
        sort_by,
        descending=order == "desc",
    )

    items = [ProjectSummary.model_validate(p) for p in rows]
    total_pages = max(1, (total + page_size - 1) // page_size)
    pagination = Pagination(page=page, page_size=page_size, total=total, total_pages=total_pages)
    return {
        "code": status.HTTP_200_OK,
        "message": "success",
        "data": {"items": [item.model_dump() for item in items], "pagination": pagination.model_dump()},
    }
