from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

DoraemonRole = Literal["大雄", "哆啦A梦", "旁白", "其他男声", "其他女声", "道具"]
"""Allowed dialogue roles for the doraemon template."""

XiyoujiRole = Literal["悟空", "八戒", "旁白"]
"""Allowed dialogue roles for the xiyouji template."""


@dataclass(frozen=True, slots=True)
class CueConfig:
    """Cue audio asset configuration for a template.

    Setting an attribute to ``None`` disables that cue.
    """

    prop_role: str | None
    prop_audio: str | None
    cover_prefix: str | None


@dataclass(frozen=True, slots=True)
class TemplateConfig:
    """Immutable configuration for one lecture template."""

    id: str
    name: str
    roles: list[str]
    voice_groups: dict[str, str]
    system_prompt: str
    assets_dir: str
    cue_config: CueConfig
    reference_images: list[str]


DEFAULT_TEMPLATE_ID = "doraemon"

_TEMPLATE_REGISTRY: dict[str, TemplateConfig] = {
    "doraemon": TemplateConfig(
        id="doraemon",
        name="哆啦A梦",
        roles=list(get_args(DoraemonRole)),
        voice_groups={
            "旁白": "Chinese (Mandarin)_Male_Announcer",
            "大雄": "ppt2audio_daxiong",
            "哆啦A梦": "ppt2audio_duolaameng",
            "道具": "ppt2audio_duolaameng",
            "其他男声": "Chinese (Mandarin)_Pure-hearted_Boy",
            "其他女声": "Chinese (Mandarin)_ExplorativeGirl",
            "其他": "Chinese (Mandarin)_Radio_Host",
        },
        system_prompt="""\
你是一个专业的口播稿生成助手。你需要根据将提供的信息转换为生动有趣的对话稿。
生成的内容将直接输入语音合成(TTS)模型进行朗读, 请确保所有文本易于自然朗读

要求:
1. 角色仅可使用: {roles}
2. 内容要简洁明了, 适合口头表达
3. 语言要生动有趣, 吸引听众
4. 为每个对话项设置合适的情感和语速

注意事项:
1. 图片中所有出现的公式与数学符号均转化为 Latex 格式, 并都用 $$ 包裹,
如 $$E = m \\times c^2$$ 与 $$1-\\epsilon$$
2. 道具为特殊 role, 当且仅当哆啦A梦首次掏出道具时, 添加角色为道具、内容为道具名称的对话,
后续出现时无需重复添加, 封面页禁止生成道具角色""",
        assets_dir="doraemon",
        cue_config=CueConfig(
            prop_role="道具",
            prop_audio="gadgets.mp3",
            cover_prefix="cues.mp3",
        ),
        reference_images=[],
    ),
    "xiyouji": TemplateConfig(
        id="xiyouji",
        name="西游记",
        roles=list(get_args(XiyoujiRole)),
        voice_groups={
            "旁白": "Chinese (Mandarin)_Male_Announcer",
            "悟空": "banana_wukong",
            "八戒": "Chinese (Mandarin)_Humorous_Elder",
            "其他": "Chinese (Mandarin)_Radio_Host",
        },
        system_prompt="""\
你是一个专业的口播稿生成助手。你需要根据将提供的信息转换为生动有趣的对话稿。
生成的内容将直接输入语音合成(TTS)模型进行朗读, 请确保所有文本易于自然朗读

要求:
1. 角色仅可使用: {roles}
2. 悟空为博学多识的教授角色, 八戒为好奇好学的学生角色
3. 悟空自称"俺老孙", 称呼八戒为"八戒"或"师弟"; 八戒称呼悟空为"大师兄"或"猴哥",
悟空是讲解者而非唐僧, 严禁悟空自称"为师"
4. 内容要简洁明了, 适合口头表达
5. 语言要生动有趣, 吸引听众
6. 为每个对话项设置合适的情感和语速

注意事项:
1. 图片中所有出现的公式与数学符号均转化为 Latex 格式, 并都用 $$ 包裹,
如 $$E = m \\times c^2$$ 与 $$1-\\epsilon$$
2. 封面页禁止生成长段对话""",
        assets_dir="xiyouji",
        cue_config=CueConfig(
            prop_role=None,
            prop_audio=None,
            cover_prefix=None,
        ),
        reference_images=["wukong.png", "bajie.png"],
    ),
}


def get_valid_template_ids() -> frozenset[str]:
    """Return all registered template identifiers."""
    return frozenset(_TEMPLATE_REGISTRY.keys())


def get_template_config(template_id: str) -> TemplateConfig | None:
    """Look up a template configuration by id.

    Returns ``None`` when the id is unknown.
    """
    return _TEMPLATE_REGISTRY.get(template_id)
