# ruff: noqa: D102, D107, FBT001

from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bananalecture_backend.models import (
    DialogueModel,
    GenerationSessionModel,
    ProjectModel,
    SlideModel,
    TaskModel,
)


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

    async def count_all(self) -> int:
        query = select(func.count()).select_from(ProjectModel)
        return int((await self.session.execute(query)).scalar_one())

    async def count_distinct_users(self) -> int:
        query = select(func.count(func.distinct(ProjectModel.user_id))).select_from(ProjectModel)
        return int((await self.session.execute(query)).scalar_one())

    async def list_all(
        self,
        page: int,
        page_size: int,
        user_id: str | None,
        sort_column: str,
        descending: bool,
    ) -> tuple[list[ProjectModel], int]:
        base_filter = [ProjectModel.user_id == user_id] if user_id else []
        count_query = select(func.count()).select_from(ProjectModel)
        if base_filter:
            count_query = count_query.where(*base_filter)
        total = int((await self.session.execute(count_query)).scalar_one())

        order_column = getattr(ProjectModel, sort_column)
        if descending:
            order_column = order_column.desc()

        query = (
            select(ProjectModel)
            .where(*base_filter)
            .order_by(order_column)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.session.execute(query)).scalars().all()
        return list(rows), total

    async def list_distinct_users(
        self,
        page: int,
        page_size: int,
        sort_by: str,
        descending: bool,
    ) -> tuple[list[tuple[str, int, Any]], int]:
        subq = (
            select(
                ProjectModel.user_id,
                func.count().label("project_count"),
                func.max(ProjectModel.updated_at).label("last_active_at"),
            )
            .group_by(ProjectModel.user_id)
            .subquery()
        )
        count_query = select(func.count()).select_from(subq)
        total = int((await self.session.execute(count_query)).scalar_one())

        if sort_by == "user_id":
            order_col = subq.c.user_id
        elif sort_by == "project_count":
            order_col = subq.c.project_count
        else:
            order_col = subq.c.last_active_at
        order: Any = order_col.desc() if descending else order_col

        query = (
            select(subq.c.user_id, subq.c.project_count, subq.c.last_active_at)
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.session.execute(query)).all()
        return [tuple(row) for row in rows], total


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

    async def count_all(self) -> int:
        query = select(func.count()).select_from(SlideModel)
        return int((await self.session.execute(query)).scalar_one())


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

    async def count_all(self) -> int:
        query = select(func.count()).select_from(DialogueModel)
        return int((await self.session.execute(query)).scalar_one())


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

    async def count_all(self) -> int:
        query = select(func.count()).select_from(TaskModel)
        return int((await self.session.execute(query)).scalar_one())

    async def count_by_status(self) -> dict[str, int]:
        query = select(TaskModel.status, func.count()).group_by(TaskModel.status)
        rows = (await self.session.execute(query)).all()
        return {row[0]: int(row[1]) for row in rows}


class GenerationSessionRepository:
    """Data access for generation session entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, session_obj: GenerationSessionModel) -> None:
        self.session.add(session_obj)

    async def get(self, session_id: str) -> GenerationSessionModel | None:
        return await self.session.get(GenerationSessionModel, session_id)

    async def get_by_project(self, project_id: str) -> GenerationSessionModel | None:
        query = (
            select(GenerationSessionModel)
            .where(
                GenerationSessionModel.project_id == project_id,
            )
            .order_by(GenerationSessionModel.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def update(self, session_obj: GenerationSessionModel, values: dict[str, object]) -> None:
        for field_name, field_value in values.items():
            setattr(session_obj, field_name, field_value)
