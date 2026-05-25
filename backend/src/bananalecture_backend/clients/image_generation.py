from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

import httpx

from bananalecture_backend.core.errors import ConfigurationError, ExternalServiceError

if TYPE_CHECKING:
    from bananalecture_backend.core.config import Settings


IMAGE_API_KEY_NOT_CONFIGURED = "IMAGE_API_KEY is not configured"
IMAGE_BASE_URL_NOT_CONFIGURED = "IMAGE_GENERATION__BASE_URL is not configured"
IMAGE_MODEL_LIST_EMPTY = "IMAGE_MODEL_LIST must not be empty"
IMAGE_PROMPT_EMPTY = "Image prompt must not be empty"
IMAGE_STATUS_FAILED = "Image generation failed"
IMAGE_STATUS_VIOLATION = "Image generation violation"
IMAGE_RESULTS_MISSING = "Image API response is missing results[0].url"


class ImageGenerationClient:
    """Client for the external image generation service."""

    def __init__(self, settings: Settings) -> None:
        """Store immutable image service settings."""
        self.settings = settings.IMAGE_GENERATION

    async def generate_image(self, prompt: str, reference_image: str | None = None) -> bytes:
        """Generate an image by trying the configured models in order."""
        prompt_text = prompt.strip()
        if not self.settings.API_KEY:
            raise ConfigurationError(IMAGE_API_KEY_NOT_CONFIGURED)
        if not self.settings.BASE_URL:
            raise ConfigurationError(IMAGE_BASE_URL_NOT_CONFIGURED)
        if not self.settings.MODEL_LIST:
            raise ConfigurationError(IMAGE_MODEL_LIST_EMPTY)
        if not prompt_text:
            raise ExternalServiceError(IMAGE_PROMPT_EMPTY)

        failures: list[str] = []
        for model in self.settings.MODEL_LIST:
            try:
                response = await self._generate(model, prompt_text, reference_image)
                image_url = self._extract_image_url(response)
            except (httpx.HTTPError, ExternalServiceError, ValueError) as exc:
                failures.append(f"{model}: {exc}")
                continue

            try:
                return await self._download_image_with_retries(model, image_url)
            except httpx.HTTPError as exc:
                error_message = f"Image download failed after generation succeeded for model {model}: {exc}"
                raise ExternalServiceError(error_message) from exc

        joined_failures = "; ".join(failures)
        error_message = f"Image generation failed for all configured models: {joined_failures}"
        raise ExternalServiceError(error_message)

    async def _generate(
        self,
        model: str,
        prompt: str,
        reference_image: str | None,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [reference_image] if reference_image else [],
            "aspectRatio": self.settings.ASPECT_RATIO,
            "imageSize": self.settings.IMAGE_SIZE,
            "replyType": "json",
        }
        url = f"{self.settings.BASE_URL}/v1/api/generate"
        async with httpx.AsyncClient(timeout=self.settings.REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.settings.API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return cast("dict[str, Any]", response.json())

    async def _download_image(self, image_url: str) -> bytes:
        async with httpx.AsyncClient(timeout=self.settings.REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content

    async def _download_image_with_retries(self, model: str, image_url: str) -> bytes:
        failures: list[str] = []
        attempts = self.settings.DOWNLOAD_RETRIES + 1
        for attempt in range(1, attempts + 1):
            try:
                return await self._download_image(image_url)
            except httpx.HTTPError as exc:
                failures.append(f"attempt {attempt}: {exc}")
                if attempt == attempts:
                    break
                if self.settings.DOWNLOAD_RETRY_DELAY_SECONDS > 0:
                    await asyncio.sleep(self.settings.DOWNLOAD_RETRY_DELAY_SECONDS)

        joined_failures = "; ".join(failures)
        error_message = f"model {model} url {image_url} failed to download after {attempts} attempts: {joined_failures}"
        raise httpx.HTTPError(error_message)

    def _extract_image_url(self, response: dict[str, Any]) -> str:
        status = response.get("status")
        if status == "failed":
            error = response.get("error") or IMAGE_STATUS_FAILED
            raise ExternalServiceError(error)
        if status == "violation":
            error = response.get("error") or IMAGE_STATUS_VIOLATION
            raise ExternalServiceError(error)
        if status != "succeeded":
            error = response.get("error") or f"Unexpected image generation status: {status}"
            raise ExternalServiceError(error)

        results = response.get("results")
        if not isinstance(results, Sequence) or isinstance(results, str) or not results:
            raise ExternalServiceError(IMAGE_RESULTS_MISSING)

        first_item = results[0]
        if not isinstance(first_item, dict):
            raise ExternalServiceError(IMAGE_RESULTS_MISSING)

        image_url = first_item.get("url")
        if not isinstance(image_url, str) or not image_url:
            raise ExternalServiceError(IMAGE_RESULTS_MISSING)
        return image_url


def build_image_generation_client(settings: Settings) -> ImageGenerationClient:
    """Build an image generation client from application settings."""
    return ImageGenerationClient(settings)
