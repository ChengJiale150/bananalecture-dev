from __future__ import annotations

from typing import Any

import pytest

from bananalecture_backend.clients.audio_generation import AudioGenerationClient
from bananalecture_backend.core.config import (
    AudioGenerationSettings,
    AudioProviderSettings,
    Settings,
)
from bananalecture_backend.core.errors import ConfigurationError, ExternalServiceError


TEST_VOICE_GROUPS = {
    "旁白": "voice-narrator",
    "大雄": "voice-nobita",
    "哆啦A梦": "voice-doraemon",
    "道具": "voice-prop",
    "其他男声": "voice-male",
    "其他女声": "voice-female",
    "其他": "voice-other",
}


class StubAudioGenerationClient(AudioGenerationClient):
    """Test double for payload construction and request dispatch."""

    def __init__(self, settings: Settings, voice_groups: dict[str, str] | None = None) -> None:
        super().__init__(settings, voice_groups or TEST_VOICE_GROUPS)
        self.seen_payloads: list[dict[str, Any]] = []

    async def _request_audio(self, payload: dict[str, Any]) -> bytes:
        self.seen_payloads.append(payload)
        return b"audio-bytes"


def _build_settings() -> Settings:
    return Settings(
        AUDIO_GENERATION=AudioGenerationSettings(
            PROVIDER=AudioProviderSettings(
                GROUP_ID="group-id",
                API_KEY="api-key",
                MODEL="speech-2",
            ),
        )
    )


@pytest.mark.asyncio
async def test_audio_client_maps_role_emotion_and_speed_into_payload() -> None:
    client = StubAudioGenerationClient(_build_settings())

    result = await client.generate_audio(
        text="今天开始讲解。",
        role="大雄",
        emotion="开心的",
        speed="快速",
    )

    payload = client.seen_payloads[0]
    assert result == b"audio-bytes"
    assert payload["text"] == "今天开始讲解。"
    assert payload["model"] == "speech-2"
    assert payload["timbre_weights"][0]["voice_id"] == "voice-nobita"
    assert payload["voice_setting"]["voice_id"] == "voice-nobita"
    assert payload["voice_setting"]["emotion"] == "happy"
    assert payload["voice_setting"]["speed"] == 1.25
    assert payload["voice_setting"]["latex_read"] is True


@pytest.mark.asyncio
async def test_audio_client_uses_auto_emotion_for_neutral_dialogue() -> None:
    client = StubAudioGenerationClient(_build_settings())

    await client.generate_audio(
        text="保持平静说明。",
        role="旁白",
        emotion="无明显情感",
        speed="中速",
    )

    payload = client.seen_payloads[0]
    assert "emotion" not in payload["voice_setting"]
    assert payload["voice_setting"]["speed"] == 1.0


@pytest.mark.asyncio
async def test_audio_client_uses_prop_specific_payload_rules() -> None:
    client = StubAudioGenerationClient(_build_settings())

    await client.generate_audio(
        text="竹蜻蜓",
        role="道具",
        emotion="生气的",
        speed="慢速",
    )

    payload = client.seen_payloads[0]
    assert payload["timbre_weights"][0]["voice_id"] == "voice-prop"
    assert payload["voice_setting"]["voice_id"] == "voice-prop"
    assert payload["voice_setting"]["emotion"] == "happy"
    assert payload["voice_setting"]["speed"] == 0.8
    assert payload["voice_setting"]["latex_read"] is False


def test_audio_client_requires_provider_credentials() -> None:
    settings = Settings(
        AUDIO_GENERATION=AudioGenerationSettings(
            PROVIDER=AudioProviderSettings(
                GROUP_ID="group-id",
                API_KEY=None,
                MODEL="speech-2",
            )
        )
    )

    with pytest.raises(ConfigurationError, match="API_KEY"):
        AudioGenerationClient(settings, {"其他": "voice-other"})


@pytest.mark.asyncio
async def test_audio_client_falls_back_to_other_voice_for_unknown_role() -> None:
    client = StubAudioGenerationClient(_build_settings())

    await client.generate_audio(
        text="未知角色的台词。",
        role="孙悟空",
        emotion="无明显情感",
        speed="中速",
    )

    payload = client.seen_payloads[0]
    assert payload["timbre_weights"][0]["voice_id"] == "voice-other"
    assert payload["voice_setting"]["voice_id"] == "voice-other"


@pytest.mark.asyncio
async def test_audio_client_raises_for_unknown_voice_group() -> None:
    settings = Settings(
        AUDIO_GENERATION=AudioGenerationSettings(
            PROVIDER=AudioProviderSettings(
                GROUP_ID="group-id",
                API_KEY="api-key",
                MODEL="speech-2",
            ),
        )
    )
    client = AudioGenerationClient(settings, {"旁白": "voice-narrator"})

    with pytest.raises(ConfigurationError, match="not configured for role"):
        await client.generate_audio(
            text="测试",
            role="悟空",
            emotion="无明显情感",
            speed="中速",
        )


def test_audio_client_validates_api_response_shape() -> None:
    settings = _build_settings()
    client = AudioGenerationClient(settings, TEST_VOICE_GROUPS)

    with pytest.raises(ExternalServiceError, match="missing data.audio"):
        client._extract_audio_bytes({"base_resp": {"status_code": 0, "status_msg": "ok"}, "data": {}})
