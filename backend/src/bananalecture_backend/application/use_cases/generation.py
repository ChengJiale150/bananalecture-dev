# ruff: noqa: ARG002, C901, D102, D107, EM101, EM102, F401, PLR0913, PLR2004, TC001, TRY003

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from bananalecture_backend.application.use_cases.tasks import launch_task
from bananalecture_backend.core.config import Settings
from bananalecture_backend.core.errors import BadRequestError, NotFoundError
from bananalecture_backend.core.logging_config import get_global_logger, get_project_logger
from bananalecture_backend.db.repositories import SlideRepository
from bananalecture_backend.models.entities import SlideModel
from bananalecture_backend.schemas.generation import GenerationSessionResponse
from bananalecture_backend.schemas.task import Task, TaskType
from bananalecture_backend.services.resources import GenerationSessionService, TaskRecordService

_WorkBuilder = Callable[
    [str, list[SlideModel], str],
    Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]],
]

global_logger = get_global_logger()


class RunPipelineUseCase:
    """Create and run a generation pipeline (images → dialogues → audio → video)."""

    def __init__(
        self,
        runtime: BackgroundTaskRunner,
        session_factory: async_sessionmaker[AsyncSession],
        image_generator: ImageGenerator,
        dialogue_generator: DialogueGenerator,
        prompt_strategy: DialoguePromptStrategy,
        audio_synthesizer: AudioSynthesizer,
        audio_processor: AudioProcessor,
        audio_cue_strategy: AudioCueStrategy,
        video_renderer: VideoRenderer,
        asset_store: AssetStore,
        settings: Settings,
    ) -> None:
        self.runtime = runtime
        self.session_factory = session_factory
        self.image_generator = image_generator
        self.dialogue_generator = dialogue_generator
        self.prompt_strategy = prompt_strategy
        self.audio_synthesizer = audio_synthesizer
        self.audio_processor = audio_processor
        self.audio_cue_strategy = audio_cue_strategy
        self.video_renderer = video_renderer
        self.asset_store = asset_store
        self.settings = settings

    async def execute(self, project_id: str) -> str:
        async with self.session_factory() as session:
            sessions_svc = GenerationSessionService(session)
            slides_repo = SlideRepository(session)

            existing = await sessions_svc.get_active_by_project(project_id)
            if existing and existing.status in ("running", "paused"):
                raise BadRequestError("已有进行中的生成会话")

            slides = await slides_repo.list_by_project(project_id)
            if not slides:
                raise BadRequestError("项目没有幻灯片")

            session_obj = await sessions_svc.create_session(project_id)
            slides_list = slides

        async def pipeline_runner() -> None:
            try:
                await self._run_pipeline(session_obj.id, project_id, slides_list)
            except asyncio.CancelledError:
                async with self.session_factory() as s:
                    await GenerationSessionService(s).mark_cancelled(session_obj.id)
                global_logger.bind(
                    session_id=session_obj.id,
                    project_id=project_id,
                ).info("pipeline_cancelled")
                raise

        self.runtime.start(session_obj.id, pipeline_runner())

        global_logger.bind(
            session_id=session_obj.id,
            project_id=project_id,
        ).info("pipeline_started")

        return session_obj.id

    async def _run_pipeline(
        self,
        session_id: str,
        project_id: str,
        slides: list[SlideModel],
    ) -> None:
        phases: list[tuple[str, TaskType, _WorkBuilder]] = [
            ("images", TaskType.IMAGE_GENERATION, self._build_image_work),
            ("dialogues", TaskType.DIALOGUE_GENERATION, self._build_dialogue_work),
            ("audio", TaskType.AUDIO_GENERATION, self._build_audio_work),
            ("video", TaskType.VIDEO_GENERATION, self._build_video_work),
        ]

        for idx, (name, task_type, build_work) in enumerate(phases):
            async with self.session_factory() as s:
                await GenerationSessionService(s).mark_phase(session_id, idx)

            total_steps = max(1, len(slides)) if task_type != TaskType.VIDEO_GENERATION else len(slides) + 1
            async with self.session_factory() as s:
                task = await TaskRecordService(s).create_task(project_id, task_type, total_steps)
            async with self.session_factory() as s:
                await GenerationSessionService(s).mark_phase(session_id, idx, task_id=task.id)

            work = build_work(project_id, slides, task.id)
            launch_task(task, self.runtime, self.session_factory, self.settings, work)

            while True:
                await self.runtime.wait_if_paused(session_id)
                await asyncio.sleep(0.5)
                async with self.session_factory() as s:
                    t = await TaskRecordService(s).get_task(task.id)
                if t.status in ("completed", "failed", "cancelled"):
                    break

            if t.status != "completed":
                async with self.session_factory() as s:
                    await GenerationSessionService(s).mark_failed(
                        session_id, t.error_message or f"{name} generation failed"
                    )
                global_logger.bind(
                    session_id=session_id,
                    project_id=project_id,
                    phase=name,
                    status=t.status,
                    error=t.error_message,
                ).error("pipeline_phase_failed")
                return

            global_logger.bind(
                session_id=session_id,
                project_id=project_id,
                phase=name,
            ).info("pipeline_phase_completed")

        async with self.session_factory() as s:
            await GenerationSessionService(s).mark_completed(session_id)
        global_logger.bind(
            session_id=session_id,
            project_id=project_id,
        ).info("pipeline_completed")

    def _build_image_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        task_id: str,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        image_generator = self.image_generator
        asset_store = self.asset_store
        session_factory = self.session_factory
        settings = self.settings

        async def work(_task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                await runtime.wait_if_paused(_task_id)
                async with session_factory() as session:
                    await GenerateSlideImageUseCase(
                        session,
                        image_generator,
                        asset_store,
                        settings,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(_task_id, index)

        return work

    def _build_dialogue_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        task_id: str,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        dialogue_generator = self.dialogue_generator
        prompt_strategy = self.prompt_strategy
        asset_store = self.asset_store
        session_factory = self.session_factory
        settings = self.settings

        async def work(_task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                await runtime.wait_if_paused(_task_id)
                async with session_factory() as session:
                    await GenerateSlideDialoguesUseCase(
                        session,
                        dialogue_generator,
                        prompt_strategy,
                        asset_store,
                        settings,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(_task_id, index)

        return work

    def _build_audio_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        task_id: str,
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

        async def work(_task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                await runtime.wait_if_paused(_task_id)
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
                    await TaskRecordService(session).mark_progress(_task_id, index)

        return work

    def _build_video_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        task_id: str,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        asset_store = self.asset_store
        video_renderer = self.video_renderer
        session_factory = self.session_factory
        settings = self.settings
        total_steps = len(slides) + 1

        async def work(_task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            async with session_factory() as session:
                await GenerateProjectVideoUseCase(
                    session,
                    asset_store,
                    video_renderer,
                    settings,
                ).execute(
                    project_id,
                    on_slide_rendered=lambda step: TaskRecordService(session).mark_progress(_task_id, step),
                    before_slide_render=lambda: runtime.wait_if_paused(_task_id),
                )
                await TaskRecordService(session).mark_progress(_task_id, total_steps)

        return work


class PausePipelineUseCase:
    """Pause a running generation pipeline."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.settings = settings
        self.sessions = GenerationSessionService(session)
        self.tasks = TaskRecordService(session)

    async def execute(self, project_id: str) -> GenerationSessionResponse:
        session_obj = await self.sessions.get_active_by_project(project_id)
        if session_obj is None:
            raise NotFoundError("No active generation session")

        if session_obj.status in ("completed", "failed", "cancelled", "paused"):
            return await self.sessions.build_response(session_obj.id)

        self.runtime.pause(session_obj.id)

        if session_obj.current_task_id:
            self.runtime.pause(session_obj.current_task_id)

        await self.sessions.mark_paused(session_obj.id)

        global_logger.bind(
            session_id=session_obj.id,
            project_id=project_id,
        ).info("pipeline_paused")

        return await self.sessions.build_response(session_obj.id)


class ResumePipelineUseCase:
    """Resume a paused or failed generation pipeline."""

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
        self.video_renderer = video_renderer
        self.asset_store = asset_store
        self.settings = settings
        self.sessions = GenerationSessionService(session)
        self.slides = SlideRepository(session)
        self.tasks = TaskRecordService(session)

    async def execute(self, project_id: str) -> GenerationSessionResponse:
        session_obj = await self.sessions.get_active_by_project(project_id)
        if session_obj is None:
            raise NotFoundError("No generation session to resume")

        if session_obj.status == "completed":
            return await self.sessions.build_response(session_obj.id)

        # Fast path: PAUSED + runtime event still alive
        if session_obj.status == "paused" and self.runtime.resume(session_obj.id):
            if session_obj.current_task_id:
                self.runtime.resume(session_obj.current_task_id)
            await self.sessions.mark_running(session_obj.id)
            global_logger.bind(
                session_id=session_obj.id,
                project_id=project_id,
            ).info("pipeline_resumed_fast")
            return await self.sessions.build_response(session_obj.id)

        # Slow path: server restart or failed task
        resume_from = session_obj.current_phase

        # Check current task status if exists
        if session_obj.current_task_id:
            async with self.session_factory() as s:
                try:
                    task = await TaskRecordService(s).get_task(session_obj.current_task_id)
                except NotFoundError:
                    task = None

            if task and task.status == "completed":
                resume_from = session_obj.current_phase + 1
            elif task and task.status in ("running", "paused"):
                # Task coroutine lost, rebuild it
                slides = await self.slides.list_by_project(project_id)
                work = self._rebuild_task_work(
                    task.type,
                    project_id,
                    slides,
                    task.id,
                )
                launch_task(task, self.runtime, self.session_factory, self.settings, work)
            elif task and task.status == "failed":
                # Failed task — mark pipeline failed, let user decide
                await self.sessions.mark_failed(session_obj.id, task.error_message or "Pipeline task failed")
                return await self.sessions.build_response(session_obj.id)

        if resume_from >= 4:
            await self.sessions.mark_completed(session_obj.id)
            return await self.sessions.build_response(session_obj.id)

        # Rebuild pipeline runner from resume_from
        slides = await self.slides.list_by_project(project_id)
        await self.sessions.mark_running(session_obj.id)

        async def pipeline_runner() -> None:
            try:
                await self._run_pipeline_from(session_obj.id, project_id, slides, resume_from)
            except asyncio.CancelledError:
                async with self.session_factory() as s:
                    await GenerationSessionService(s).mark_cancelled(session_obj.id)
                raise

        self.runtime.start(session_obj.id, pipeline_runner())

        global_logger.bind(
            session_id=session_obj.id,
            project_id=project_id,
            resume_from=resume_from,
        ).info("pipeline_resumed_slow")

        return await self.sessions.build_response(session_obj.id)

    async def _run_pipeline_from(
        self,
        session_id: str,
        project_id: str,
        slides: list[SlideModel],
        start_phase: int,
    ) -> None:
        phases: list[tuple[str, TaskType, _WorkBuilder]] = [
            ("images", TaskType.IMAGE_GENERATION, self._build_image_work),
            ("dialogues", TaskType.DIALOGUE_GENERATION, self._build_dialogue_work),
            ("audio", TaskType.AUDIO_GENERATION, self._build_audio_work),
            ("video", TaskType.VIDEO_GENERATION, self._build_video_work),
        ]

        for idx in range(start_phase, 4):
            name, task_type, build_work = phases[idx]
            async with self.session_factory() as s:
                await GenerationSessionService(s).mark_phase(session_id, idx)

            total_steps = max(1, len(slides)) if task_type != TaskType.VIDEO_GENERATION else len(slides) + 1
            async with self.session_factory() as s:
                task = await TaskRecordService(s).create_task(project_id, task_type, total_steps)
            async with self.session_factory() as s:
                await GenerationSessionService(s).mark_phase(session_id, idx, task_id=task.id)

            work = build_work(project_id, slides, task.id)
            launch_task(task, self.runtime, self.session_factory, self.settings, work)

            while True:
                await self.runtime.wait_if_paused(session_id)
                await asyncio.sleep(0.5)
                async with self.session_factory() as s:
                    t = await TaskRecordService(s).get_task(task.id)
                if t.status in ("completed", "failed", "cancelled"):
                    break

            if t.status != "completed":
                async with self.session_factory() as s:
                    await GenerationSessionService(s).mark_failed(
                        session_id, t.error_message or f"{name} generation failed"
                    )
                return

        async with self.session_factory() as s:
            await GenerationSessionService(s).mark_completed(session_id)

    def _rebuild_task_work(
        self,
        task_type: str,
        project_id: str,
        slides: list[SlideModel],
        task_id: str,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        type_map = {
            TaskType.IMAGE_GENERATION.value: self._build_image_work,
            TaskType.DIALOGUE_GENERATION.value: self._build_dialogue_work,
            TaskType.AUDIO_GENERATION.value: self._build_audio_work,
            TaskType.VIDEO_GENERATION.value: self._build_video_work,
        }
        builder = type_map.get(task_type)
        if builder is None:
            raise BadRequestError(f"Unknown task type: {task_type}")
        return builder(project_id, slides, task_id)

    def _build_image_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        task_id: str,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        image_generator = self.image_generator
        asset_store = self.asset_store
        session_factory = self.session_factory
        settings = self.settings

        async def work(_task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                await runtime.wait_if_paused(_task_id)
                async with session_factory() as session:
                    await GenerateSlideImageUseCase(
                        session,
                        image_generator,
                        asset_store,
                        settings,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(_task_id, index)

        return work

    def _build_dialogue_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        task_id: str,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        dialogue_generator = self.dialogue_generator
        prompt_strategy = self.prompt_strategy
        asset_store = self.asset_store
        session_factory = self.session_factory
        settings = self.settings

        async def work(_task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                await runtime.wait_if_paused(_task_id)
                async with session_factory() as session:
                    await GenerateSlideDialoguesUseCase(
                        session,
                        dialogue_generator,
                        prompt_strategy,
                        asset_store,
                        settings,
                    ).execute(project_id, slide.id)
                    await TaskRecordService(session).mark_progress(_task_id, index)

        return work

    def _build_audio_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        task_id: str,
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

        async def work(_task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            for index, slide in enumerate(slides, start=1):
                await runtime.wait_if_paused(_task_id)
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
                    await TaskRecordService(session).mark_progress(_task_id, index)

        return work

    def _build_video_work(
        self,
        project_id: str,
        slides: list[SlideModel],
        task_id: str,
    ) -> Callable[[str, async_sessionmaker[AsyncSession]], Awaitable[None]]:
        runtime = self.runtime
        asset_store = self.asset_store
        video_renderer = self.video_renderer
        session_factory = self.session_factory
        settings = self.settings
        total_steps = len(slides) + 1

        async def work(_task_id: str, _: async_sessionmaker[AsyncSession]) -> None:
            async with session_factory() as session:
                await GenerateProjectVideoUseCase(
                    session,
                    asset_store,
                    video_renderer,
                    settings,
                ).execute(
                    project_id,
                    on_slide_rendered=lambda step: TaskRecordService(session).mark_progress(_task_id, step),
                    before_slide_render=lambda: runtime.wait_if_paused(_task_id),
                )
                await TaskRecordService(session).mark_progress(_task_id, total_steps)

        return work


class CancelPipelineUseCase:
    """Cancel a running or paused generation pipeline."""

    def __init__(
        self,
        session: AsyncSession,
        runtime: BackgroundTaskRunner,
        settings: Settings,
    ) -> None:
        self.session = session
        self.runtime = runtime
        self.settings = settings
        self.sessions = GenerationSessionService(session)

    async def execute(self, project_id: str) -> GenerationSessionResponse:
        session_obj = await self.sessions.get_active_by_project(project_id)
        if session_obj is None:
            raise NotFoundError("No active generation session")

        if session_obj.status in ("completed", "failed", "cancelled"):
            return await self.sessions.build_response(session_obj.id)

        if session_obj.current_task_id:
            self.runtime.cancel(session_obj.current_task_id)

        self.runtime.cancel(session_obj.id)
        await self.sessions.mark_cancelled(session_obj.id)

        global_logger.bind(
            session_id=session_obj.id,
            project_id=project_id,
        ).info("pipeline_cancelled")

        return await self.sessions.build_response(session_obj.id)
