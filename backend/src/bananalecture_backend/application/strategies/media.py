# ruff: noqa: D102

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bananalecture_backend.schemas.slide import SlideType

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class DialoguePromptContext:
    """Application data required to build one slide dialogue prompt."""

    slide_type: str
    title: str
    description: str
    content: str
    previous_script: str | None


class DialoguePromptStrategy(Protocol):
    """Build the upstream prompt for slide dialogue generation."""

    def build(self, context: DialoguePromptContext) -> str: ...


class AudioCueStrategy(Protocol):
    """Resolve static cue assets for dialogue and slide audio assembly."""

    def dialogue_prefix_assets(self, role: str) -> list[Path]: ...

    def slide_prefix_assets(self, slide_type: str) -> list[Path]: ...


class DefaultDialoguePromptStrategy:
    """Default prompt construction strategy for slide dialogue generation."""

    def build(self, context: DialoguePromptContext) -> str:
        """Build one dialogue-generation prompt from slide context."""
        sections = [
            "请根据以下信息生成当前页的讲解对话。",
            f"当前页类型: {context.slide_type}",
            f"当前页标题: {context.title}",
            f"当前页描述: {context.description}",
            f"当前页内容: {context.content}",
        ]
        if context.previous_script is not None:
            sections.append(f"前一页口播稿:\n{context.previous_script}")
        else:
            sections.append("这是首页, 前一页口播稿: 无")
        if context.slide_type == SlideType.COVER.value:
            sections.append("当前页为封面页, 禁止生成道具角色。")
        return "\n\n".join(sections)


class DefaultAudioCueStrategy:
    """Default cue selection rules for generated audio."""

    def __init__(self, assets_root: Path) -> None:
        """Store the root directory containing static cue assets."""
        self.assets_root = assets_root

    def dialogue_prefix_assets(self, role: str) -> list[Path]:
        """Return cue assets that must be prefixed before one dialogue audio."""
        if role == "道具":
            return [self.assets_root / "gadgets.mp3"]
        return []

    def slide_prefix_assets(self, slide_type: str) -> list[Path]:
        """Return cue assets that must be prefixed before merged slide audio."""
        if slide_type == SlideType.COVER.value:
            return [self.assets_root / "cues.mp3"]
        return []
