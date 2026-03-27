from __future__ import annotations

import asyncio
import binascii
from random import SystemRandom
from typing import TYPE_CHECKING, Any, ClassVar

import httpx

from bananalecture_backend.core.errors import ConfigurationError, ExternalServiceError

if TYPE_CHECKING:
    from bananalecture_backend.core.config import Settings


AUDIO_API_GROUP_ID_NOT_CONFIGURED = "AUDIO_GENERATION.PROVIDER.GROUP_ID is not configured"
AUDIO_API_KEY_NOT_CONFIGURED = "AUDIO_GENERATION.PROVIDER.API_KEY is not configured"
AUDIO_MODEL_NOT_CONFIGURED = "AUDIO_GENERATION.PROVIDER.MODEL is not configured"
AUDIO_DEFAULT_GROUP_INVALID = "AUDIO_GENERATION.DEFAULT_VOICE_GROUP is not configured in VOICE_GROUPS"
AUDIO_RESPONSE_MISSING_BASE = "Audio generation response is missing base_resp"
AUDIO_RESPONSE_INVALID_STATUS = "Audio generation response returned non-zero status"
AUDIO_RESPONSE_MISSING_DATA = "Audio generation response is missing data"
AUDIO_RESPONSE_MISSING_AUDIO = "Audio generation response is missing data.audio"
TEXT_EMPTY = "Audio generation text must not be empty"
RATE_LIMITED = "Audio generation rate limited"
FAILED = "Audio generation failed"
CLIENT_ERROR_TEMPLATE = "Audio generation request failed with status {status_code}: {response_text}"
VOICE_MISSING_TEMPLATE = "Audio voice is not configured for role: {role}"
DECODE_FAILED_TEMPLATE = "Audio generation response decode failed: {error}"
HTTP_STATUS_TOO_MANY_REQUESTS = 429
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_SERVER_ERROR = 500
_RANDOM = SystemRandom()


