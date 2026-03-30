from __future__ import annotations

import asyncio
from io import BytesIO
import time
from pathlib import Path

import pytest
from PIL import Image

from bananalecture_backend.application.use_cases import (
    GenerateProjectVideoUseCase,
    GenerateSlideAudioUseCase,
    GetSlideImageFileUseCase,
    QueueProjectVideoGenerationUseCase,
)
from bananalecture_backend.application.strategies import DefaultAudioCueStrategy, DefaultDialoguePromptStrategy
from bananalecture_backend.core.config import ImageDeliverySettings, ROOT_DIR, Settings
from bananalecture_backend.core.errors import BadRequestError, ExternalServiceError, NotFoundError
from bananalecture_backend.db.repositories import DialogueRepository, ProjectRepository, SlideRepository, TaskRepository
from bananalecture_backend.infrastructure.storage import StorageService
from bananalecture_backend.infrastructure.storage_layout import StorageLayout
from bananalecture_backend.infrastructure.task_runtime import InMemoryBackgroundTaskRunner
from bananalecture_backend.schemas.dialogue import AddDialogueRequest, DialogueEmotion, DialogueRole, DialogueSpeed
from bananalecture_backend.schemas.project import CreateProjectRequest
from bananalecture_backend.schemas.slide import SlideCreate, SlideType
from bananalecture_backend.services.resources import (
    DialogueResourceService,
    ProjectResourceService,
    SlideResourceService,
)


class FakeAudioGenerationClient:
    """In-memory audio generator used by media service tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def generate_audio(self, text: str, role: str, emotion: str, speed: str) -> bytes:
        self.calls.append(
            {
                "text": text,
                "role": role,
                "emotion": emotion,
                "speed": speed,
            }
        )
        return f"{role}:{text}".encode("utf-8")


class FakeAudioProcessingService:
    """Record concat operations and emit deterministic output files."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str]] = []

    async def concatenate_mp3_files(self, inputs: list[Path], output: Path) -> None:
        self.calls.append(([path.name for path in inputs], output.name))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"|".join(path.read_bytes() for path in inputs))


class FakeVideoProcessingService:
    """Record slide clip rendering and final concatenation."""

    def __init__(self) -> None:
        self.render_calls: list[tuple[str, str, str]] = []
        self.concat_calls: list[tuple[list[str], str]] = []

    async def render_static_slide_clip(self, image: Path, audio: Path, output: Path) -> None:
        self.render_calls.append((image.name, audio.name, output.name))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(image.read_bytes() + b"|" + audio.read_bytes())

    async def concatenate_mp4_files(self, inputs: list[Path], output: Path) -> None:
        self.concat_calls.append(([path.name for path in inputs], output.name))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"".join(path.read_bytes() for path in inputs))


def _png_bytes(width: int, height: int) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), color="red").save(output, format="PNG")
    return output.getvalue()


async def _create_project_and_slide(db_session, slide_type: SlideType = SlideType.CONTENT) -> tuple[str, str]:
    project = await ProjectResourceService(db_session).create_project(
        CreateProjectRequest(name="Deck", user_id="admin")
    )
    slide = await SlideResourceService(db_session).add_slide(
        project.id,
        SlideCreate(type=slide_type, title="Slide", description="Desc", content="Body"),
    )
    return project.id, slide.id


async def _wait_for_task_completion(session_factory, task_id: str, timeout_seconds: float = 2.0) -> object:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        async with session_factory() as session:
            task = await TaskRepository(session).get(task_id)
            if task is not None and task.status in {"completed", "failed", "cancelled"}:
                return task
        await asyncio.sleep(0.05)
    pytest.fail(f"task {task_id} did not finish in time")


