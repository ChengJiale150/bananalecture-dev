from contextlib import contextmanager
from typing import Any, Iterator

import httpx
import pytest
from loguru import logger

from bananalecture_backend.clients.image_generation import ImageGenerationClient
from bananalecture_backend.core.config import ImageGenerationSettings, Settings
from bananalecture_backend.core.errors import ExternalServiceError


@contextmanager
def capture_log_records(level: str = "WARNING") -> Iterator[list[Any]]:
    """Capture loguru records emitted at or above the given level."""
    records: list[Any] = []
    sink_id = logger.add(lambda message: records.append(message.record), level=level)
    try:
        yield records
    finally:
        logger.remove(sink_id)


class StubImageGenerationClient(ImageGenerationClient):
    """Test double for the external image generation client."""

    def __init__(
        self,
        settings: Settings,
        responses: list[dict[str, object] | Exception],
        download_responses: list[bytes | Exception] | None = None,
    ) -> None:
        super().__init__(settings)
        self.responses = responses
        self.download_responses = download_responses or [b"fake-image"]
        self.requested_models: list[str] = []
        self.downloaded_urls: list[str] = []

    async def _generate(
        self,
        model: str,
        prompt: str,
        reference_image: str | None,
    ) -> dict[str, object]:
        self.requested_models.append(model)
        response = self.responses[len(self.requested_models) - 1]
        if isinstance(response, Exception):
            raise response
        assert prompt == "Generate a chart"
        assert reference_image is None
        return response

    async def _download_image(self, image_url: str) -> bytes:
        self.downloaded_urls.append(image_url)
        response = self.download_responses[len(self.downloaded_urls) - 1]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.asyncio
async def test_image_client_falls_back_to_next_model() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2", "nano-banana-fast", "nano-banana-pro", "nano-banana"],
        ),
    )
    client = StubImageGenerationClient(
        settings,
        [
            ExternalServiceError("first failed"),
            {
                "id": "task-1",
                "status": "succeeded",
                "results": [{"url": "https://example.com/generated.png"}],
                "progress": 100,
            },
        ],
    )

    image_bytes = await client.generate_image("Generate a chart")

    assert image_bytes == b"fake-image"
    assert client.requested_models == ["nano-banana-2", "nano-banana-fast"]
    assert client.downloaded_urls == ["https://example.com/generated.png"]


@pytest.mark.asyncio
async def test_image_client_raises_when_results_is_missing_url() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2"],
        )
    )
    client = StubImageGenerationClient(
        settings,
        [{"id": "task-1", "status": "succeeded", "results": [{}], "progress": 100}],
    )

    with pytest.raises(ExternalServiceError, match=r"missing results\[0\]\.url"):
        await client.generate_image("Generate a chart")


@pytest.mark.asyncio
async def test_image_client_raises_when_results_is_empty() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2"],
        )
    )
    client = StubImageGenerationClient(
        settings,
        [{"id": "task-1", "status": "succeeded", "results": [], "progress": 100}],
    )

    with pytest.raises(ExternalServiceError, match=r"missing results\[0\]\.url"):
        await client.generate_image("Generate a chart")


@pytest.mark.asyncio
async def test_image_client_raises_on_failed_status() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2"],
        )
    )
    client = StubImageGenerationClient(
        settings,
        [{"id": "task-1", "status": "failed", "error": "generate failed"}],
    )

    with pytest.raises(ExternalServiceError, match="generate failed"):
        await client.generate_image("Generate a chart")


@pytest.mark.asyncio
async def test_image_client_raises_on_violation_status() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2"],
        )
    )
    client = StubImageGenerationClient(
        settings,
        [{"id": "task-1", "status": "violation", "error": "content violation"}],
    )

    with pytest.raises(ExternalServiceError, match="content violation"):
        await client.generate_image("Generate a chart")


@pytest.mark.asyncio
async def test_image_client_does_not_fallback_on_non_retryable_error() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2", "nano-banana-fast", "nano-banana-pro", "nano-banana"],
        ),
    )
    client = StubImageGenerationClient(
        settings,
        [
            AssertionError("unexpected request payload"),
            {
                "id": "task-2",
                "status": "succeeded",
                "results": [{"url": "https://example.com/second.png"}],
                "progress": 100,
            },
            {
                "id": "task-3",
                "status": "succeeded",
                "results": [{"url": "https://example.com/third.png"}],
                "progress": 100,
            },
        ],
    )

    with pytest.raises(AssertionError, match="unexpected request payload"):
        await client.generate_image("Generate a chart")

    assert client.requested_models == ["nano-banana-2"]
    assert client.downloaded_urls == []


