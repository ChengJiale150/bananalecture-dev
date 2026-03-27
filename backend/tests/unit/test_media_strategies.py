from pathlib import Path

from bananalecture_backend.application.strategies import (
    DefaultAudioCueStrategy,
    DefaultDialoguePromptStrategy,
    DialoguePromptContext,
)


def test_default_dialogue_prompt_strategy_builds_cover_prompt_without_previous_script() -> None:
    prompt = DefaultDialoguePromptStrategy().build(
        DialoguePromptContext(
            slide_type="cover",
            title="Intro",
            description="Welcome",
            content="Physics basics",
            previous_script=None,
        )
    )

    assert "这是首页, 前一页口播稿: 无" in prompt
    assert "当前页为封面页, 禁止生成道具角色。" in prompt


def test_default_dialogue_prompt_strategy_builds_prompt_with_previous_script() -> None:
    prompt = DefaultDialoguePromptStrategy().build(
        DialoguePromptContext(
            slide_type="content",
            title="Motion",
            description="Topic",
            content="Force and velocity",
            previous_script="大雄：这一页先让我来开场。",
        )
    )

    assert "前一页口播稿:" in prompt
    assert "大雄：这一页先让我来开场。" in prompt
    assert "禁止生成道具角色" not in prompt


def test_default_audio_cue_strategy_resolves_expected_assets() -> None:
    strategy = DefaultAudioCueStrategy(Path("/tmp/assets"))

    assert strategy.dialogue_prefix_assets("旁白") == []
    assert strategy.dialogue_prefix_assets("道具") == [Path("/tmp/assets/gadgets.mp3")]
    assert strategy.slide_prefix_assets("content") == []
    assert strategy.slide_prefix_assets("cover") == [Path("/tmp/assets/cues.mp3")]
