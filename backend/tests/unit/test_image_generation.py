import pytest
import httpx

from bananalecture_backend.clients.image_generation import ImageGenerationClient
from bananalecture_backend.core.config import ImageGenerationSettings, Settings
from bananalecture_backend.core.errors import ExternalServiceError


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

    async def _post_completion(
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
            MODEL_LIST=["nano-banana-2", "nano-banana-pro", "nano-banana"],
        ),
    )
    client = StubImageGenerationClient(
        settings,
        [
            ExternalServiceError("first failed"),
            {"data": [{"url": "https://example.com/generated.png"}], "created": 1},
        ],
    )

    image_bytes = await client.generate_image("Generate a chart")

    assert image_bytes == b"fake-image"
    assert client.requested_models == ["nano-banana-2", "nano-banana-pro"]
    assert client.downloaded_urls == ["https://example.com/generated.png"]


@pytest.mark.asyncio
async def test_image_client_raises_when_response_is_missing_url() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2"],
        )
    )
    client = StubImageGenerationClient(settings, [{"data": [{}], "created": 1}])

    with pytest.raises(ExternalServiceError, match="missing data\\[0\\]\\.url"):
        await client.generate_image("Generate a chart")


@pytest.mark.asyncio
async def test_image_client_does_not_fallback_on_non_retryable_error() -> None:
    settings = Settings(
        IMAGE_GENERATION=ImageGenerationSettings(
            API_KEY="test-key",
            MODEL_LIST=["nano-banana-2", "nano-banana-pro", "nano-banana"],
        ),
    )
    client = StubImageGenerationClient(
        settings,
        [
            AssertionError("unexpected request payload"),
            {"data": [{"url": "https://example.com/second.png"}], "created": 1},
            {"data": [{"url": "https://example.com/third.png"}], "created": 1},
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
            MODEL_LIST=["nano-banana-2", "nano-banana-pro", "nano-banana"],
            DOWNLOAD_RETRIES=2,
            DOWNLOAD_RETRY_DELAY_SECONDS=0.0,
        ),
    )
    client = StubImageGenerationClient(
        settings,
        [{"data": [{"url": "https://example.com/generated.png"}], "created": 1}],
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
            MODEL_LIST=["nano-banana-2", "nano-banana-pro", "nano-banana"],
            DOWNLOAD_RETRIES=2,
            DOWNLOAD_RETRY_DELAY_SECONDS=0.0,
        ),
    )
    client = StubImageGenerationClient(
        settings,
        [{"data": [{"url": "https://example.com/generated.png"}], "created": 1}],
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
