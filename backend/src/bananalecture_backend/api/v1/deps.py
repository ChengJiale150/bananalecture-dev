# ruff: noqa: D103, PLR0913

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bananalecture_backend.application.ports import (
    AssetStore,
    AudioProcessor,
    AudioSynthesizer,
    AudioTemplateClients,
    BackgroundTaskRunner,
    DialogueGenerator,
    DialogueTemplateClients,
    ImageGenerator,
    ImagePreprocessor,
    TemplateClientResolver,
    VideoRenderer,
)
from bananalecture_backend.application.strategies import (
    AudioCueStrategy,
    DefaultAudioCueStrategy,
    DefaultDialoguePromptStrategy,
    DialoguePromptStrategy,
)
from bananalecture_backend.application.use_cases import (
    CancelPipelineUseCase,
    CancelTaskUseCase,
    GenerateProjectVideoUseCase,
    GenerateSlideAudioUseCase,
    GenerateSlideDialoguesUseCase,
    GenerateSlideImageUseCase,
    GetSlideImageFileUseCase,
    ModifySlideImageUseCase,
    PausePipelineUseCase,
    PauseTaskUseCase,
    QueueBatchAudioGenerationUseCase,
    QueueBatchDialogueGenerationUseCase,
    QueueBatchImageGenerationUseCase,
    QueueProjectVideoGenerationUseCase,
    ResumePipelineUseCase,
    ResumeTaskUseCase,
    RunPipelineUseCase,
)
from bananalecture_backend.clients.audio_generation import build_audio_generation_client
from bananalecture_backend.clients.dialogue_generation import build_dialogue_generation_client
from bananalecture_backend.clients.image_generation import build_image_generation_client
from bananalecture_backend.core.config import ROOT_DIR, Settings
from bananalecture_backend.core.errors import ConfigurationError
from bananalecture_backend.core.templates import DEFAULT_TEMPLATE_ID, TemplateConfig, get_template_config
from bananalecture_backend.db.repositories import ProjectRepository
from bananalecture_backend.infrastructure.audio_processing import build_audio_processing_service
from bananalecture_backend.infrastructure.image_processing import build_image_processing_service
from bananalecture_backend.infrastructure.log_reader import LogReader
from bananalecture_backend.infrastructure.storage import StorageService
from bananalecture_backend.infrastructure.video_processing import build_video_processing_service
from bananalecture_backend.services.resources import (
    DialogueResourceService,
    GenerationSessionService,
    ProjectResourceService,
    SlideResourceService,
    TaskRecordService,
)


def get_settings(request: Request) -> Settings:
    """Read settings from application state."""
    return cast("Settings", request.app.state.settings)


def get_runtime(request: Request) -> BackgroundTaskRunner:
    """Read task runtime from application state."""
    return cast("BackgroundTaskRunner", request.app.state.task_runtime)


def get_storage(request: Request) -> StorageService:
    """Read storage service from application state."""
    return cast("StorageService", request.app.state.storage)


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """Read session factory from application state."""
    return cast("async_sessionmaker[AsyncSession]", request.app.state.database.session_factory)


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """Open a database session for the request."""
    async with request.app.state.database.session_factory() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RuntimeDep = Annotated[BackgroundTaskRunner, Depends(get_runtime)]
StorageDep = Annotated[StorageService, Depends(get_storage)]
SessionFactoryDep = Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)]


def get_current_user_id(request: Request) -> str:
    """Extract user identity from X-User-Id header.

    Raises 401 if the header is missing. No fallback to a default user.
    """
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )
    return user_id


CurrentUserIdDep = Annotated[str, Depends(get_current_user_id)]


def require_admin(current_user_id: str, settings: Settings) -> None:
    """Raise 403 if the current user is not in the admin list."""
    if current_user_id not in settings.SYSTEM.ADMIN_USER_IDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


def get_log_reader() -> LogReader:
    """Build a log reader instance."""
    return LogReader()


LogReaderDep = Annotated[LogReader, Depends(get_log_reader)]


@dataclass
class AppContext:
    """Shared request-scoped services for endpoints."""

    session: AsyncSession
    settings: Settings
    runtime: BackgroundTaskRunner
    storage: StorageService
    session_factory: async_sessionmaker[AsyncSession]