@pytest.mark.asyncio
async def test_image_client_retries_download_without_falling_back_to_next_model() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2", "nano-banana-fast", "nano-banana-pro", "nano-banana"],
            DOWNLOAD_RETRIES=2,
            DOWNLOAD_RETRY_DELAY_SECONDS=0.0,
        ),
    )
    client = StubImageGenerationClient(
        settings,
        [
            {
                "id": "task-1",
                "status": "succeeded",
                "results": [{"url": "https://example.com/generated.png"}],
                "progress": 100,
            }
        ],
        [
            httpx.ReadTimeout("cdn not ready"),
            b"fake-image",
        ],
    )

    image_bytes = await client.generate_image("Generate a chart")

    assert image_bytes == b"fake-image"
    assert client.requested_models == ["nano-banana-2"]
    assert client.downloaded_urls == [
        "https://example.com/generated.png",
        "https://example.com/generated.png",
    ]


@pytest.mark.asyncio
async def test_image_client_raises_when_download_retries_exhausted_without_fallback() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2", "nano-banana-fast", "nano-banana-pro", "nano-banana"],
            DOWNLOAD_RETRIES=2,
            DOWNLOAD_RETRY_DELAY_SECONDS=0.0,
        ),
    )
    client = StubImageGenerationClient(
        settings,
        [
            {
                "id": "task-1",
                "status": "succeeded",
                "results": [{"url": "https://example.com/generated.png"}],
                "progress": 100,
            }
        ],
        [
            httpx.ReadTimeout("cdn not ready"),
            httpx.ReadTimeout("cdn not ready"),
            httpx.ReadTimeout("cdn not ready"),
        ],
    )

    with pytest.raises(
        ExternalServiceError, match="Image download failed after generation succeeded for model nano-banana-2"
    ):
        await client.generate_image("Generate a chart")

    assert client.requested_models == ["nano-banana-2"]
    assert client.downloaded_urls == [
        "https://example.com/generated.png",
        "https://example.com/generated.png",
        "https://example.com/generated.png",
    ]


@pytest.mark.asyncio
async def test_image_client_logs_upstream_error_body_and_still_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """A rejected model must log the upstream body while keeping the existing fallback behavior."""
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2", "nano-banana-pro"],
        ),
    )
    client = ImageGenerationClient(settings)
    requested_models: list[str] = []

    class StubAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "StubAsyncClient":
            return self

        async def __aexit__(self, *exc_info: Any) -> bool:
            return False

        async def post(self, url: str, headers: Any = None, json: Any = None) -> httpx.Response:
            requested_models.append(json["model"])
            if len(requested_models) == 1:
                return httpx.Response(
                    status_code=400,
                    json={"status": "failed", "error": "apikey credits not enough"},
                    request=httpx.Request("POST", url),
                )
            return httpx.Response(
                status_code=200,
                json={"status": "succeeded", "results": [{"url": "https://cdn.example.com/a.png"}]},
                request=httpx.Request("POST", url),
            )

        async def get(self, url: str) -> httpx.Response:
            return httpx.Response(status_code=200, content=b"fake-image", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "AsyncClient", StubAsyncClient)

    with capture_log_records() as records:
        image_bytes = await client.generate_image("Generate a chart")

    assert image_bytes == b"fake-image"
    assert requested_models == ["nano-banana-2", "nano-banana-pro"]

    rejections = [record for record in records if record["message"] == "external_image_http_error"]
    assert len(rejections) == 1
    assert rejections[0]["extra"]["model"] == "nano-banana-2"
    assert rejections[0]["extra"]["status_code"] == 400
    assert rejections[0]["extra"]["response_body"] == '{"status":"failed","error":"apikey credits not enough"}'


def test_image_client_logs_truncated_upstream_error_body() -> None:
    settings = Settings(IMAGE_GENERATION=ImageGenerationSettings(API_KEY="test-key"))
    client = ImageGenerationClient(settings)

    with capture_log_records() as records:
        client._log_http_failure(  # noqa: SLF001
            httpx.Response(status_code=400, text="detail " + "x" * 4000),
            "nano-banana-2",
            "https://grsai.dakka.com.cn/v1/api/generate",
        )

    assert len(records) == 1
    body = records[0]["extra"]["response_body"]
    assert body.startswith("detail xxx")
    assert len(body) == 501
    assert body.endswith("…")


def test_image_client_does_not_log_http_failure_for_success_status() -> None:
    settings = Settings(IMAGE_GENERATION=ImageGenerationSettings(API_KEY="test-key"))
    client = ImageGenerationClient(settings)

    with capture_log_records() as records:
        client._log_http_failure(  # noqa: SLF001
            httpx.Response(status_code=200, json={"status": "succeeded"}),
            "nano-banana-2",
            "https://grsai.dakka.com.cn/v1/api/generate",
        )

    assert records == []


def test_image_client_logs_server_errors_at_error_level() -> None:
    settings = Settings(IMAGE_GENERATION=ImageGenerationSettings(API_KEY="test-key"))
    client = ImageGenerationClient(settings)

    with capture_log_records(level="ERROR") as records:
        client._log_http_failure(  # noqa: SLF001
            httpx.Response(status_code=502, text="bad gateway"),
            "nano-banana-2",
            "https://grsai.dakka.com.cn/v1/api/generate",
        )

    assert len(records) == 1
    assert records[0]["level"].name == "ERROR"
    assert records[0]["extra"]["response_body"] == "bad gateway"
