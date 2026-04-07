# ruff: noqa: D103, PLR0913

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Request
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
from bananalecture_backend.application.strategies import (
    AudioCueStrategy,
    DefaultAudioCueStrategy,
    DefaultDialoguePromptStrategy,
    DialoguePromptStrategy,
)
from bananalecture_backend.application.use_cases import (
    CancelTaskUseCase,
    GenerateProjectVideoUseCase,
    GenerateSlideAudioUseCase,
    GenerateSlideDialoguesUseCase,
    GenerateSlideImageUseCase,
    GetSlideImageFileUseCase,
    ModifySlideImageUseCase,
    QueueBatchAudioGenerationUseCase,
    QueueBatchDialogueGenerationUseCase,
    QueueBatchImageGenerationUseCase,
    QueueProjectVideoGenerationUseCase,
)
from bananalecture_backend.clients.audio_generation import build_audio_generation_client
from bananalecture_backend.clients.dialogue_generation import build_dialogue_generation_client
from bananalecture_backend.clients.image_generation import build_image_generation_client
from bananalecture_backend.core.config import ROOT_DIR, Settings
from bananalecture_backend.infrastructure.audio_processing import build_audio_processing_service
from bananalecture_backend.infrastructure.storage import StorageService
from bananalecture_backend.infrastructure.video_processing import build_video_processing_service
from bananalecture_backend.services.resources import (
    DialogueResourceService,
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
    """Build the dialogue generator port."""
    return build_dialogue_generation_client(settings)


def get_audio_synthesizer(settings: SettingsDep) -> AudioSynthesizer:
    """Build the audio synthesizer port."""
    return build_audio_generation_client(settings)


def get_audio_processor(settings: SettingsDep) -> AudioProcessor:
    """Build the audio processing port."""
    return build_audio_processing_service(settings)


def get_video_renderer(settings: SettingsDep) -> VideoRenderer:
    """Build the video renderer port."""
    return build_video_processing_service(settings)


def get_dialogue_prompt_strategy() -> DialoguePromptStrategy:
    """Build the dialogue prompt strategy."""
    return DefaultDialoguePromptStrategy()


def get_audio_cue_strategy() -> AudioCueStrategy:
    """Build the audio cue strategy."""
    return DefaultAudioCueStrategy(ROOT_DIR / "assets")


AssetStoreDep = Annotated[AssetStore, Depends(get_asset_store)]
ImageGeneratorDep = Annotated[ImageGenerator, Depends(get_image_generator)]
DialogueGeneratorDep = Annotated[DialogueGenerator, Depends(get_dialogue_generator)]
AudioSynthesizerDep = Annotated[AudioSynthesizer, Depends(get_audio_synthesizer)]
AudioProcessorDep = Annotated[AudioProcessor, Depends(get_audio_processor)]
VideoRendererDep = Annotated[VideoRenderer, Depends(get_video_renderer)]
DialoguePromptStrategyDep = Annotated[DialoguePromptStrategy, Depends(get_dialogue_prompt_strategy)]
AudioCueStrategyDep = Annotated[AudioCueStrategy, Depends(get_audio_cue_strategy)]


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


def get_generate_slide_image_use_case(
    session: DBSessionDep,
    image_generator: ImageGeneratorDep,
    asset_store: AssetStoreDep,
    settings: SettingsDep,
) -> GenerateSlideImageUseCase:
    return GenerateSlideImageUseCase(session, image_generator, asset_store, settings)


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


def get_generate_slide_dialogues_use_case(
    session: DBSessionDep,
    dialogue_generator: DialogueGeneratorDep,
    prompt_strategy: DialoguePromptStrategyDep,
    asset_store: AssetStoreDep,
) -> GenerateSlideDialoguesUseCase:
    return GenerateSlideDialoguesUseCase(session, dialogue_generator, prompt_strategy, asset_store)


def get_generate_slide_audio_use_case(
    session: DBSessionDep,
    asset_store: AssetStoreDep,
    audio_synthesizer: AudioSynthesizerDep,
    audio_processor: AudioProcessorDep,
    dialogue_generator: DialogueGeneratorDep,
    prompt_strategy: DialoguePromptStrategyDep,
    audio_cue_strategy: AudioCueStrategyDep,
    settings: SettingsDep,
) -> GenerateSlideAudioUseCase:
    return GenerateSlideAudioUseCase(
        session,
        asset_store,
        audio_synthesizer,
        audio_processor,
        dialogue_generator,
        prompt_strategy,
        audio_cue_strategy,
        settings,
    )


def get_generate_project_video_use_case(
    session: DBSessionDep,
    asset_store: AssetStoreDep,
    video_renderer: VideoRendererDep,
    settings: SettingsDep,
) -> GenerateProjectVideoUseCase:
    return GenerateProjectVideoUseCase(session, asset_store, video_renderer, settings)


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
    dialogue_generator: DialogueGeneratorDep,
    prompt_strategy: DialoguePromptStrategyDep,
    asset_store: AssetStoreDep,
) -> QueueBatchDialogueGenerationUseCase:
    return QueueBatchDialogueGenerationUseCase(
        context.session,
        context.runtime,
        context.session_factory,
        dialogue_generator,
        prompt_strategy,
        asset_store,
    )


def get_queue_batch_audio_generation_use_case(
    context: AppContextDep,
    asset_store: AssetStoreDep,
    audio_synthesizer: AudioSynthesizerDep,
    audio_processor: AudioProcessorDep,
    dialogue_generator: DialogueGeneratorDep,
    prompt_strategy: DialoguePromptStrategyDep,
    audio_cue_strategy: AudioCueStrategyDep,
) -> QueueBatchAudioGenerationUseCase:
    return QueueBatchAudioGenerationUseCase(
        context.session,
        context.runtime,
        context.session_factory,
        asset_store,
        audio_synthesizer,
        audio_processor,
        dialogue_generator,
        prompt_strategy,
        audio_cue_strategy,
        context.settings,
    )


def get_queue_project_video_generation_use_case(
    context: AppContextDep,
    asset_store: AssetStoreDep,
    video_renderer: VideoRendererDep,
) -> QueueProjectVideoGenerationUseCase:
    return QueueProjectVideoGenerationUseCase(
        context.session,
        context.runtime,
        context.session_factory,
        asset_store,
        video_renderer,
        context.settings,
    )


def get_cancel_task_use_case(session: DBSessionDep, runtime: RuntimeDep) -> CancelTaskUseCase:
    return CancelTaskUseCase(session, runtime)


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