async def get_app_context(
    session: DBSessionDep,
    settings: SettingsDep,
    runtime: RuntimeDep,
    storage: StorageDep,
    session_factory: SessionFactoryDep,
) -> AppContext:
    """Build a request-scoped application context."""
    return AppContext(
        session=session,
        settings=settings,
        runtime=runtime,
        storage=storage,
        session_factory=session_factory,
    )


AppContextDep = Annotated[AppContext, Depends(get_app_context)]


def get_asset_store(storage: StorageDep) -> AssetStore:
    """Build the application asset store port."""
    return storage


def get_image_generator(settings: SettingsDep) -> ImageGenerator:
    """Build the image generator port."""
    return build_image_generation_client(settings)


def get_dialogue_generator(settings: SettingsDep) -> DialogueGenerator:
    """Build the dialogue generator port (uses default doraemon template)."""
    config = get_template_config(DEFAULT_TEMPLATE_ID)
    if config is None:
        msg = f"Default template {DEFAULT_TEMPLATE_ID!r} not found"
        raise ConfigurationError(msg)
    return build_dialogue_generation_client(settings, config)


def get_audio_synthesizer(settings: SettingsDep) -> AudioSynthesizer:
    """Build the audio synthesizer port (uses default doraemon template)."""
    config = get_template_config(DEFAULT_TEMPLATE_ID)
    if config is None:
        msg = f"Default template {DEFAULT_TEMPLATE_ID!r} not found"
        raise ConfigurationError(msg)
    return build_audio_generation_client(settings, config.voice_groups)


def get_audio_processor(settings: SettingsDep) -> AudioProcessor:
    """Build the audio processing port."""
    return build_audio_processing_service(settings)


def get_video_renderer(settings: SettingsDep) -> VideoRenderer:
    """Build the video renderer port."""
    return build_video_processing_service(settings)


def get_image_preprocessor() -> ImagePreprocessor:
    """Build the image preprocessor port."""
    return build_image_processing_service()


def get_dialogue_prompt_strategy() -> DialoguePromptStrategy:
    """Build the default dialogue prompt strategy (doraemon)."""
    config = get_template_config(DEFAULT_TEMPLATE_ID)
    if config is None:
        msg = f"Default template {DEFAULT_TEMPLATE_ID!r} not found"
        raise ConfigurationError(msg)
    return DefaultDialoguePromptStrategy(config.cue_config)


def get_audio_cue_strategy() -> AudioCueStrategy:
    """Build the default audio cue strategy (doraemon)."""
    config = get_template_config(DEFAULT_TEMPLATE_ID)
    if config is None:
        msg = f"Default template {DEFAULT_TEMPLATE_ID!r} not found"
        raise ConfigurationError(msg)
    return DefaultAudioCueStrategy(ROOT_DIR / "assets" / config.assets_dir, config.cue_config)


AssetStoreDep = Annotated[AssetStore, Depends(get_asset_store)]
ImageGeneratorDep = Annotated[ImageGenerator, Depends(get_image_generator)]
DialogueGeneratorDep = Annotated[DialogueGenerator, Depends(get_dialogue_generator)]
AudioSynthesizerDep = Annotated[AudioSynthesizer, Depends(get_audio_synthesizer)]
AudioProcessorDep = Annotated[AudioProcessor, Depends(get_audio_processor)]
VideoRendererDep = Annotated[VideoRenderer, Depends(get_video_renderer)]
ImagePreprocessorDep = Annotated[ImagePreprocessor, Depends(get_image_preprocessor)]
DialoguePromptStrategyDep = Annotated[DialoguePromptStrategy, Depends(get_dialogue_prompt_strategy)]
AudioCueStrategyDep = Annotated[AudioCueStrategy, Depends(get_audio_cue_strategy)]


