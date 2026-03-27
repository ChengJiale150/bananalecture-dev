# ruff: noqa: D102, D107, EM101, TRY003

from math import ceil
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from bananalecture_backend.core.errors import NotFoundError
from bananalecture_backend.core.time import utc_now
from bananalecture_backend.db.repositories import ProjectRepository, SlideRepository
from bananalecture_backend.models import ProjectModel
from bananalecture_backend.schemas.common import Pagination
from bananalecture_backend.schemas.project import (
    CreateProjectRequest,
    ProjectDetail,
    ProjectListItem,
    ProjectSummary,
    ProjectUpdateResult,
    UpdateProjectRequest,
)
from bananalecture_backend.schemas.slide import Slide
from bananalecture_backend.services.utils import new_id


class ProjectResourceService:
    """Resource operations for project entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.slides = SlideRepository(session)

    async def create_project(self, request: CreateProjectRequest) -> ProjectSummary:
        timestamp = utc_now()

        project = ProjectModel(
            id=new_id(),
            user_id=request.user_id,
            name=request.name,
            messages=None,
            video_path=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        await self.projects.create(project)
        await self.session.commit()
        return ProjectSummary.model_validate(project)

    async def list_projects(
        self,
        user_id: str,
        page: int,
        page_size: int,
        sort_by: str,
        order: str,
    ) -> tuple[list[ProjectListItem], Pagination]:
        items, total = await self.projects.list_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            sort_column=sort_by,
            descending=order == "desc",
        )
        pagination = Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, ceil(total / page_size)),
        )
        return [ProjectListItem.model_validate(item) for item in items], pagination

    async def get_project_detail(self, project_id: str) -> ProjectDetail:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        slides = [Slide.model_validate(slide) for slide in await self.slides.list_by_project(project_id)]
        return ProjectDetail.model_validate(
            {
                "id": project.id,
                "user_id": project.user_id,
                "name": project.name,
                "messages": project.messages,
                "video_path": project.video_path,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "slides": slides,
            }
        )

    async def update_project(self, project_id: str, request: UpdateProjectRequest) -> ProjectUpdateResult:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")

        values: dict[str, Any] = {"updated_at": utc_now()}
        if request.name is not None:
            values["name"] = request.name
        if request.messages is not None:
            values["messages"] = request.messages

        await self.projects.update(project, values)
        await self.session.commit()
        return ProjectUpdateResult.model_validate(project)

    async def delete_project(self, project_id: str) -> None:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        await self.projects.delete(project_id)
        await self.session.commit()

    async def get_video_path(self, project_id: str) -> str:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        if project.video_path is None:
            raise NotFoundError("Video not found")
        return project.video_path

    async def set_video_path(self, project_id: str, video_path: str) -> None:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        await self.projects.update(project, {"video_path": video_path, "updated_at": utc_now()})
