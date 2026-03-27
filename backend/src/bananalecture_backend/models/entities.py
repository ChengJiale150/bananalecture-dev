# ruff: noqa: TC003

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bananalecture_backend.db.types import UTCDateTime
from bananalecture_backend.models.base import Base


class ProjectModel(Base):
    """Persistent project entity."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    messages: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())

    slides: Mapped[list[SlideModel]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tasks: Mapped[list[TaskModel]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SlideModel(Base):
    """Persistent slide entity."""

    __tablename__ = "slides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    idx: Mapped[int] = mapped_column(Integer)
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())

    project: Mapped[ProjectModel] = relationship(back_populates="slides")
    dialogues: Mapped[list[DialogueModel]] = relationship(
        back_populates="slide",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (Index("idx_slides_project_id", "project_id"),)


class DialogueModel(Base):
    """Persistent dialogue entity."""

    __tablename__ = "dialogues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slide_id: Mapped[str] = mapped_column(ForeignKey("slides.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    emotion: Mapped[str] = mapped_column(String(32))
    speed: Mapped[str] = mapped_column(String(32))
    idx: Mapped[int] = mapped_column(Integer)
    audio_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())

    slide: Mapped[SlideModel] = relationship(back_populates="dialogues")

    __table_args__ = (Index("idx_dialogues_slide_id", "slide_id"),)


class TaskModel(Base):
    """Persistent task entity."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    current_step: Mapped[int] = mapped_column(Integer)
    total_steps: Mapped[int] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())

    project: Mapped[ProjectModel] = relationship(back_populates="tasks")
