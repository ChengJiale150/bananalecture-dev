# ruff: noqa: PLR0913

from typing import Annotated

from fastapi import APIRouter, Query, status

from bananalecture_backend.api.v1.deps import ProjectResourceServiceDep
from bananalecture_backend.schemas.project import CreateProjectRequest, UpdateProjectRequest

router = APIRouter()

PageQuery = Annotated[int, Query(ge=1)]
PageSizeQuery = Annotated[int, Query(ge=1, le=100)]
SortByQuery = Annotated[str, Query(pattern="^(created_at|updated_at|name)$")]
OrderQuery = Annotated[str, Query(pattern="^(asc|desc)$")]


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(request: CreateProjectRequest, service: ProjectResourceServiceDep) -> dict[str, object]:
    """Create a project."""
    project = await service.create_project(request)
    return {"code": status.HTTP_201_CREATED, "message": "项目创建成功", "data": project.model_dump()}


@router.get("/{user_id}/projects")
async def list_projects(
    user_id: str,
    service: ProjectResourceServiceDep,
    page: PageQuery = 1,
    page_size: PageSizeQuery = 20,
    sort_by: SortByQuery = "created_at",
    order: OrderQuery = "desc",
) -> dict[str, object]:
    """List projects for a user."""
    items, pagination = await service.list_projects(user_id, page, page_size, sort_by, order)
    return {
        "code": status.HTTP_200_OK,
        "message": "success",
        "data": {
            "items": [item.model_dump() for item in items],
            "pagination": pagination.model_dump(),
        },
    }


@router.get("/projects/{project_id}")
async def get_project(project_id: str, service: ProjectResourceServiceDep) -> dict[str, object]:
    """Get project detail."""
    project = await service.get_project_detail(project_id)
    return {"code": status.HTTP_200_OK, "message": "success", "data": project.model_dump()}


@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    service: ProjectResourceServiceDep,
) -> dict[str, object]:
    """Update project metadata."""
    project = await service.update_project(project_id, request)
    return {"code": status.HTTP_200_OK, "message": "项目更新成功", "data": project.model_dump()}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, service: ProjectResourceServiceDep) -> dict[str, object]:
    """Delete a project."""
    await service.delete_project(project_id)
    return {"code": status.HTTP_200_OK, "message": "项目删除成功", "data": None}
