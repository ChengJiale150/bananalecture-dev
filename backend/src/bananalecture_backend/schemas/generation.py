# ruff: noqa: D101, D102

from datetime import datetime
from enum import IntEnum, StrEnum

from bananalecture_backend.schemas.common import APIModel


class GenerationSessionStatus(StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationPhase(IntEnum):
    IMAGES = 0
    DIALOGUES = 1
    AUDIO = 2
    VIDEO = 3

    @property
    def label(self) -> str:
        return _PHASE_LABELS[self]

    @property
    def name(self) -> str:
        return _PHASE_NAMES[self]


_PHASE_LABELS: dict[GenerationPhase, str] = {
    GenerationPhase.IMAGES: "图片",
    GenerationPhase.DIALOGUES: "口播稿",
    GenerationPhase.AUDIO: "音频",
    GenerationPhase.VIDEO: "视频",
}

_PHASE_NAMES: dict[GenerationPhase, str] = {
    GenerationPhase.IMAGES: "images",
    GenerationPhase.DIALOGUES: "dialogues",
    GenerationPhase.AUDIO: "audio",
    GenerationPhase.VIDEO: "video",
}


class GenerationPhaseTaskState(APIModel):
    task_id: str | None = None
    status: str = "pending"
    current_step: int = 0
    total_steps: int = 0
    progress: int = 0
    error_message: str | None = None


class GenerationPhaseState(APIModel):
    phase: str
    label: str
    status: str = "pending"
    task: GenerationPhaseTaskState = GenerationPhaseTaskState()
    started_at: datetime | None = None
    completed_at: datetime | None = None


class GenerationSessionResponse(APIModel):
    session_id: str
    project_id: str
    status: str
    current_phase: int
    phases: list[GenerationPhaseState]
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


PHASES_ORDER = [
    GenerationPhase.IMAGES,
    GenerationPhase.DIALOGUES,
    GenerationPhase.AUDIO,
    GenerationPhase.VIDEO,
]
