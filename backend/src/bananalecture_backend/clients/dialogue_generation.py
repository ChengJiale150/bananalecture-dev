from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pydantic import Field
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.providers.openai import OpenAIProvider

from bananalecture_backend.application.ports import GeneratedDialogueDraft
from bananalecture_backend.core.errors import ConfigurationError, ExternalServiceError
from bananalecture_backend.schemas.common import APIModel
from bananalecture_backend.schemas.dialogue import DialogueEmotion, DialogueRole, DialogueSpeed

if TYPE_CHECKING:
    from pydantic_ai.settings import ModelSettings

    from bananalecture_backend.core.config import Settings


DIALOGUE_API_KEY_NOT_CONFIGURED = "DIALOGUE_GENERATION.PROVIDER.API_KEY is not configured"
DIALOGUE_MODEL_NAME_EMPTY = "DIALOGUE_GENERATION.MODEL_NAME must not be empty"
DIALOGUE_PROFILE_INVALID = "DIALOGUE_GENERATION.PROFILE is invalid"

SYSTEM_PROMPT_TEMPLATE = """
你是一个专业的口播稿生成助手。你需要根据将提供的信息转换为生动有趣的对话稿。

要求:
1. 角色仅可使用: {roles}
2. 内容要简洁明了, 适合口头表达
3. 语言要生动有趣, 吸引听众
4. 为每个对话项设置合适的情感和语速

注意事项:
1. 图片中所有出现的公式与数学符号均转化为 Latex 格式, 并都用 $$ 包裹,
如 $$E = m \\times c^2$$ 与 $$1-\\epsilon$$
2. 道具为特殊 role, 当且仅当哆啦A梦首次掏出道具时, 添加角色为道具、内容为道具名称的对话,
后续出现时无需重复添加, 封面页禁止生成道具角色
""".strip()


class GeneratedDialogueItem(APIModel):
    """Structured dialogue item returned by the LLM."""

    role: DialogueRole = Field(description="说话的角色名称")
    content: str = Field(description="口播稿具体内容", min_length=1, max_length=5000)
    emotion: DialogueEmotion = Field(description="对话的情感")
    speed: DialogueSpeed = Field(description="对话的语速")


class DialogueGenerationClient:
    """Pydantic AI client for slide dialogue generation."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the client from immutable application settings."""
        self.settings = settings.DIALOGUE_GENERATION
        self.agent = Agent(
            model=self._build_model(),
            output_type=list[GeneratedDialogueItem],
            system_prompt=SYSTEM_PROMPT_TEMPLATE.format(
                roles="、".join(role.value for role in DialogueRole),
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

        try:
            result = await self.agent.run(content)
        except Exception as exc:
            message = f"Dialogue generation failed: {exc}"
            raise ExternalServiceError(message) from exc
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


def build_dialogue_generation_client(settings: Settings) -> DialogueGenerationClient:
    """Build a dialogue generation client from application settings."""
    return DialogueGenerationClient(settings)
