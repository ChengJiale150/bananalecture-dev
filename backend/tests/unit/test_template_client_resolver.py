from pathlib import Path

import pytest

from bananalecture_backend.api.v1.deps import SettingsTemplateClientResolver
from bananalecture_backend.application.strategies import DefaultAudioCueStrategy, DefaultDialoguePromptStrategy
from bananalecture_backend.clients.audio_generation import AudioGenerationClient
from bananalecture_backend.clients.dialogue_generation import DialogueGenerationClient
from bananalecture_backend.core.config import (
    AudioGenerationSettings,
    AudioProviderSettings,
    DialogueGenerationProviderSettings,
    DialogueGenerationSettings,
    Settings,
)
from bananalecture_backend.core.templates import DEFAULT_TEMPLATE_ID, get_template_config
from tests.conftest import FakeAudioGenerationClient, FakeDialogueGenerationClient


def _build_settings() -> Settings:
    return Settings(
        DIALOGUE_GENERATION=DialogueGenerationSettings(
            PROVIDER=DialogueGenerationProviderSettings(API_KEY="dialogue-key"),
        ),
        AUDIO_GENERATION=AudioGenerationSettings(
            PROVIDER=AudioProviderSettings(
                GROUP_ID="group-id",
                API_KEY="api-key",
                MODEL="speech-2",
            ),
        ),
    )


def _build_resolver() -> tuple[
    SettingsTemplateClientResolver,
    FakeDialogueGenerationClient,
    DefaultDialoguePromptStrategy,
    FakeAudioGenerationClient,
    DefaultAudioCueStrategy,
]:
    default_config = get_template_config(DEFAULT_TEMPLATE_ID)
    assert default_config is not None
    default_generator = FakeDialogueGenerationClient()
    default_strategy = DefaultDialoguePromptStrategy(default_config.cue_config)
    default_synthesizer = FakeAudioGenerationClient()
    default_cue_strategy = DefaultAudioCueStrategy(
        Path("assets") / default_config.assets_dir, default_config.cue_config
    )
    resolver = SettingsTemplateClientResolver(
        _build_settings(),
        default_generator,
        default_strategy,
        default_synthesizer,
        default_cue_strategy,
    )
    return resolver, default_generator, default_strategy, default_synthesizer, default_cue_strategy


@pytest.mark.unit
def test_resolver_reuses_default_clients_for_none_and_default_template() -> None:
    resolver, default_generator, default_strategy, default_synthesizer, default_cue_strategy = _build_resolver()
    default_template = get_template_config(DEFAULT_TEMPLATE_ID)

    for template in (None, default_template):
        dialogue_clients = resolver.resolve_dialogue_clients(template)
        assert dialogue_clients.dialogue_generator is default_generator
        assert dialogue_clients.prompt_strategy is default_strategy

        audio_clients = resolver.resolve_audio_clients(template)
        assert audio_clients.audio_synthesizer is default_synthesizer
        assert audio_clients.dialogue_generator is default_generator
        assert audio_clients.dialogue_prompt_strategy is default_strategy
        assert audio_clients.audio_cue_strategy is default_cue_strategy


@pytest.mark.unit
def test_resolver_builds_template_clients_for_non_default_template() -> None:
    resolver, default_generator, default_strategy, default_synthesizer, default_cue_strategy = _build_resolver()
    template = get_template_config("xiyouji")
    assert template is not None

    dialogue_clients = resolver.resolve_dialogue_clients(template)
    assert isinstance(dialogue_clients.dialogue_generator, DialogueGenerationClient)
    assert dialogue_clients.dialogue_generator is not default_generator
    assert dialogue_clients.prompt_strategy is not default_strategy

    audio_clients = resolver.resolve_audio_clients(template)
    assert isinstance(audio_clients.audio_synthesizer, AudioGenerationClient)
    assert audio_clients.audio_synthesizer.voice_groups == template.voice_groups
    assert audio_clients.audio_synthesizer is not default_synthesizer
    assert isinstance(audio_clients.dialogue_generator, DialogueGenerationClient)
    assert audio_clients.dialogue_prompt_strategy is not default_strategy
    assert audio_clients.audio_cue_strategy is not default_cue_strategy
