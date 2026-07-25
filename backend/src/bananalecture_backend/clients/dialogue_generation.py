from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pydantic import Field
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider

from bananalecture_backend.application.ports import GeneratedDialogueDraft
from bananalecture_backend.core.errors import ConfigurationError, ExternalServiceError
from bananalecture_backend.core.logging_config import get_global_logger
from bananalecture_backend.core.templates import DoraemonRole, XiyoujiRole  # noqa: TC001  # pydantic 运行时需要
from bananalecture_backend.schemas.common import APIModel
from bananalecture_backend.schemas.dialogue import DialogueEmotion, DialogueSpeed  # noqa: TC001  # pydantic 运行时需要

if TYPE_CHECKING:
    from pydantic_ai.settings import ModelSettings

    from bananalecture_backend.core.config import Settings
    from bananalecture_backend.core.templates import TemplateConfig

global_logger = get_global_logger()

DIALOGUE_API_KEY_NOT_CONFIGURED = "DIALOGUE_GENERATION.PROVIDER.API_KEY is not configured"
DIALOGUE_MODEL_NAME_EMPTY = "DIALOGUE_GENERATION.MODEL_NAME must not be empty"
DIALOGUE_PROFILE_INVALID = "DIALOGUE_GENERATION.PROFILE is invalid"


class GeneratedDialogueItem(APIModel):
    """Structured dialogue item returned by the LLM."""

    role: str = Field(description="说话的角色名称")
    content: str = Field(description="口播稿具体内容", min_length=1, max_length=5000)
    emotion: DialogueEmotion = Field(description="对话的情感")
    speed: DialogueSpeed = Field(description="对话的语速")


class DoraemonDialogueItem(GeneratedDialogueItem):
    """Dialogue item constrained to doraemon template roles."""

    role: DoraemonRole = Field(description="说话的角色名称")


class XiyoujiDialogueItem(GeneratedDialogueItem):
    """Dialogue item constrained to xiyouji template roles."""

    role: XiyoujiRole = Field(description="说话的角色名称")


_ITEM_MODELS: dict[str, type[GeneratedDialogueItem]] = {
    "doraemon": DoraemonDialogueItem,
    "xiyouji": XiyoujiDialogueItem,
}


def _build_output_type(template_id: str) -> type[list[GeneratedDialogueItem]]:
    """Return the constrained list output type for a template (fallback: unconstrained base)."""
    item_model = _ITEM_MODELS.get(template_id, GeneratedDialogueItem)
    return cast("type[list[GeneratedDialogueItem]]", list.__class_getitem__(item_model))


class DialogueGenerationClient:
    """Pydantic AI client for slide dialogue generation."""

    def __init__(self, settings: Settings, template_config: TemplateConfig) -> None:
        """Initialize the client from application settings and template config."""
        self.settings = settings.DIALOGUE_GENERATION
        self.agent = Agent(
            model=self._build_model(),
            output_type=_build_output_type(template_config.id),
            system_prompt=template_config.system_prompt.format(
                roles="、".join(template_config.roles),
            ),
            retries=self.settings.RETRIES,
        )

    async def generate_dialogues(
        self,
        prompt: str,
        image_bytes: bytes | None = None,
    ) -> list[GeneratedDialogueDraft]:
        """Generate dialogue items for a single slide."""
        content: list[str | BinaryContent] = [prompt]
        if image_bytes is not None:
            content.append(BinaryContent(data=image_bytes, media_type="image/png"))

        global_logger.bind(
            prompt_length=len(prompt),
            has_image=image_bytes is not None,
            model=self.settings.MODEL_NAME,
        ).info("external_dialogue_request")
        try:
            result = await self.agent.run(content)
        except Exception as exc:
            message = f"Dialogue generation failed: {exc}"
            global_logger.bind(error=message).error("external_dialogue_failed")
            raise ExternalServiceError(message) from exc
        global_logger.bind(count=len(result.output)).info("external_dialogue_succeeded")
        return [
            GeneratedDialogueDraft(
                role=item.role,
                content=item.content,
                emotion=item.emotion,
                speed=item.speed,
            )
            for item in result.output
        ]

    def _build_model(self) -> OpenAIChatModel:
        model_name = self.settings.MODEL_NAME.strip()
        if not self.settings.PROVIDER.API_KEY:
            raise ConfigurationError(DIALOGUE_API_KEY_NOT_CONFIGURED)
        if not model_name:
            raise ConfigurationError(DIALOGUE_MODEL_NAME_EMPTY)

        try:
            profile = OpenAIModelProfile(**self.settings.PROFILE)
        except TypeError as exc:
            message = f"{DIALOGUE_PROFILE_INVALID}: {exc}"
            raise ConfigurationError(message) from exc

        return OpenAIChatModel(
            model_name,
            provider=OpenAIProvider(
                api_key=self.settings.PROVIDER.API_KEY,
                base_url=self.settings.PROVIDER.BASE_URL,
            ),
            profile=profile,
            settings=cast("ModelSettings", dict(self.settings.SETTINGS)),
        )


def build_dialogue_generation_client(settings: Settings, template_config: TemplateConfig) -> DialogueGenerationClient:
    """Build a dialogue generation client from application settings and template config."""
    return DialogueGenerationClient(settings, template_config)