class SettingsTemplateClientResolver:
    """Resolve template-specific clients, reusing defaults for the default template."""

    def __init__(
        self,
        settings: Settings,
        default_dialogue_generator: DialogueGenerator,
        default_prompt_strategy: DialoguePromptStrategy,
        default_audio_synthesizer: AudioSynthesizer,
        default_audio_cue_strategy: AudioCueStrategy,
    ) -> None:
        """Store settings and default-template clients for reuse."""
        self.settings = settings
        self.default_dialogue_generator = default_dialogue_generator
        self.default_prompt_strategy = default_prompt_strategy
        self.default_audio_synthesizer = default_audio_synthesizer
        self.default_audio_cue_strategy = default_audio_cue_strategy

    def resolve_dialogue_clients(self, template: TemplateConfig | None) -> DialogueTemplateClients:
        """Resolve dialogue generator and prompt strategy for a template."""
        if template is None or template.id == DEFAULT_TEMPLATE_ID:
            return DialogueTemplateClients(
                dialogue_generator=self.default_dialogue_generator,
                prompt_strategy=self.default_prompt_strategy,
            )
        return DialogueTemplateClients(
            dialogue_generator=build_dialogue_generation_client(self.settings, template),
            prompt_strategy=DefaultDialoguePromptStrategy(template.cue_config),
        )

    def resolve_audio_clients(self, template: TemplateConfig | None) -> AudioTemplateClients:
        """Resolve audio clients and strategies for a template."""
        if template is None or template.id == DEFAULT_TEMPLATE_ID:
            return AudioTemplateClients(
                audio_synthesizer=self.default_audio_synthesizer,
                dialogue_generator=self.default_dialogue_generator,
                dialogue_prompt_strategy=self.default_prompt_strategy,
                audio_cue_strategy=self.default_audio_cue_strategy,
            )
        return AudioTemplateClients(
            audio_synthesizer=build_audio_generation_client(self.settings, template.voice_groups),
            dialogue_generator=build_dialogue_generation_client(self.settings, template),
            dialogue_prompt_strategy=DefaultDialoguePromptStrategy(template.cue_config),
            audio_cue_strategy=DefaultAudioCueStrategy(
                ROOT_DIR / "assets" / template.assets_dir,
                template.cue_config,
            ),
        )


def get_template_client_resolver(
    settings: SettingsDep,
    dialogue_generator: DialogueGeneratorDep,
    prompt_strategy: DialoguePromptStrategyDep,
    audio_synthesizer: AudioSynthesizerDep,
    audio_cue_strategy: AudioCueStrategyDep,
) -> TemplateClientResolver:
    """Build the template client resolver port."""
    return SettingsTemplateClientResolver(
        settings,
        dialogue_generator,
        prompt_strategy,
        audio_synthesizer,
        audio_cue_strategy,
    )


TemplateClientResolverDep = Annotated[TemplateClientResolver, Depends(get_template_client_resolver)]


async def _get_project_template(session: AsyncSession, project_id: str) -> TemplateConfig | None:
    """Read the project's template configuration (None when the project is missing)."""
    project = await ProjectRepository(session).get(project_id)
    if project is None:
        return None
    return get_template_config(project.template_id or DEFAULT_TEMPLATE_ID)


def get_project_resource_service(session: DBSessionDep) -> ProjectResourceService:
    return ProjectResourceService(session)


def get_slide_resource_service(session: DBSessionDep) -> SlideResourceService:
    return SlideResourceService(session)


def get_dialogue_resource_service(session: DBSessionDep) -> DialogueResourceService:
    return DialogueResourceService(session)


def get_task_record_service(session: DBSessionDep) -> TaskRecordService:
    return TaskRecordService(session)


ProjectResourceServiceDep = Annotated[ProjectResourceService, Depends(get_project_resource_service)]
SlideResourceServiceDep = Annotated[SlideResourceService, Depends(get_slide_resource_service)]
DialogueResourceServiceDep = Annotated[DialogueResourceService, Depends(get_dialogue_resource_service)]
TaskRecordServiceDep = Annotated[TaskRecordService, Depends(get_task_record_service)]


async def get_generate_slide_image_use_case(
    project_id: str,
    session: DBSessionDep,
    image_generator: ImageGeneratorDep,
    asset_store: AssetStoreDep,
    settings: SettingsDep,
) -> GenerateSlideImageUseCase:
    template = await _get_project_template(session, project_id)
    return GenerateSlideImageUseCase(session, image_generator, asset_store, settings, template)


def get_modify_slide_image_use_case(
    session: DBSessionDep,
    image_generator: ImageGeneratorDep,
    asset_store: AssetStoreDep,
    settings: SettingsDep,
) -> ModifySlideImageUseCase:
    return ModifySlideImageUseCase(session, image_generator, asset_store, settings)


def get_slide_image_file_use_case(
    service: SlideResourceServiceDep,
    asset_store: AssetStoreDep,
    settings: SettingsDep,
) -> GetSlideImageFileUseCase:
    return GetSlideImageFileUseCase(service, asset_store, settings)


