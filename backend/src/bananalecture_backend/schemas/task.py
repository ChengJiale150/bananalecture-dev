from datetime import datetime
from enum import StrEnum

from bananalecture_backend.schemas.common import APIModel


class TaskType(StrEnum):
    """Supported task types."""

    DIALOGUE_GENERATION = "dialogue_generation"
    AUDIO_GENERATION = "audio_generation"
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"


class TaskStatus(StrEnum):
    """Task lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Task(APIModel):
    """Task response model."""

    id: str
    project_id: str
    type: TaskType
    status: TaskStatus
    current_step: int
    total_steps: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
