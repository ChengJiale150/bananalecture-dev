from pathlib import Path

from pydantic_settings import SettingsConfigDict

from bananalecture_backend.core.config import ROOT_DIR, Settings
from tests.conftest import _default_runtime_artifact_paths


def test_settings_load_from_yaml_and_env_override(tmp_path: Path) -> None:
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                "APP:",
                "  NAME: yaml-project",
                "  DEBUG: false",
                "SERVER:",
                "  PORT: 8001",
                "DATABASE:",
                "  URL: sqlite+aiosqlite:///./yaml.db",
                "IMAGE_GENERATION:",
                "  API_URL: https://yaml.example/v1/chat/completions",
                "  API_KEY: yaml-key",
                "  MODEL_LIST:",
                "    - yaml-model",
                "  REQUEST_TIMEOUT_SECONDS: 12.5",
                '  GENERATION_SIZE: "4:3"',
                "  DOWNLOAD_RETRIES: 4",
                "  DOWNLOAD_RETRY_DELAY_SECONDS: 0.25",
                "AUDIO_GENERATION:",
                "  PROVIDER:",
                "    GROUP_ID: yaml-group",
                "    API_KEY: yaml-audio-key",
                "    MODEL: yaml-speech",
                "    REQUEST_TIMEOUT_SECONDS: 18.0",
                "  SAMPLE_RATE: 44100",
                "  BITRATE: 192000",
                '  FORMAT: "mp3"',
                "  MAX_RETRIES: 5",
                "  BASE_DELAY_SECONDS: 1.5",
                "  MAX_DELAY_SECONDS: 8.0",
                "  EXPONENTIAL_BASE: 2.5",
                '  DEFAULT_VOICE_GROUP: "yaml-default"',
                "  VOICE_GROUPS:",
                "    yaml-default:",
                '      旁白: "yaml-narrator"',
                '      其他: "yaml-other"',
                "VIDEO_GENERATION:",
                "  WIDTH: 1920",
                "  HEIGHT: 1080",
                "  FPS: 30",
                '  VIDEO_CODEC: "libx265"',
                '  AUDIO_CODEC: "aac"',
                "  AUDIO_BITRATE: 256000",
                '  PIXEL_FORMAT: "yuv420p"',
                '  BACKGROUND_COLOR: "white"',
                '  IMAGE_SCALE_MODE: "contain"',
                '  OUTPUT_FILENAME: "lesson.mp4"',
                '  TEMP_DIR_PREFIX: "yaml-video-"',
            ]
        ),
        encoding="utf-8",
    )
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "SERVER__PORT=9000",
                "IMAGE_GENERATION__API_KEY=env-key",
                'IMAGE_GENERATION__MODEL_LIST=["env-model-1", "env-model-2"]',
                "DIALOGUE_GENERATION__PROVIDER__API_KEY=dialogue-env-key",
                "AUDIO_GENERATION__PROVIDER__API_KEY=audio-env-key",
                "AUDIO_GENERATION__DEFAULT_VOICE_GROUP=env-default",
                'AUDIO_GENERATION__VOICE_GROUPS={"env-default":{"旁白":"env-narrator","其他":"env-other"}}',
                "VIDEO_GENERATION__FPS=24",
                "VIDEO_GENERATION__BACKGROUND_COLOR=navy",
            ]
        ),
        encoding="utf-8",
    )

    test_model_config = dict(Settings.model_config)
    test_model_config["yaml_file"] = yaml_path
    test_model_config["env_file"] = env_path

    class TestSettings(Settings):
        model_config = SettingsConfigDict(**test_model_config)

    settings = TestSettings()

    assert settings.APP.NAME == "yaml-project"
    assert settings.SERVER.PORT == 9000
    assert settings.DATABASE.URL == "sqlite+aiosqlite:///./yaml.db"
    assert settings.IMAGE_GENERATION.API_URL == "https://yaml.example/v1/chat/completions"
    assert settings.IMAGE_GENERATION.API_KEY == "env-key"
    assert settings.IMAGE_GENERATION.MODEL_LIST == ["env-model-1", "env-model-2"]
    assert settings.IMAGE_GENERATION.REQUEST_TIMEOUT_SECONDS == 12.5
    assert settings.IMAGE_GENERATION.GENERATION_SIZE == "4:3"
    assert settings.IMAGE_GENERATION.DOWNLOAD_RETRIES == 4
    assert settings.IMAGE_GENERATION.DOWNLOAD_RETRY_DELAY_SECONDS == 0.25
    assert settings.DIALOGUE_GENERATION.MODEL_NAME == "gpt-5"
    assert settings.DIALOGUE_GENERATION.PROVIDER.API_KEY == "dialogue-env-key"
    assert settings.DIALOGUE_GENERATION.PROFILE == {}
    assert settings.DIALOGUE_GENERATION.SETTINGS == {}
    assert settings.DIALOGUE_GENERATION.RETRIES == 3
    assert settings.AUDIO_GENERATION.PROVIDER.GROUP_ID == "yaml-group"
    assert settings.AUDIO_GENERATION.PROVIDER.API_KEY == "audio-env-key"
    assert settings.AUDIO_GENERATION.PROVIDER.MODEL == "yaml-speech"
    assert settings.AUDIO_GENERATION.PROVIDER.REQUEST_TIMEOUT_SECONDS == 18.0
    assert settings.AUDIO_GENERATION.DEFAULT_VOICE_GROUP == "env-default"
    assert settings.AUDIO_GENERATION.VOICE_GROUPS == {
        "yaml-default": {"旁白": "yaml-narrator", "其他": "yaml-other"},
        "env-default": {"旁白": "env-narrator", "其他": "env-other"},
    }
    assert settings.AUDIO_GENERATION.SAMPLE_RATE == 44100
    assert settings.AUDIO_GENERATION.BITRATE == 192000
    assert settings.AUDIO_GENERATION.FORMAT == "mp3"
    assert settings.AUDIO_GENERATION.MAX_RETRIES == 5
    assert settings.VIDEO_GENERATION.WIDTH == 1920
    assert settings.VIDEO_GENERATION.HEIGHT == 1080
    assert settings.VIDEO_GENERATION.FPS == 24
    assert settings.VIDEO_GENERATION.VIDEO_CODEC == "libx265"
    assert settings.VIDEO_GENERATION.AUDIO_CODEC == "aac"
    assert settings.VIDEO_GENERATION.AUDIO_BITRATE == 256000
    assert settings.VIDEO_GENERATION.PIXEL_FORMAT == "yuv420p"
    assert settings.VIDEO_GENERATION.BACKGROUND_COLOR == "navy"
    assert settings.VIDEO_GENERATION.IMAGE_SCALE_MODE == "contain"
    assert settings.VIDEO_GENERATION.OUTPUT_FILENAME == "lesson.mp4"
    assert settings.VIDEO_GENERATION.TEMP_DIR_PREFIX == "yaml-video-"


def test_default_runtime_cleanup_paths_ignore_repo_config() -> None:
    data_dir, database_path = _default_runtime_artifact_paths()

    assert data_dir == ROOT_DIR / ".bananalecture_data"
    assert database_path == ROOT_DIR / "bananalecture.db"