async def get_generate_slide_dialogues_use_case(
    project_id: str,
    session: DBSessionDep,
    template_client_resolver: TemplateClientResolverDep,
    asset_store: AssetStoreDep,
    settings: SettingsDep,
) -> GenerateSlideDialoguesUseCase:
    template = await _get_project_template(session, project_id)
    clients = template_client_resolver.resolve_dialogue_clients(template)
    return GenerateSlideDialoguesUseCase(
        session,
        clients.dialogue_generator,
        clients.prompt_strategy,
        asset_store,
        settings,
    )


async def get_generate_slide_audio_use_case(
    project_id: str,
    session: DBSessionDep,
    asset_store: AssetStoreDep,
    audio_processor: AudioProcessorDep,
    template_client_resolver: TemplateClientResolverDep,
    settings: SettingsDep,
) -> GenerateSlideAudioUseCase:
    template = await _get_project_template(session, project_id)
    clients = template_client_resolver.resolve_audio_clients(template)
    return GenerateSlideAudioUseCase(
        session,
        asset_store,
        clients.audio_synthesizer,
        audio_processor,
        clients.dialogue_generator,
        clients.dialogue_prompt_strategy,
        clients.audio_cue_strategy,
        settings,
    )


def get_generate_project_video_use_case(
    session: DBSessionDep,
    asset_store: AssetStoreDep,
    image_preprocessor: ImagePreprocessorDep,
    video_renderer: VideoRendererDep,
    settings: SettingsDep,
) -> GenerateProjectVideoUseCase:
    return GenerateProjectVideoUseCase(session, asset_store, image_preprocessor, video_renderer, settings)


def get_queue_batch_image_generation_use_case(
    context: AppContextDep,
    image_generator: ImageGeneratorDep,
    asset_store: AssetStoreDep,
) -> QueueBatchImageGenerationUseCase:
    return QueueBatchImageGenerationUseCase(
        context.session,
        context.runtime,
        context.session_factory,
        image_generator,
        asset_store,
        context.settings,
    )


def get_queue_batch_dialogue_generation_use_case(
    context: AppContextDep,
    asset_store: AssetStoreDep,
    template_client_resolver: TemplateClientResolverDep,
) -> QueueBatchDialogueGenerationUseCase:
    return QueueBatchDialogueGenerationUseCase(
        context.session,
        context.runtime,
        context.session_factory,
        asset_store,
        template_client_resolver,
        context.settings,
    )


def get_queue_batch_audio_generation_use_case(
    context: AppContextDep,
    asset_store: AssetStoreDep,
    audio_processor: AudioProcessorDep,
    template_client_resolver: TemplateClientResolverDep,
) -> QueueBatchAudioGenerationUseCase:
    return QueueBatchAudioGenerationUseCase(
        context.session,
        context.runtime,
        context.session_factory,
        asset_store,
        audio_processor,
        template_client_resolver,
        context.settings,
    )


def get_queue_project_video_generation_use_case(
    context: AppContextDep,
    asset_store: AssetStoreDep,
    image_preprocessor: ImagePreprocessorDep,
    video_renderer: VideoRendererDep,
) -> QueueProjectVideoGenerationUseCase:
    return QueueProjectVideoGenerationUseCase(
        context.session,
        context.runtime,
        context.session_factory,
        asset_store,
        image_preprocessor,
        video_renderer,
        context.settings,
    )


def get_cancel_task_use_case(
    session: DBSessionDep,
    runtime: RuntimeDep,
    settings: SettingsDep,
) -> CancelTaskUseCase:
    return CancelTaskUseCase(session, runtime, settings)


def get_pause_task_use_case(
    session: DBSessionDep,
    runtime: RuntimeDep,
    settings: SettingsDep,
) -> PauseTaskUseCase:
    return PauseTaskUseCase(session, runtime, settings)


def get_resume_task_use_case(
    context: AppContextDep,
    image_generator: ImageGeneratorDep,
    audio_processor: AudioProcessorDep,
    image_preprocessor: ImagePreprocessorDep,
    video_renderer: VideoRendererDep,
    asset_store: AssetStoreDep,
    template_client_resolver: TemplateClientResolverDep,
) -> ResumeTaskUseCase:
    return ResumeTaskUseCase(
        context.session,
        context.runtime,
        context.session_factory,
        image_generator,
        audio_processor,
        image_preprocessor,
        video_renderer,
        asset_store,
        template_client_resolver,
        context.settings,
    )


