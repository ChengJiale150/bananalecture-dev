# ruff: noqa: D102, D107, BLE001, EM101, TRY003, TC001, TC003, PLR0913

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from bananalecture_backend.application.ports import (
    AssetStore,
    AudioProcessor,
    AudioSynthesizer,
    BackgroundTaskRunner,
    DialogueGenerator,
    ImageGenerator,
    VideoRenderer,
)
from bananalecture_backend.application.strategies import AudioCueStrategy, DialoguePromptStrategy
from bananalecture_backend.application.use_cases.media import (
    GenerateProjectVideoUseCase,
    GenerateSlideAudioUseCase,
    GenerateSlideDialoguesUseCase,
    GenerateSlideImageUseCase,
)
from bananalecture_backend.core.errors import NotFoundError
from bananalecture_backend.db.repositories import ProjectRepository, SlideRepository
from bananalecture_backend.schemas.task import Task, TaskType
from bananalecture_backend.services.resources import TaskRecordService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from bananalecture_backend.core.config import Settings


def launch_task(
    task: Task,
    runtime: BackgroundTaskRunner,
    session_factory: async_sessionmaker[AsyncSession],
    work: Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]],
) -> None:
    """Create and register an application background task."""

    async def runner() -> None:
        async with session_factory() as session:
            await TaskRecordService(session).mark_running(task.id)

        try:
            await work(task.id, session_factory)
        except asyncio.CancelledError:
            async with session_factory() as session:
                await TaskRecordService(session).mark_cancelled(task.id)
            raise
        except Exception as exc:
            async with session_factory() as session:
                await TaskRecordService(session).mark_failed(task.id, str(exc))
        else:
            async with session_factory() as session:
                await TaskRecordService(session).mark_completed(task.id)

    runtime.start(task.id, runner())


class QueueBatchImageGenerationUseCase:
    """Queue image generation for all project slides."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        session_factory: async_sessionmaker[AsyncSession],
        image_generator: ImageGenerator,
        asset_store: AssetStore,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.session_factory = session_factory
        self.image_generator = image_generator
        self.asset_store = asset_store
        self.settings = settings
        self.projects = ProjectRepository(session)
        self.slides = SlideRepository(session)
        self.tasks = TaskRecordService(session)

    async def execute(self, project_id: str) -> str:
        await _ensure_project(self.projects, project_id)
        slides = await self.slides.list_by_project(project_id)
        task = await self.tasks.create_task(project_id, TaskType.IMAGE_GENERATION, max(1, len(slides)))

        async def work(task_id: str, session_factory: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                async with session_factory() as session:
                    await GenerateSlideImageUseCase(
                        session,
                        self.image_generator,
                        self.asset_store,
                        self.settings,
                    ).execute(
                        project_id,
                        slide.id,
                    )
                    await TaskRecordService(session).mark_progress(task_id, index)

        launch_task(task, self.runtime, self.session_factory, work)
        return task.id


class QueueBatchDialogueGenerationUseCase:
    """Queue dialogue generation for all project slides."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        session_factory: async_sessionmaker[AsyncSession],
        dialogue_generator: DialogueGenerator,
        prompt_strategy: DialoguePromptStrategy,
        asset_store: AssetStore,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.session_factory = session_factory
        self.dialogue_generator = dialogue_generator
        self.prompt_strategy = prompt_strategy
        self.asset_store = asset_store
        self.projects = ProjectRepository(session)
        self.slides = SlideRepository(session)
        self.tasks = TaskRecordService(session)

    async def execute(self, project_id: str) -> str:
        await _ensure_project(self.projects, project_id)
        slides = await self.slides.list_by_project(project_id)
        task = await self.tasks.create_task(project_id, TaskType.DIALOGUE_GENERATION, max(1, len(slides)))

        async def work(task_id: str, session_factory: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                async with session_factory() as session:
                    await GenerateSlideDialoguesUseCase(
                        session,
                        self.dialogue_generator,
                        self.prompt_strategy,
                        self.asset_store,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(task_id, index)

        launch_task(task, self.runtime, self.session_factory, work)
        return task.id


class QueueBatchAudioGenerationUseCase:
    """Queue audio generation for all project slides."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        session_factory: async_sessionmaker[AsyncSession],
        asset_store: AssetStore,
        audio_synthesizer: AudioSynthesizer,
        audio_processor: AudioProcessor,
        dialogue_generator: DialogueGenerator,
        prompt_strategy: DialoguePromptStrategy,
        audio_cue_strategy: AudioCueStrategy,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.session_factory = session_factory
        self.asset_store = asset_store
        self.audio_synthesizer = audio_synthesizer
        self.audio_processor = audio_processor
        self.dialogue_generator = dialogue_generator
        self.prompt_strategy = prompt_strategy
        self.audio_cue_strategy = audio_cue_strategy
        self.settings = settings
        self.projects = ProjectRepository(session)
        self.slides = SlideRepository(session)
        self.tasks = TaskRecordService(session)

    async def execute(self, project_id: str) -> str:
        await _ensure_project(self.projects, project_id)
        slides = await self.slides.list_by_project(project_id)
        task = await self.tasks.create_task(project_id, TaskType.AUDIO_GENERATION, max(1, len(slides)))

        async def work(task_id: str, session_factory: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                async with session_factory() as session:
                    await GenerateSlideAudioUseCase(
                        session,
                        self.asset_store,
                        self.audio_synthesizer,
                        self.audio_processor,
                        self.dialogue_generator,
                        self.prompt_strategy,
                        self.audio_cue_strategy,
                        self.settings,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(task_id, index)

        launch_task(task, self.runtime, self.session_factory, work)
        return task.id


class QueueProjectVideoGenerationUseCase:
    """Queue full-project video generation."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        session_factory: async_sessionmaker[AsyncSession],
        asset_store: AssetStore,
        video_renderer: VideoRenderer,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.session_factory = session_factory
        self.asset_store = asset_store
        self.video_renderer = video_renderer
        self.settings = settings
        self.tasks = TaskRecordService(session)

    async def execute(self, project_id: str) -> str:
        total_slide_steps = await GenerateProjectVideoUseCase(
            self.session,
            self.asset_store,
            self.video_renderer,
            self.settings,
        ).validate_inputs(project_id)
        task = await self.tasks.create_task(project_id, TaskType.VIDEO_GENERATION, total_slide_steps + 1)

        async def work(task_id: str, session_factory: async_sessionmaker[AsyncSession]) -> None:
            async with session_factory() as session:
                await GenerateProjectVideoUseCase(
                    session,
                    self.asset_store,
                    self.video_renderer,
                    self.settings,
                ).execute(
                    project_id,
                    on_slide_rendered=lambda step: TaskRecordService(session).mark_progress(task_id, step),
                )
                await TaskRecordService(session).mark_progress(task_id, total_slide_steps + 1)

        launch_task(task, self.runtime, self.session_factory, work)
        return task.id


class CancelTaskUseCase:
    """Cancel a queued or running task."""

    def __init__(self, session: AsyncSession, runtime: BackgroundTaskRunner) -> None:
        self.session = session
        self.runtime = runtime
        self.tasks = TaskRecordService(session)

    async def execute(self, task_id: str) -> Task:
        task = await self.tasks.get_task(task_id)
        if task.status.value in {"completed", "failed", "cancelled"}:
            return task

        self.runtime.cancel(task_id)
        await self.tasks.mark_cancelled(task_id)
        return await self.tasks.get_task(task_id)


async def _ensure_project(projects: ProjectRepository, project_id: str) -> None:
    if await projects.get(project_id) is None:
        raise NotFoundError("Project not found")
