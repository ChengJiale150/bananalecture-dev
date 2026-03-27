# ruff: noqa: D102, EM101, TC001, TRY003

from datetime import datetime

from pydantic import Field, model_validator

from bananalecture_backend.schemas.common import APIModel


class CreateProjectRequest(APIModel):
    """Payload for project creation."""

    name: str = Field(min_length=1, max_length=255)
    user_id: str = Field(default="admin", min_length=1, max_length=255)


class UpdateProjectRequest(APIModel):
    """Payload for project update."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    messages: str | None = None

    @model_validator(mode="after")
    def validate_non_empty(self) -> "UpdateProjectRequest":
        if self.name is None and self.messages is None:
            raise ValueError("at least one field must be provided")
        return self


class ProjectSummary(APIModel):
    """Project summary model."""

    id: str
    user_id: str
    name: str
    messages: str | None = None
    video_path: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectListItem(APIModel):
    """Project list item."""

    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectSummary):
    """Project detail with slides."""

    slides: list["Slide"]


class ProjectUpdateResult(APIModel):
    """Project update response payload."""

    id: str
    name: str
    messages: str | None = None
    updated_at: datetime


from bananalecture_backend.schemas.slide import Slide  # noqa: E402