GenerateSlideImageUseCaseDep = Annotated[GenerateSlideImageUseCase, Depends(get_generate_slide_image_use_case)]
ModifySlideImageUseCaseDep = Annotated[ModifySlideImageUseCase, Depends(get_modify_slide_image_use_case)]
GetSlideImageFileUseCaseDep = Annotated[GetSlideImageFileUseCase, Depends(get_slide_image_file_use_case)]
GenerateSlideDialoguesUseCaseDep = Annotated[
    GenerateSlideDialoguesUseCase,
    Depends(get_generate_slide_dialogues_use_case),
]
GenerateSlideAudioUseCaseDep = Annotated[GenerateSlideAudioUseCase, Depends(get_generate_slide_audio_use_case)]
GenerateProjectVideoUseCaseDep = Annotated[
    GenerateProjectVideoUseCase,
    Depends(get_generate_project_video_use_case),
]
QueueBatchImageGenerationUseCaseDep = Annotated[
    QueueBatchImageGenerationUseCase,
    Depends(get_queue_batch_image_generation_use_case),
]
QueueBatchDialogueGenerationUseCaseDep = Annotated[
    QueueBatchDialogueGenerationUseCase,
    Depends(get_queue_batch_dialogue_generation_use_case),
]
QueueBatchAudioGenerationUseCaseDep = Annotated[
    QueueBatchAudioGenerationUseCase,
    Depends(get_queue_batch_audio_generation_use_case),
]
QueueProjectVideoGenerationUseCaseDep = Annotated[
    QueueProjectVideoGenerationUseCase,
    Depends(get_queue_project_video_generation_use_case),
]
CancelTaskUseCaseDep = Annotated[CancelTaskUseCase, Depends(get_cancel_task_use_case)]
PauseTaskUseCaseDep = Annotated[PauseTaskUseCase, Depends(get_pause_task_use_case)]
ResumeTaskUseCaseDep = Annotated[ResumeTaskUseCase, Depends(get_resume_task_use_case)]


# ── Generation Session Service ──


def get_generation_session_service(session: DBSessionDep) -> GenerationSessionService:
    return GenerationSessionService(session)


GenerationSessionServiceDep = Annotated[GenerationSessionService, Depends(get_generation_session_service)]


# ── Pipeline Use Cases ──


def get_run_pipeline_use_case(
    runtime: RuntimeDep,
    session_factory: SessionFactoryDep,
    image_generator: ImageGeneratorDep,
    audio_processor: AudioProcessorDep,
    image_preprocessor: ImagePreprocessorDep,
    video_renderer: VideoRendererDep,
    asset_store: AssetStoreDep,
    template_client_resolver: TemplateClientResolverDep,
    settings: SettingsDep,
) -> RunPipelineUseCase:
    return RunPipelineUseCase(
        runtime,
        session_factory,
        image_generator,
        audio_processor,
        image_preprocessor,
        video_renderer,
        asset_store,
        template_client_resolver,
        settings,
    )


def get_pause_pipeline_use_case(
    session: DBSessionDep,
    runtime: RuntimeDep,
    settings: SettingsDep,
) -> PausePipelineUseCase:
    return PausePipelineUseCase(session, runtime, settings)


def get_resume_pipeline_use_case(
    context: AppContextDep,
    image_generator: ImageGeneratorDep,
    audio_processor: AudioProcessorDep,
    image_preprocessor: ImagePreprocessorDep,
    video_renderer: VideoRendererDep,
    asset_store: AssetStoreDep,
    template_client_resolver: TemplateClientResolverDep,
) -> ResumePipelineUseCase:
    return ResumePipelineUseCase(
        context.session,
        context.runtime,
        context.session_factory,
        image_generator,
        audio_processor,
        image_preprocessor,
        video_renderer,
        asset_store,
        template_client_resolver,
        context.settings,
    )


def get_cancel_pipeline_use_case(
    session: DBSessionDep,
    runtime: RuntimeDep,
    settings: SettingsDep,
) -> CancelPipelineUseCase:
    return CancelPipelineUseCase(session, runtime, settings)


RunPipelineUseCaseDep = Annotated[RunPipelineUseCase, Depends(get_run_pipeline_use_case)]
PausePipelineUseCaseDep = Annotated[PausePipelineUseCase, Depends(get_pause_pipeline_use_case)]
ResumePipelineUseCaseDep = Annotated[ResumePipelineUseCase, Depends(get_resume_pipeline_use_case)]
CancelPipelineUseCaseDep = Annotated[CancelPipelineUseCase, Depends(get_cancel_pipeline_use_case)]
