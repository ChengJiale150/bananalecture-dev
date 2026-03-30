from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from bananalecture_backend.core.config.base import DEFAULT_CONFIG_FILE, DEFAULT_ENV_FILE
from bananalecture_backend.core.config.media import (
    AudioGenerationSettings,
    DialogueGenerationSettings,
    ImageDeliverySettings,
    ImageGenerationSettings,
    VideoGenerationSettings,
)


class AppMetadataSettings(BaseModel):
    """Application identity and environment settings."""

    NAME: str = "bananalecture_backend"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"


class ApiSettings(BaseModel):
    """API exposure settings."""

    V1_STR: str = "/api/v1"


class ServerSettings(BaseModel):
    """HTTP server settings."""

    HOST: str = "0.0.0.0"  # nosec B104 # noqa: S104
    PORT: int = 8000


class DatabaseSettings(BaseModel):
    """Database connection settings."""

    URL: str = "sqlite+aiosqlite:///./bananalecture.db"


class StorageSettings(BaseModel):
    """Local storage and default user settings."""

    DATA_DIR: str = ".bananalecture_data"
    DEFAULT_USER_ID: str = "admin"


class PaginationSettings(BaseModel):
    """Pagination defaults."""

    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100


class TaskSettings(BaseModel):
    """Background task runtime settings."""

    VIDEO_TASK_DELAY_SECONDS: float = Field(default=0.2, ge=0.0)


class Settings(BaseSettings):
    """System settings for the FastAPI application."""

    APP: AppMetadataSettings = Field(default_factory=AppMetadataSettings)
    API: ApiSettings = Field(default_factory=ApiSettings)
    SERVER: ServerSettings = Field(default_factory=ServerSettings)
    DATABASE: DatabaseSettings = Field(default_factory=DatabaseSettings)
    STORAGE: StorageSettings = Field(default_factory=StorageSettings)
    PAGINATION: PaginationSettings = Field(default_factory=PaginationSettings)
    TASKS: TaskSettings = Field(default_factory=TaskSettings)
    IMAGE_GENERATION: ImageGenerationSettings = Field(default_factory=ImageGenerationSettings)
    IMAGE_DELIVERY: ImageDeliverySettings = Field(default_factory=ImageDeliverySettings)
    DIALOGUE_GENERATION: DialogueGenerationSettings = Field(default_factory=DialogueGenerationSettings)
    AUDIO_GENERATION: AudioGenerationSettings = Field(default_factory=AudioGenerationSettings)
    VIDEO_GENERATION: VideoGenerationSettings = Field(default_factory=VideoGenerationSettings)

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
        yaml_file=DEFAULT_CONFIG_FILE,
        yaml_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Load settings from init args, environment, dotenv, then YAML defaults."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    """Build cached application settings."""
    return Settings()


settings = get_settings()
