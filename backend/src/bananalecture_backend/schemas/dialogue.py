from datetime import datetime
from enum import StrEnum

from pydantic import Field

from bananalecture_backend.schemas.common import APIModel


class DialogueRole(StrEnum):
    """Supported dialogue roles."""

    NOBITA = "大雄"
    DORAEMON = "哆啦A梦"
    NARRATOR = "旁白"
    OTHER_MALE = "其他男声"
    OTHER_FEMALE = "其他女声"
    PROP = "道具"


class DialogueEmotion(StrEnum):
    """Supported dialogue emotions."""

    HAPPY = "开心的"
    SAD = "悲伤的"
    ANGRY = "生气的"
    AFRAID = "害怕的"
    SURPRISED = "惊讶的"
    NEUTRAL = "无明显情感"


class DialogueSpeed(StrEnum):
    """Supported dialogue speed values."""

    SLOW = "慢速"
    MEDIUM = "中速"
    FAST = "快速"


class DialogueBase(APIModel):
    """Editable dialogue fields."""

    role: DialogueRole = DialogueRole.NARRATOR
    content: str = Field(default="", max_length=5000)
    emotion: DialogueEmotion = DialogueEmotion.NEUTRAL
    speed: DialogueSpeed = DialogueSpeed.MEDIUM


class AddDialogueRequest(DialogueBase):
    """Add dialogue payload."""


class UpdateDialogueRequest(DialogueBase):
    """Update dialogue payload."""


class ReorderDialoguesRequest(APIModel):
    """Dialogue reorder payload."""

    dialogue_ids: list[str]


class Dialogue(APIModel):
    """Dialogue response model."""

    id: str
    slide_id: str
    role: DialogueRole
    content: str
    emotion: DialogueEmotion
    speed: DialogueSpeed
    idx: int
    audio_path: str | None = None
    created_at: datetime
    updated_at: datetime


class DialogueListData(APIModel):
    """Dialogue list payload."""

    items: list[Dialogue]
    total: int


class ReorderedDialogue(APIModel):
    """Reordered dialogue output."""

    id: str
    idx: int