async def bananalecture_add_dialogue(
    db_session,
    project_id: str,
    slide_id: str,
    *,
    role: DialogueRole,
    content: str,
) -> str:
    dialogue = await DialogueResourceService(db_session).add_dialogue(
        project_id,
        slide_id,
        AddDialogueRequest(
            role=role,
            content=content,
            emotion=DialogueEmotion.NEUTRAL,
            speed=DialogueSpeed.MEDIUM,
        ),
    )
    return dialogue.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_slide_image_file_returns_webp_with_resized_dimensions(
    db_session,
    test_settings: Settings,
) -> None:
    project_id, slide_id = await _create_project_and_slide(db_session)
    storage = StorageService(test_settings.STORAGE.DATA_DIR)
    await storage.initialize()

    image_path = await storage.write_bytes(StorageLayout.slide_image(project_id, slide_id), _png_bytes(3200, 1800))
    await SlideResourceService(db_session).set_image_path(slide_id, image_path)
    await db_session.commit()

    settings = test_settings.model_copy(
        update={
            "IMAGE_DELIVERY": ImageDeliverySettings(
                MAX_WIDTH=1600,
                MAX_HEIGHT=900,
                WEBP_QUALITY=75,
                WEBP_METHOD=4,
                LOSSLESS=False,
            )
        }
    )

    delivered = await GetSlideImageFileUseCase(
        SlideResourceService(db_session),
        storage,
        settings,
    ).execute(project_id, slide_id)

    assert delivered.media_type == "image/webp"
    assert delivered.filename == f"{slide_id}.webp"
    with Image.open(BytesIO(delivered.content)) as image:
        assert image.format == "WEBP"
        assert image.size == (1600, 900)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_slide_image_file_does_not_upscale_small_images(
    db_session,
    test_settings: Settings,
) -> None:
    project_id, slide_id = await _create_project_and_slide(db_session)
    storage = StorageService(test_settings.STORAGE.DATA_DIR)
    await storage.initialize()

    image_path = await storage.write_bytes(StorageLayout.slide_image(project_id, slide_id), _png_bytes(640, 360))
    await SlideResourceService(db_session).set_image_path(slide_id, image_path)
    await db_session.commit()

    settings = test_settings.model_copy(
        update={"IMAGE_DELIVERY": ImageDeliverySettings(MAX_WIDTH=1600, MAX_HEIGHT=900)}
    )

    delivered = await GetSlideImageFileUseCase(
        SlideResourceService(db_session),
        storage,
        settings,
    ).execute(project_id, slide_id)

    with Image.open(BytesIO(delivered.content)) as image:
        assert image.format == "WEBP"
        assert image.size == (640, 360)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_slide_audio_writes_dialogue_and_slide_audio(
    db_session,
    test_settings: Settings,
    fake_dialogue_client,
) -> None:
    project_id, slide_id = await _create_project_and_slide(db_session, SlideType.COVER)
    await bananalecture_add_dialogue(
        db_session,
        project_id,
        slide_id,
        role=DialogueRole.NOBITA,
        content="第一句",
    )
    await bananalecture_add_dialogue(
        db_session,
        project_id,
        slide_id,
        role=DialogueRole.PROP,
        content="竹蜻蜓",
    )

    storage = StorageService(test_settings.STORAGE.DATA_DIR)
    await storage.initialize()
    fake_audio_client = FakeAudioGenerationClient()
    fake_processing = FakeAudioProcessingService()

    await GenerateSlideAudioUseCase(
        db_session,
        storage,
        fake_audio_client,
        fake_processing,
        fake_dialogue_client,
        DefaultDialoguePromptStrategy(),
        DefaultAudioCueStrategy(ROOT_DIR / "assets"),
        settings=test_settings,
    ).execute(project_id, slide_id)

    dialogue_items = await DialogueRepository(db_session).list_by_slide(slide_id)
    assert [call["role"] for call in fake_audio_client.calls] == ["大雄", "道具"]
    assert all(item.audio_path is not None for item in dialogue_items)
    slide = await SlideRepository(db_session).get(project_id, slide_id)
    assert slide is not None
    assert slide.audio_path is not None

    assert fake_processing.calls == [
        (["gadgets.mp3", "audio.raw.mp3"], "audio.mp3"),
        (["cues.mp3", "audio.mp3", "audio.mp3"], "slide.mp3"),
    ]

    slide_audio_bytes = await storage.read_bytes(slide.audio_path)
    assert b"\xe7\xac\xac\xe4\xb8\x80\xe5\x8f\xa5" in slide_audio_bytes
    assert b"\xe7\xab\xb9\xe8\x9c\xbb\xe8\x9c\x93" in slide_audio_bytes


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_slide_audio_propagates_processing_failures(
    db_session,
    test_settings: Settings,
    fake_dialogue_client,
) -> None:
    project_id, slide_id = await _create_project_and_slide(db_session)
    await bananalecture_add_dialogue(
        db_session,
        project_id,
        slide_id,
        role=DialogueRole.NARRATOR,
        content="说明",
    )

    storage = StorageService(test_settings.STORAGE.DATA_DIR)
    await storage.initialize()
    fake_audio_client = FakeAudioGenerationClient()

    class FailingAudioProcessingService:
        async def concatenate_mp3_files(self, inputs: list[Path], output: Path) -> None:
            raise ExternalServiceError("ffmpeg failed")

    with pytest.raises(ExternalServiceError, match="ffmpeg failed"):
        await GenerateSlideAudioUseCase(
            db_session,
            storage,
            fake_audio_client,
            FailingAudioProcessingService(),
            fake_dialogue_client,
            DefaultDialoguePromptStrategy(),
            DefaultAudioCueStrategy(ROOT_DIR / "assets"),
            settings=test_settings,
        ).execute(project_id, slide_id)

    slide = await SlideRepository(db_session).get(project_id, slide_id)
    assert slide is not None
    assert slide.audio_path is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_video_generation_writes_project_video_and_updates_progress(
    db_session,
    test_settings: Settings,
    database_manager,
) -> None:
    first_project_id, first_slide_id = await _create_project_and_slide(db_session)
    second_slide = await SlideResourceService(db_session).add_slide(
        first_project_id,
        SlideCreate(type=SlideType.CONTENT, title="Slide 2", description="Desc", content="Body 2"),
    )

    storage = StorageService(test_settings.STORAGE.DATA_DIR)
    await storage.initialize()
    runtime = InMemoryBackgroundTaskRunner()
    fake_video_processing = FakeVideoProcessingService()

    first_image_path = await storage.write_bytes(
        StorageLayout.slide_image(first_project_id, first_slide_id), b"image-1"
    )
    first_audio_path = await storage.write_bytes(
        StorageLayout.slide_audio(first_project_id, first_slide_id), b"audio-1"
    )
    second_image_path = await storage.write_bytes(
        StorageLayout.slide_image(first_project_id, second_slide.id), b"image-2"
    )
    second_audio_path = await storage.write_bytes(
        StorageLayout.slide_audio(first_project_id, second_slide.id), b"audio-2"
    )
    await SlideResourceService(db_session).set_image_path(first_slide_id, first_image_path)
    await SlideResourceService(db_session).set_audio_path(first_slide_id, first_audio_path)
    await SlideResourceService(db_session).set_image_path(second_slide.id, second_image_path)
    await SlideResourceService(db_session).set_audio_path(second_slide.id, second_audio_path)
    await db_session.commit()

    service = QueueProjectVideoGenerationUseCase(
        db_session,
        runtime,
        database_manager.session_factory,
        storage,
        fake_video_processing,
        test_settings,
    )

    task_id = await service.execute(first_project_id)
    task = await _wait_for_task_completion(database_manager.session_factory, task_id)

    assert task.status == "completed"
    assert task.current_step == 3
    project = await ProjectRepository(db_session).get(first_project_id)
    assert project is not None
    assert project.video_path == f"projects/{first_project_id}/video/project-video.mp4"

    video_bytes = await storage.read_bytes(project.video_path)
    assert video_bytes == b"image-1|audio-1image-2|audio-2"
    assert fake_video_processing.render_calls == [
        ("original.png", "slide.mp3", "001.mp4"),
        ("original.png", "slide.mp3", "002.mp4"),
    ]
    assert fake_video_processing.concat_calls == [(["001.mp4", "002.mp4"], "project-video.mp4")]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_video_generation_rejects_missing_slide_image(
    db_session,
    test_settings: Settings,
    database_manager,
) -> None:
    project_id, slide_id = await _create_project_and_slide(db_session)

    storage = StorageService(test_settings.STORAGE.DATA_DIR)
    await storage.initialize()
    runtime = InMemoryBackgroundTaskRunner()
    audio_path = await storage.write_bytes(StorageLayout.slide_audio(project_id, slide_id), b"audio")
    await SlideResourceService(db_session).set_audio_path(slide_id, audio_path)
    await db_session.commit()

    service = QueueProjectVideoGenerationUseCase(
        db_session,
        runtime,
        database_manager.session_factory,
        storage,
        FakeVideoProcessingService(),
        test_settings,
    )

    with pytest.raises(BadRequestError, match=f"Slide {slide_id} image must be generated before video generation"):
        await service.execute(project_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_video_generation_rejects_missing_audio_file(
    db_session,
    test_settings: Settings,
    database_manager,
) -> None:
    project_id, slide_id = await _create_project_and_slide(db_session)

    storage = StorageService(test_settings.STORAGE.DATA_DIR)
    await storage.initialize()
    runtime = InMemoryBackgroundTaskRunner()
    image_path = await storage.write_bytes(StorageLayout.slide_image(project_id, slide_id), b"image")
    await SlideResourceService(db_session).set_image_path(slide_id, image_path)
    await SlideResourceService(db_session).set_audio_path(slide_id, "projects/missing/slide.mp3")
    await db_session.commit()

    service = QueueProjectVideoGenerationUseCase(
        db_session,
        runtime,
        database_manager.session_factory,
        storage,
        FakeVideoProcessingService(),
        test_settings,
    )

    with pytest.raises(NotFoundError, match=f"Slide {slide_id} audio file not found"):
        await service.execute(project_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_video_generation_marks_task_failed_when_processing_errors(
    db_session,
    test_settings: Settings,
    database_manager,
) -> None:
    project_id, slide_id = await _create_project_and_slide(db_session)

    storage = StorageService(test_settings.STORAGE.DATA_DIR)
    await storage.initialize()
    runtime = InMemoryBackgroundTaskRunner()

    class FailingVideoProcessingService:
        async def render_static_slide_clip(self, image: Path, audio: Path, output: Path) -> None:
            raise ExternalServiceError("video ffmpeg failed")

        async def concatenate_mp4_files(self, inputs: list[Path], output: Path) -> None:
            raise AssertionError("should not concatenate after render failure")

    image_path = await storage.write_bytes(StorageLayout.slide_image(project_id, slide_id), b"image")
    audio_path = await storage.write_bytes(StorageLayout.slide_audio(project_id, slide_id), b"audio")
    await SlideResourceService(db_session).set_image_path(slide_id, image_path)
    await SlideResourceService(db_session).set_audio_path(slide_id, audio_path)
    await db_session.commit()

    service = QueueProjectVideoGenerationUseCase(
        db_session,
        runtime,
        database_manager.session_factory,
        storage,
        FailingVideoProcessingService(),
        test_settings,
    )

    task_id = await service.execute(project_id)
    task = await _wait_for_task_completion(database_manager.session_factory, task_id)

    assert task.status == "failed"
    assert task.error_message == "video ffmpeg failed"
    project = await ProjectRepository(db_session).get(project_id)
    assert project is not None
    assert project.video_path is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_video_service_validates_inputs_without_creating_task(
    db_session,
    test_settings: Settings,
) -> None:
    project_id, slide_id = await _create_project_and_slide(db_session)
    storage = StorageService(test_settings.STORAGE.DATA_DIR)
    await storage.initialize()

    service = GenerateProjectVideoUseCase(db_session, storage, FakeVideoProcessingService(), test_settings)

    with pytest.raises(BadRequestError, match=f"Slide {slide_id} image must be generated before video generation"):
        await service.validate_inputs(project_id)
