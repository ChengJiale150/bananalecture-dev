from typing import Any

from pydantic import BaseModel, Field


class ImageGenerationSettings(BaseModel):
    """Settings for the external image generation service."""

    API_URL: str = "https://api.chatfire.site/v1/images/generations"
    API_KEY: str | None = None
    MODEL_LIST: list[str] = Field(
        default_factory=lambda: [
            "nano-banana-2",
            "nano-banana-pro",
            "nano-banana",
        ]
    )
    REQUEST_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0.0)
    GENERATION_SIZE: str = "16:9"
    DOWNLOAD_RETRIES: int = Field(default=3, ge=0)
    DOWNLOAD_RETRY_DELAY_SECONDS: float = Field(default=0.5, ge=0.0)


class DialogueGenerationProviderSettings(BaseModel):
    """Provider settings for dialogue generation."""

    BASE_URL: str | None = None
    API_KEY: str | None = None


class DialogueGenerationSettings(BaseModel):
    """Settings for the external dialogue generation service."""

    MODEL_NAME: str = "gpt-5"
    PROVIDER: DialogueGenerationProviderSettings = Field(default_factory=DialogueGenerationProviderSettings)
    PROFILE: dict[str, Any] = Field(default_factory=dict)
    SETTINGS: dict[str, Any] = Field(default_factory=dict)
    RETRIES: int = Field(default=3, ge=0)


class AudioProviderSettings(BaseModel):
    """Provider settings for audio generation."""

    GROUP_ID: str | None = None
    API_KEY: str | None = None
    MODEL: str | None = None
    REQUEST_TIMEOUT_SECONDS: float = Field(default=60.0, gt=0.0)


class AudioGenerationSettings(BaseModel):
    """Settings for the external audio generation service."""

    PROVIDER: AudioProviderSettings = Field(default_factory=AudioProviderSettings)
    SAMPLE_RATE: int = Field(default=32000, gt=0)
    CHANNELS: int = Field(default=2, gt=0)
    BITRATE: int = Field(default=128000, gt=0)
    FORMAT: str = "mp3"
    MAX_RETRIES: int = Field(default=3, ge=0)
    BASE_DELAY_SECONDS: float = Field(default=5.0, ge=0.0)
    MAX_DELAY_SECONDS: float = Field(default=60.0, gt=0.0)
    EXPONENTIAL_BASE: float = Field(default=2.0, gt=1.0)
    DEFAULT_VOICE_GROUP: str = "default"
    VOICE_GROUPS: dict[str, dict[str, str]] = Field(
        default_factory=lambda: {
            "default": {
                "旁白": "Chinese (Mandarin)_Male_Announcer",
                "大雄": "bananalecture_nobita",
                "哆啦A梦": "bananalecture_doraemon",
                "道具": "bananalecture_doraemon",
                "其他男声": "Chinese (Mandarin)_Pure-hearted_Boy",
                "其他女声": "Chinese (Mandarin)_ExplorativeGirl",
                "其他": "Chinese (Mandarin)_Radio_Host",
            }
        }
    )


class VideoGenerationSettings(BaseModel):
    """Settings for ffmpeg-based video generation."""

    WIDTH: int = Field(default=1366, gt=0)
    HEIGHT: int = Field(default=768, gt=0)
    FPS: int = Field(default=25, gt=0)
    VIDEO_CODEC: str = "libx264"
    AUDIO_CODEC: str = "aac"
    AUDIO_CHANNELS: int = Field(default=2, gt=0)
    AUDIO_SAMPLE_RATE: int = Field(default=32000, gt=0)
    AUDIO_BITRATE: int = Field(default=192000, gt=0)
    PIXEL_FORMAT: str = "yuv420p"
    BACKGROUND_COLOR: str = "black"
    IMAGE_SCALE_MODE: str = "contain"
    OUTPUT_FILENAME: str = "project-video.mp4"
    TEMP_DIR_PREFIX: str = "video-build-"
