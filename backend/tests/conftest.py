from collections.abc import AsyncGenerator, Generator
from base64 import b64decode
from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from bananalecture_backend.api.v1 import deps
from bananalecture_backend.application.ports import GeneratedDialogueDraft
from bananalecture_backend.core.config import DatabaseSettings, ROOT_DIR, Settings, StorageSettings
from bananalecture_backend.db.session import DatabaseManager
from bananalecture_backend.main import create_app
from bananalecture_backend.schemas.dialogue import DialogueEmotion, DialogueRole, DialogueSpeed

TEST_PNG_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0xQAAAAASUVORK5CYII="
)


class FakeImageGenerationClient:
    """In-memory image generator used by tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    async def generate_image(self, prompt: str, reference_image: str | None = None) -> bytes:
        self.calls.append({"prompt": prompt, "reference_image": reference_image})
        return TEST_PNG_BYTES


class FakeDialogueGenerationClient:
    """In-memory dialogue generator used by tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def generate_dialogues(
        self,
        prompt: str,
        image_bytes: bytes | None = None,
    ) -> list[GeneratedDialogueDraft]:
        self.calls.append(
            {
                "prompt": prompt,
                "has_image": image_bytes is not None,
                "image_bytes": image_bytes,
            }
        )
        return [
            GeneratedDialogueDraft(
                role=DialogueRole.NOBITA,
                content="这一页先让我来开场。",
                emotion=DialogueEmotion.HAPPY,
                speed=DialogueSpeed.MEDIUM,
            ),
            GeneratedDialogueDraft(
                role=DialogueRole.DORAEMON,
                content="接着我来解释这一页的重点。",
                emotion=DialogueEmotion.NEUTRAL,
                speed=DialogueSpeed.MEDIUM,
            ),
        ]


class FakeAudioGenerationClient:
    """In-memory audio generator used by tests."""

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
        return f"{role}:{emotion}:{speed}:{text}".encode("utf-8")


class FakeAudioProcessingService:
    """Simple concat implementation for tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str]] = []

    async def concatenate_mp3_files(self, inputs: list[Path], output: Path) -> None:
        self.calls.append(([path.name for path in inputs], output.name))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"|".join(path.read_bytes() for path in inputs))


class FakeVideoProcessingService:
    """Simple video renderer used by tests."""

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


def _default_runtime_artifact_paths() -> tuple[Path, Path | None]:
    """Return repository-local artifact paths for built-in defaults only."""
    data_dir = _resolve_runtime_path(StorageSettings().DATA_DIR)
    sqlite_prefix = "sqlite+aiosqlite:///"
    database_url = DatabaseSettings().URL
    database_path: Path | None = None
    if database_url.startswith(sqlite_prefix):
        database_path = _resolve_runtime_path(database_url.removeprefix(sqlite_prefix))
    return data_dir, database_path


def _resolve_runtime_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (ROOT_DIR / path).resolve(strict=False)


def _cleanup_default_runtime_artifacts() -> None:
    """Remove runtime artifacts created from built-in defaults without reading repo config."""
    data_dir, database_path = _default_runtime_artifact_paths()
    shutil.rmtree(data_dir, ignore_errors=True)
    if database_path is not None and database_path.exists():
        database_path.unlink()


@pytest.fixture(autouse=True, scope="session")
def cleanup_default_runtime_artifacts() -> Generator[None, None, None]:
    """Ensure tests do not leave default runtime files in the repository."""
    _cleanup_default_runtime_artifacts()
    yield
    _cleanup_default_runtime_artifacts()


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Build isolated settings for each test."""
    database_path = tmp_path / "bananalecture.db"
    data_dir = tmp_path / "data"
    return Settings(
        DATABASE=DatabaseSettings(URL=f"sqlite+aiosqlite:///{database_path}"),
        STORAGE=StorageSettings(DATA_DIR=str(data_dir)),
    )


@pytest.fixture
def fake_image_client() -> FakeImageGenerationClient:
    return FakeImageGenerationClient()


@pytest.fixture
def fake_dialogue_client() -> FakeDialogueGenerationClient:
    return FakeDialogueGenerationClient()


@pytest.fixture
def fake_audio_client() -> FakeAudioGenerationClient:
    return FakeAudioGenerationClient()


@pytest.fixture
def fake_audio_processing() -> FakeAudioProcessingService:
    return FakeAudioProcessingService()


@pytest.fixture
def fake_video_processing() -> FakeVideoProcessingService:
    return FakeVideoProcessingService()


@pytest.fixture
def client(
    test_settings: Settings,
    fake_image_client: FakeImageGenerationClient,
    fake_dialogue_client: FakeDialogueGenerationClient,
    fake_audio_client: FakeAudioGenerationClient,
    fake_audio_processing: FakeAudioProcessingService,
    fake_video_processing: FakeVideoProcessingService,
) -> Generator[TestClient, None, None]:
    """Create a test client with isolated storage."""
    app = create_app(test_settings)
    app.dependency_overrides[deps.get_image_generator] = lambda: fake_image_client
    app.dependency_overrides[deps.get_dialogue_generator] = lambda: fake_dialogue_client
    app.dependency_overrides[deps.get_audio_synthesizer] = lambda: fake_audio_client
    app.dependency_overrides[deps.get_audio_processor] = lambda: fake_audio_processing
    app.dependency_overrides[deps.get_video_renderer] = lambda: fake_video_processing
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def database_manager(test_settings: Settings) -> AsyncGenerator[DatabaseManager, None]:
    """Create an isolated async database manager for service tests."""
    database = DatabaseManager(test_settings)
    await database.initialize()
    yield database
    await database.dispose()


@pytest.fixture
async def db_session(database_manager: DatabaseManager) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async session backed by the isolated test database."""
    async with database_manager.session_factory() as session:
        yield session
