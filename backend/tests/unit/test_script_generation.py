from typing import Any

import pytest

from bananalecture_backend.clients.dialogue_generation import DialogueGenerationClient, GeneratedDialogueItem
from bananalecture_backend.core.config import (
    DialogueGenerationProviderSettings,
    DialogueGenerationSettings,
    Settings,
)
from bananalecture_backend.core.errors import ConfigurationError, ExternalServiceError
from bananalecture_backend.schemas.dialogue import DialogueEmotion, DialogueRole, DialogueSpeed


class StubAgent:
    """Minimal stub for Agent.run."""

    def __init__(self, output: list[GeneratedDialogueItem] | Exception) -> None:
        self.output = output
        self.calls: list[list[object]] = []

    async def run(self, content: list[object]) -> Any:
        self.calls.append(content)
        if isinstance(self.output, Exception):
            raise self.output
        return type("RunResult", (), {"output": self.output})()


def _build_settings() -> Settings:
    return Settings(
        DIALOGUE_GENERATION=DialogueGenerationSettings(
            MODEL_NAME="gpt-4.1-mini",
            PROVIDER=DialogueGenerationProviderSettings(
                API_KEY="test-key",
                BASE_URL="https://example.com/v1",
            ),
        )
    )


@pytest.mark.asyncio
async def test_dialogue_client_passes_prompt_without_image() -> None:
    client = DialogueGenerationClient(_build_settings())
    stub_agent = StubAgent(
        [
            GeneratedDialogueItem(
                role=DialogueRole.NARRATOR,
                content="先用文本输入生成。",
                emotion=DialogueEmotion.NEUTRAL,
                speed=DialogueSpeed.MEDIUM,
            )
        ]
    )
    client.agent = stub_agent  # type: ignore[assignment]

    result = await client.generate_dialogues("生成讲解稿")

    assert result[0].content == "先用文本输入生成。"
    assert stub_agent.calls == [["生成讲解稿"]]


@pytest.mark.asyncio
async def test_dialogue_client_appends_image_when_present() -> None:
    client = DialogueGenerationClient(_build_settings())
    stub_agent = StubAgent(
        [
            GeneratedDialogueItem(
                role=DialogueRole.NARRATOR,
                content="带图输入生成。",
                emotion=DialogueEmotion.NEUTRAL,
                speed=DialogueSpeed.MEDIUM,
            )
        ]
    )
    client.agent = stub_agent  # type: ignore[assignment]

    await client.generate_dialogues("生成讲解稿", b"png-bytes")

    assert len(stub_agent.calls[0]) == 2
    assert stub_agent.calls[0][0] == "生成讲解稿"


@pytest.mark.asyncio
async def test_dialogue_client_wraps_upstream_errors() -> None:
    client = DialogueGenerationClient(_build_settings())
    client.agent = StubAgent(RuntimeError("boom"))  # type: ignore[assignment]

    with pytest.raises(ExternalServiceError, match="Dialogue generation failed: boom"):
        await client.generate_dialogues("生成讲解稿")


def test_dialogue_client_requires_api_key() -> None:
    settings = Settings(
        DIALOGUE_GENERATION=DialogueGenerationSettings(
            MODEL_NAME="gpt-4.1-mini",
            PROVIDER=DialogueGenerationProviderSettings(API_KEY=None),
        )
    )

    with pytest.raises(ConfigurationError, match="API_KEY"):
        DialogueGenerationClient(settings)
