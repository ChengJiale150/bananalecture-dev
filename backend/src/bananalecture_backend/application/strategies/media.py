# ruff: noqa: D102

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bananalecture_backend.schemas.slide import SlideType

if TYPE_CHECKING:
    from pathlib import Path

    from bananalecture_backend.core.templates import CueConfig


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
    """Template-aware prompt construction strategy for slide dialogue generation."""

    def __init__(self, cue_config: CueConfig) -> None:
        """Store the template cue configuration."""
        self.cue_config = cue_config

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
        if self.cue_config.prop_role and context.slide_type == SlideType.COVER.value:
            sections.append(f"当前页为封面页, 禁止生成{self.cue_config.prop_role}角色。")
        return "\n\n".join(sections)


class DefaultAudioCueStrategy:
    """Template-aware cue selection rules for generated audio."""

    def __init__(self, assets_root: Path, cue_config: CueConfig) -> None:
        """Store the cue assets root and template cue configuration."""
        self.assets_root = assets_root
        self.cue_config = cue_config

    def dialogue_prefix_assets(self, role: str) -> list[Path]:
        """Return cue assets that must be prefixed before one dialogue audio."""
        if self.cue_config.prop_role and role == self.cue_config.prop_role:
            audio = self.cue_config.prop_audio
            if audio:
                return [self.assets_root / audio]
        return []

    def slide_prefix_assets(self, slide_type: str) -> list[Path]:
        """Return cue assets that must be prefixed before merged slide audio."""
        if self.cue_config.cover_prefix and slide_type == SlideType.COVER.value:
            return [self.assets_root / self.cue_config.cover_prefix]
        return []
