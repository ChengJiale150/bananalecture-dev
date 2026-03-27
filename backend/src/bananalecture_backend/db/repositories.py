# ruff: noqa: D102, D107, FBT001

from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bananalecture_backend.models import DialogueModel, ProjectModel, SlideModel, TaskModel


class ProjectRepository:
    """Data access for project entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, project: ProjectModel) -> None:
        self.session.add(project)

    async def get(self, project_id: str) -> ProjectModel | None:
        return await self.session.get(ProjectModel, project_id)

    async def list_by_user(
        self,
        user_id: str,
        page: int,
        page_size: int,
        sort_column: str,
        descending: bool,
    ) -> tuple[list[ProjectModel], int]:
        count_query = select(func.count()).select_from(ProjectModel).where(ProjectModel.user_id == user_id)
        total = int((await self.session.execute(count_query)).scalar_one())

        order_column = getattr(ProjectModel, sort_column)
        if descending:
            order_column = order_column.desc()

        query = (
            select(ProjectModel)
            .where(ProjectModel.user_id == user_id)
            .order_by(order_column)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.session.execute(query)).scalars().all()
        return list(rows), total

    async def delete(self, project_id: str) -> None:
        project = await self.get(project_id)
        if project is not None:
            await self.session.delete(project)

    async def update(self, project: ProjectModel, values: dict[str, Any]) -> None:
        for field_name, field_value in values.items():
            setattr(project, field_name, field_value)


class SlideRepository:
    """Data access for slide entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_project(self, project_id: str) -> list[SlideModel]:
        query = (
            select(SlideModel)
            .where(SlideModel.project_id == project_id)
            .order_by(SlideModel.idx.asc(), SlideModel.created_at.asc())
        )
        rows = (await self.session.execute(query)).scalars().all()
        return list(rows)

    async def get(self, project_id: str, slide_id: str) -> SlideModel | None:
        query = select(SlideModel).where(
            SlideModel.project_id == project_id,
            SlideModel.id == slide_id,
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def create_many(self, slides: Sequence[SlideModel]) -> None:
        self.session.add_all(list(slides))

    async def create_one(self, slide: SlideModel) -> None:
        self.session.add(slide)

    async def delete_by_project(self, project_id: str) -> None:
        await self.session.execute(delete(SlideModel).where(SlideModel.project_id == project_id))

    async def delete_one(self, slide: SlideModel) -> None:
        await self.session.delete(slide)

    async def update(self, slide: SlideModel, values: dict[str, Any]) -> None:
        for field_name, field_value in values.items():
            setattr(slide, field_name, field_value)


class DialogueRepository:
    """Data access for dialogue entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_slide(self, slide_id: str) -> list[DialogueModel]:
        query = (
            select(DialogueModel)
            .where(DialogueModel.slide_id == slide_id)
            .order_by(DialogueModel.idx.asc(), DialogueModel.created_at.asc())
        )
        rows = (await self.session.execute(query)).scalars().all()
        return list(rows)

    async def get(self, slide_id: str, dialogue_id: str) -> DialogueModel | None:
        query = select(DialogueModel).where(
            DialogueModel.slide_id == slide_id,
            DialogueModel.id == dialogue_id,
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def create_many(self, dialogues: Sequence[DialogueModel]) -> None:
        self.session.add_all(list(dialogues))

    async def create_one(self, dialogue: DialogueModel) -> None:
        self.session.add(dialogue)

    async def delete_by_slide(self, slide_id: str) -> None:
        await self.session.execute(delete(DialogueModel).where(DialogueModel.slide_id == slide_id))

    async def delete_one(self, dialogue: DialogueModel) -> None:
        await self.session.delete(dialogue)

    async def update(self, dialogue: DialogueModel, values: dict[str, Any]) -> None:
        for field_name, field_value in values.items():
            setattr(dialogue, field_name, field_value)


class TaskRepository:
    """Data access for task entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, task: TaskModel) -> None:
        self.session.add(task)

    async def get(self, task_id: str) -> TaskModel | None:
        return await self.session.get(TaskModel, task_id)

    async def update(self, task: TaskModel, values: dict[str, Any]) -> None:
        for field_name, field_value in values.items():
            setattr(task, field_name, field_value)
