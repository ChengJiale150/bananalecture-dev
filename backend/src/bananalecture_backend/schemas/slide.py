from datetime import datetime
from enum import StrEnum

from pydantic import Field

from bananalecture_backend.schemas.common import APIModel


class SlideType(StrEnum):
    """Supported slide types."""

    COVER = "cover"
    INTRODUCTION = "introduction"
    CONTENT = "content"
    SUMMARY = "summary"
    ENDING = "ending"


class SlideBase(APIModel):
    """Editable slide fields."""

    type: SlideType = SlideType.CONTENT
    title: str = Field(default="", max_length=255)
    description: str = ""
    content: str = ""


class SlideCreate(SlideBase):
    """Slide creation payload."""


class CreateSlidesRequest(APIModel):
    """Bulk slide creation payload."""

    slides: list[SlideCreate]


class UpdateSlideRequest(SlideBase):
    """Slide update payload."""


class ReorderSlidesRequest(APIModel):
    """Slide reorder payload."""

    slide_ids: list[str]


class Slide(APIModel):
    """Slide response model."""

    id: str
    project_id: str
    type: SlideType
    title: str
    description: str
    content: str
    idx: int
    image_path: str | None = None
    audio_path: str | None = None
    created_at: datetime
    updated_at: datetime


class ReorderedSlide(APIModel):
    """Reordered slide output."""

    id: str
    idx: int
