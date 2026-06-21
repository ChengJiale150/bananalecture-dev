# ruff: noqa: D102, D107, BLE001, EM101, EM102, TRY003, TC001, TC003, PLR0913

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
    ImagePreprocessor,
    VideoRenderer,
)
from bananalecture_backend.application.strategies import AudioCueStrategy, DialoguePromptStrategy
from bananalecture_backend.application.use_cases.media import (
    GenerateProjectVideoUseCase,
    GenerateSlideAudioUseCase,
    GenerateSlideDialoguesUseCase,
    GenerateSlideImageUseCase,
)
from bananalecture_backend.core.config import Settings
from bananalecture_backend.core.errors import BadRequestError, NotFoundError
from bananalecture_backend.core.logging_config import get_global_logger, get_project_logger
from bananalecture_backend.db.repositories import ProjectRepository, SlideRepository
from bananalecture_backend.schemas.task import Task, TaskType
from bananalecture_backend.services.resources import TaskRecordService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from bananalecture_backend.models.entities import SlideModel

global_logger = get_global_logger()


def launch_task(
    task: Task,
    runtime: BackgroundTaskRunner,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    work: Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]],
) -> None:
    """Create and register an application background task."""
    project_logger = get_project_logger(task.project_id, settings.STORAGE.DATA_DIR)

    async def runner() -> None:
        global_logger.bind(
            task_id=task.id,
            project_id=task.project_id,
            task_type=task.type.value,
        ).info("task_started")
        if project_logger is not None:
            project_logger.bind(
                task_id=task.id,
                task_type=task.type.value,
            ).info("task_started")

        async with session_factory() as session:
            await TaskRecordService(session).mark_running(task.id)

        try:
            await work(task.id, session_factory)
        except asyncio.CancelledError:
            async with session_factory() as session:
                await TaskRecordService(session).mark_cancelled(task.id)
            global_logger.bind(
                task_id=task.id,
                project_id=task.project_id,
            ).info("task_cancelled")
            if project_logger is not None:
                project_logger.bind(task_id=task.id).info("task_cancelled")
            raise
        except Exception as exc:
            async with session_factory() as session:
                await TaskRecordService(session).mark_failed(task.id, str(exc))
            global_logger.bind(
                task_id=task.id,
                project_id=task.project_id,
                error=str(exc),
            ).error("task_failed")
            if project_logger is not None:
                project_logger.bind(
                    task_id=task.id,
                    error=str(exc),
                ).error("task_failed")
        else:
            async with session_factory() as session:
                await TaskRecordService(session).mark_completed(task.id)
            global_logger.bind(
                task_id=task.id,
                project_id=task.project_id,
            ).info("task_completed")
            if project_logger is not None:
                project_logger.bind(task_id=task.id).info("task_completed")

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
        global_logger.bind(
            task_id=task.id,
            project_id=project_id,
            task_type=task.type.value,
            total_steps=task.total_steps,
        ).info("task_queued")
        get_project_logger(project_id, self.settings.STORAGE.DATA_DIR).bind(
            task_id=task.id,
            task_type=task.type.value,
            total_steps=task.total_steps,
        ).info("task_queued")

        async def work(task_id: str, session_factory: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                await self.runtime.wait_if_paused(task_id)
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

        launch_task(task, self.runtime, self.session_factory, self.settings, work)
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
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.session_factory = session_factory
        self.dialogue_generator = dialogue_generator
        self.prompt_strategy = prompt_strategy
        self.asset_store = asset_store
        self.settings = settings
        self.projects = ProjectRepository(session)
        self.slides = SlideRepository(session)
        self.tasks = TaskRecordService(session)

    async def execute(self, project_id: str) -> str:
        await _ensure_project(self.projects, project_id)
        slides = await self.slides.list_by_project(project_id)
        task = await self.tasks.create_task(project_id, TaskType.DIALOGUE_GENERATION, max(1, len(slides)))
        global_logger.bind(
            task_id=task.id,
            project_id=project_id,
            task_type=task.type.value,
            total_steps=task.total_steps,
        ).info("task_queued")
        get_project_logger(project_id, self.settings.STORAGE.DATA_DIR).bind(
            task_id=task.id,
            task_type=task.type.value,
            total_steps=task.total_steps,
        ).info("task_queued")

        async def work(task_id: str, session_factory: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                await self.runtime.wait_if_paused(task_id)
                async with session_factory() as session:
                    await GenerateSlideDialoguesUseCase(
                        session,
                        self.dialogue_generator,
                        self.prompt_strategy,
                        self.asset_store,
                        self.settings,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(task_id, index)

        launch_task(task, self.runtime, self.session_factory, self.settings, work)
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
        global_logger.bind(
            task_id=task.id,
            project_id=project_id,
            task_type=task.type.value,
            total_steps=task.total_steps,
        ).info("task_queued")
        get_project_logger(project_id, self.settings.STORAGE.DATA_DIR).bind(
            task_id=task.id,
            task_type=task.type.value,
            total_steps=task.total_steps,
        ).info("task_queued")

        async def work(task_id: str, session_factory: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                await self.runtime.wait_if_paused(task_id)
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

        launch_task(task, self.runtime, self.session_factory, self.settings, work)
        return task.id


class QueueProjectVideoGenerationUseCase:
    """Queue full-project video generation."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        session_factory: async_sessionmaker[AsyncSession],
        asset_store: AssetStore,
        image_preprocessor: ImagePreprocessor,
        video_renderer: VideoRenderer,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.session_factory = session_factory
        self.asset_store = asset_store
        self.image_preprocessor = image_preprocessor
        self.video_renderer = video_renderer
        self.settings = settings
        self.tasks = TaskRecordService(session)

    async def execute(self, project_id: str) -> str:
        total_slide_steps = await GenerateProjectVideoUseCase(
            self.session,
            self.asset_store,
            self.image_preprocessor,
            self.video_renderer,
            self.settings,
        ).validate_inputs(project_id)
        task = await self.tasks.create_task(project_id, TaskType.VIDEO_GENERATION, total_slide_steps + 1)
        global_logger.bind(
            task_id=task.id,
            project_id=project_id,
            task_type=task.type.value,
            total_steps=task.total_steps,
        ).info("task_queued")
        get_project_logger(project_id, self.settings.STORAGE.DATA_DIR).bind(
            task_id=task.id,
            task_type=task.type.value,
            total_steps=task.total_steps,
        ).info("task_queued")

        async def work(task_id: str, session_factory: async_sessionmaker[AsyncSession]) -> None:
            async with session_factory() as session:
                await GenerateProjectVideoUseCase(
                    session,
                    self.asset_store,
                    self.image_preprocessor,
                    self.video_renderer,
                    self.settings,
                ).execute(
                    project_id,
                    on_slide_rendered=lambda step: TaskRecordService(session).mark_progress(task_id, step),
                    before_slide_render=lambda: self.runtime.wait_if_paused(task_id),
                )
                await TaskRecordService(session).mark_progress(task_id, total_slide_steps + 1)

        launch_task(task, self.runtime, self.session_factory, self.settings, work)
        return task.id


class PauseTaskUseCase:
    """Pause a running task gracefully (current slide completes before pause)."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.settings = settings
        self.tasks = TaskRecordService(session)

    async def execute(self, task_id: str) -> Task:
        task = await self.tasks.get_task(task_id)
        if task.status.value in {"completed", "failed", "cancelled", "paused"}:
            return task

        self.runtime.pause(task_id)
        await self.tasks.mark_paused(task_id)
        global_logger.bind(
            task_id=task_id,
            project_id=task.project_id,
        ).info("task_paused")
        get_project_logger(task.project_id, self.settings.STORAGE.DATA_DIR).bind(
            task_id=task_id,
        ).info("task_paused")
        return await self.tasks.get_task(task_id)


class ResumeTaskUseCase:
    """Resume a paused or failed task from its last checkpoint."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        session_factory: async_sessionmaker[AsyncSession],
        image_generator: ImageGenerator,
        dialogue_generator: DialogueGenerator,
        prompt_strategy: DialoguePromptStrategy,
        audio_synthesizer: AudioSynthesizer,
        audio_processor: AudioProcessor,
        audio_cue_strategy: AudioCueStrategy,
        image_preprocessor: ImagePreprocessor,
        video_renderer: VideoRenderer,
        asset_store: AssetStore,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.session_factory = session_factory
        self.image_generator = image_generator
        self.dialogue_generator = dialogue_generator
        self.prompt_strategy = prompt_strategy
        self.audio_synthesizer = audio_synthesizer
        self.audio_processor = audio_processor
        self.audio_cue_strategy = audio_cue_strategy
        self.image_preprocessor = image_preprocessor
        self.video_renderer = video_renderer
        self.asset_store = asset_store
        self.settings = settings
        self.tasks = TaskRecordService(session)
        self.slides = SlideRepository(session)

    async def execute(self, task_id: str) -> Task:
        task = await self.tasks.get_task(task_id)

        if task.status.value not in {"paused", "failed"}:
            return task

        project_id = task.project_id

        # Fast path: PAUSED + runtime event still alive → just unblock the coroutine
        if task.status.value == "paused" and self.runtime.resume(task_id):
            await self.tasks.mark_running(task_id)
            global_logger.bind(
                task_id=task_id,
                project_id=project_id,
            ).info("task_resumed")
            get_project_logger(project_id, self.settings.STORAGE.DATA_DIR).bind(
                task_id=task_id,
            ).info("task_resumed")
            return await self.tasks.get_task(task_id)

        # Slow path: FAILED, or PAUSED but runtime lost (server restart).
        # Rebuild the work coroutine from the checkpoint stored in current_step.
        resume_from = task.current_step
        await self.tasks.mark_running(task_id)

        slides = await self.slides.list_by_project(project_id)
        task_type = TaskType(task.type.value)

        if task_type == TaskType.IMAGE_GENERATION:
            work = self._build_image_work(project_id, slides, resume_from)
        elif task_type == TaskType.DIALOGUE_GENERATION:
            work = self._build_dialogue_work(project_id, slides, resume_from)
        elif task_type == TaskType.AUDIO_GENERATION:
            work = self._build_audio_work(project_id, slides, resume_from)
        elif task_type == TaskType.VIDEO_GENERATION:
            work = self._build_video_work(project_id, slides, resume_from)
        else:
            raise BadRequestError(f"Unknown task type: {task.type.value}")

        launch_task(task, self.runtime, self.session_factory, self.settings, work)

        global_logger.bind(
            task_id=task_id,
            project_id=project_id,
            resume_from=resume_from,
        ).info("task_resumed_from_checkpoint")
        get_project_logger(project_id, self.settings.STORAGE.DATA_DIR).bind(
            task_id=task_id,
            resume_from=resume_from,
        ).info("task_resumed_from_checkpoint")
        return await self.tasks.get_task(task_id)

    def _build_image_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        resume_from: int,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        image_generator = self.image_generator
        asset_store = self.asset_store
        session_factory = self.session_factory
        settings = self.settings

        async def work(task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides[resume_from:], start=resume_from + 1):
                await runtime.wait_if_paused(task_id)
                async with session_factory() as session:
                    await GenerateSlideImageUseCase(
                        session,
                        image_generator,
                        asset_store,
                        settings,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(task_id, index)

        return work

    def _build_dialogue_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        resume_from: int,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        dialogue_generator = self.dialogue_generator
        prompt_strategy = self.prompt_strategy
        asset_store = self.asset_store
        session_factory = self.session_factory
        settings = self.settings

        async def work(task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides[resume_from:], start=resume_from + 1):
                await runtime.wait_if_paused(task_id)
                async with session_factory() as session:
                    await GenerateSlideDialoguesUseCase(
                        session,
                        dialogue_generator,
                        prompt_strategy,
                        asset_store,
                        settings,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(task_id, index)

        return work

    def _build_audio_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        resume_from: int,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        audio_synthesizer = self.audio_synthesizer
        audio_processor = self.audio_processor
        dialogue_generator = self.dialogue_generator
        prompt_strategy = self.prompt_strategy
        audio_cue_strategy = self.audio_cue_strategy
        asset_store = self.asset_store
        session_factory = self.session_factory
        settings = self.settings

        async def work(task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides[resume_from:], start=resume_from + 1):
                await runtime.wait_if_paused(task_id)
                async with session_factory() as session:
                    await GenerateSlideAudioUseCase(
                        session,
                        asset_store,
                        audio_synthesizer,
                        audio_processor,
                        dialogue_generator,
                        prompt_strategy,
                        audio_cue_strategy,
                        settings,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(task_id, index)

        return work

    def _build_video_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        resume_from: int,  # noqa: ARG002
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        asset_store = self.asset_store
        image_preprocessor = self.image_preprocessor
        video_renderer = self.video_renderer
        session_factory = self.session_factory
        settings = self.settings
        total_steps = len(slides) + 1

        async def work(task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            async with session_factory() as session:
                await GenerateProjectVideoUseCase(
                    session,
                    asset_store,
                    image_preprocessor,
                    video_renderer,
                    settings,
                ).execute(
                    project_id,
                    on_slide_rendered=lambda step: TaskRecordService(session).mark_progress(task_id, step),
                    before_slide_render=lambda: runtime.wait_if_paused(task_id),
                )
                await TaskRecordService(session).mark_progress(task_id, total_steps)

        return work


class CancelTaskUseCase:
    """Cancel a queued or running task."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.settings = settings
        self.tasks = TaskRecordService(session)

    async def execute(self, task_id: str) -> Task:
        task = await self.tasks.get_task(task_id)
        if task.status.value in {"completed", "failed", "cancelled"}:
            return task

        self.runtime.cancel(task_id)
        await self.tasks.mark_cancelled(task_id)
        global_logger.bind(
            task_id=task_id,
            project_id=task.project_id,
        ).info("task_cancelled")
        get_project_logger(task.project_id, self.settings.STORAGE.DATA_DIR).bind(
            task_id=task_id,
        ).info("task_cancelled")
        return await self.tasks.get_task(task_id)


async def _ensure_project(projects: ProjectRepository, project_id: str) -> None:
    if await projects.get(project_id) is None:
        raise NotFoundError("Project not found")
