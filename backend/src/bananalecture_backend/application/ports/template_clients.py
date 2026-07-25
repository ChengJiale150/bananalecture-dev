# ruff: noqa: D102

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bananalecture_backend.application.ports import AudioSynthesizer, DialogueGenerator
    from bananalecture_backend.application.strategies import AudioCueStrategy, DialoguePromptStrategy
    from bananalecture_backend.core.templates import TemplateConfig


@dataclass(frozen=True, slots=True)
class DialogueTemplateClients:
    """Resolved dialogue clients for a template."""

    dialogue_generator: DialogueGenerator
    prompt_strategy: DialoguePromptStrategy


@dataclass(frozen=True, slots=True)
class AudioTemplateClients:
    """Resolved audio clients for a template."""

    audio_synthesizer: AudioSynthesizer
    dialogue_generator: DialogueGenerator
    dialogue_prompt_strategy: DialoguePromptStrategy
    audio_cue_strategy: AudioCueStrategy


class TemplateClientResolver(Protocol):
    """Resolve template-specific clients, reusing defaults for the default template."""

    def resolve_dialogue_clients(self, template: TemplateConfig | None) -> DialogueTemplateClients: ...

    def resolve_audio_clients(self, template: TemplateConfig | None) -> AudioTemplateClients: ...