class AudioGenerationClient:
    """Client for the external audio generation service."""

    emotion_map: ClassVar[dict[str, str]] = {
        "开心的": "happy",
        "悲伤的": "sad",
        "生气的": "angry",
        "害怕的": "fearful",
        "惊讶的": "surprised",
        "无明显情感": "auto",
    }
    speed_map: ClassVar[dict[str, float]] = {
        "慢速": 0.8,
        "中速": 1.0,
        "快速": 1.25,
    }

    def __init__(self, settings: Settings) -> None:
        """Store immutable audio service settings."""
        self.settings = settings.AUDIO_GENERATION
        self.provider = self.settings.PROVIDER
        self._validate_provider_configuration()
        self.url = f"https://api.minimax.chat/v1/t2a_v2?GroupId={self.provider.GROUP_ID}"

    async def generate_audio(self, text: str, role: str, emotion: str, speed: str) -> bytes:
        """Generate audio bytes for a dialogue item."""
        text_value = text.strip()
        if not text_value:
            raise ExternalServiceError(TEXT_EMPTY)

        payload = self._build_payload(text_value, role, emotion, speed)
        return await self._request_audio(payload)

    def _validate_provider_configuration(self) -> None:
        if not self.provider.GROUP_ID:
            raise ConfigurationError(AUDIO_API_GROUP_ID_NOT_CONFIGURED)
        if not self.provider.API_KEY:
            raise ConfigurationError(AUDIO_API_KEY_NOT_CONFIGURED)
        if not self.provider.MODEL:
            raise ConfigurationError(AUDIO_MODEL_NOT_CONFIGURED)

    def _build_payload(self, text: str, role: str, emotion: str, speed: str) -> dict[str, Any]:
        voice_group = self._resolve_voice_group()
        voice_id = voice_group.get(role, voice_group.get("其他"))
        if voice_id is None:
            message = VOICE_MISSING_TEMPLATE.format(role=role)
            raise ConfigurationError(message)

        mapped_emotion = self.emotion_map.get(emotion, "auto")
        payload: dict[str, Any] = {
            "model": self.provider.MODEL,
            "text": text,
            "timbre_weights": [{"voice_id": voice_id, "weight": 100}],
            "voice_setting": {
                "voice_id": voice_id,
                "speed": self.speed_map.get(speed, 1.0),
                "pitch": 0,
                "vol": 1,
                "latex_read": role != "道具",
            },
            "audio_setting": {
                "sample_rate": self.settings.SAMPLE_RATE,
                "bitrate": self.settings.BITRATE,
                "format": self.settings.FORMAT,
            },
            "language_boost": "auto",
        }

        if role == "道具":
            payload["voice_setting"]["emotion"] = "happy"
            payload["voice_setting"]["latex_read"] = False
        elif mapped_emotion != "auto":
            payload["voice_setting"]["emotion"] = mapped_emotion

        return payload

    def _resolve_voice_group(self) -> dict[str, str]:
        voice_group = self.settings.VOICE_GROUPS.get(self.settings.DEFAULT_VOICE_GROUP)
        if voice_group is None:
            raise ConfigurationError(AUDIO_DEFAULT_GROUP_INVALID)
        return voice_group

    async def _request_audio(self, payload: dict[str, Any]) -> bytes:
        last_error: ExternalServiceError | None = None
        for attempt in range(1, self.settings.MAX_RETRIES + 2):
            try:
                response = await self._post_audio(payload)
                self._raise_for_client_error(response)
                response.raise_for_status()
                return self._extract_audio_bytes(response.json())
            except ConfigurationError:
                raise
            except ExternalServiceError as exc:
                last_error = exc
            except (binascii.Error, ValueError, KeyError, TypeError) as exc:
                message = DECODE_FAILED_TEMPLATE.format(error=exc)
                last_error = ExternalServiceError(message)
            except httpx.TimeoutException as exc:
                last_error = ExternalServiceError(f"Audio generation request timed out: {exc}")
            except httpx.HTTPError as exc:
                last_error = ExternalServiceError(f"Audio generation HTTP request failed: {exc}")

            if attempt <= self.settings.MAX_RETRIES:
                await self._exponential_backoff(attempt)

        if last_error is not None:
            raise last_error
        raise ExternalServiceError(FAILED)

    async def _post_audio(self, payload: dict[str, Any]) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.provider.REQUEST_TIMEOUT_SECONDS) as client:
            return await client.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.provider.API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

    def _raise_for_client_error(self, response: httpx.Response) -> None:
        if response.status_code == HTTP_STATUS_TOO_MANY_REQUESTS:
            raise ExternalServiceError(RATE_LIMITED)
        if HTTP_STATUS_BAD_REQUEST <= response.status_code < HTTP_STATUS_SERVER_ERROR:
            message = CLIENT_ERROR_TEMPLATE.format(
                status_code=response.status_code,
                response_text=response.text,
            )
            raise ExternalServiceError(message)

    def _extract_audio_bytes(self, response_json: dict[str, Any]) -> bytes:
        base_resp = response_json.get("base_resp")
        if not isinstance(base_resp, dict):
            raise ExternalServiceError(AUDIO_RESPONSE_MISSING_BASE)
        status_code = base_resp.get("status_code")
        if status_code != 0:
            status_msg = base_resp.get("status_msg", "")
            raise ExternalServiceError(f"{AUDIO_RESPONSE_INVALID_STATUS}: {status_code} {status_msg}".strip())
        data = response_json.get("data")
        if not isinstance(data, dict):
            raise ExternalServiceError(AUDIO_RESPONSE_MISSING_DATA)
        audio_hex = data.get("audio")
        if not isinstance(audio_hex, str) or not audio_hex:
            raise ExternalServiceError(AUDIO_RESPONSE_MISSING_AUDIO)
        try:
            return binascii.unhexlify(audio_hex)
        except (binascii.Error, ValueError) as exc:
            message = DECODE_FAILED_TEMPLATE.format(error=exc)
            raise ExternalServiceError(message) from exc

    async def _exponential_backoff(self, attempt: int) -> None:
        delay = min(
            self.settings.BASE_DELAY_SECONDS * (self.settings.EXPONENTIAL_BASE ** (attempt - 1)),
            self.settings.MAX_DELAY_SECONDS,
        )
        await asyncio.sleep(delay + _RANDOM.uniform(0, 0.1 * delay))


def build_audio_generation_client(settings: Settings) -> AudioGenerationClient:
    """Build an audio generation client from application settings."""
    return AudioGenerationClient(settings)
