from datetime import UTC, datetime

import pytest

from bananalecture_backend.core.errors import BadRequestError, NotFoundError
from bananalecture_backend.models import DialogueModel
from bananalecture_backend.schemas.dialogue import (
    AddDialogueRequest,
    DialogueEmotion,
    DialogueRole,
    DialogueSpeed,
    UpdateDialogueRequest,
)
from bananalecture_backend.schemas.project import CreateProjectRequest
from bananalecture_backend.schemas.slide import SlideCreate
from bananalecture_backend.services.resources import (
    DialogueResourceService,
    ProjectResourceService,
    SlideResourceService,
)


async def _create_project(db_session, *, name: str = "Deck", user_id: str = "admin") -> str:
    project = await ProjectResourceService(db_session).create_project(CreateProjectRequest(name=name, user_id=user_id))
    return project.id


async def _create_slide(db_session, *, title: str = "Slide", content: str = "Content") -> str:
    project_id = await _create_project(db_session)
    slide = await SlideResourceService(db_session).add_slide(
        project_id,
        SlideCreate(title=title, description=title, content=content),
    )
    return slide.id


async def _create_project_with_slide(db_session, *, title: str = "Slide", content: str = "Content") -> tuple[str, str]:
    project_id = await _create_project(db_session)
    slide = await SlideResourceService(db_session).add_slide(
        project_id,
        SlideCreate(title=title, description=title, content=content),
    )
    return project_id, slide.id


async def _seed_dialogues(db_session, slide_id: str) -> list[DialogueModel]:
    dialogues = [
        DialogueModel(
            id="dialogue-2",
            slide_id=slide_id,
            role="哆啦A梦",
            content="Second",
            emotion="开心的",
            speed="快速",
            idx=2,
            audio_path=None,
            created_at=datetime(2024, 1, 2, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, 0, 0, tzinfo=UTC),
        ),
        DialogueModel(
            id="dialogue-1",
            slide_id=slide_id,
            role="大雄",
            content="First",
            emotion="无明显情感",
            speed="中速",
            idx=1,
            audio_path=None,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        ),
        DialogueModel(
            id="dialogue-3",
            slide_id=slide_id,
            role="旁白",
            content="Third",
            emotion="惊讶的",
            speed="慢速",
            idx=3,
            audio_path=None,
            created_at=datetime(2024, 1, 3, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 3, 0, 0, tzinfo=UTC),
        ),
    ]
    db_session.add_all(dialogues)
    await db_session.commit()
    return dialogues


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_dialogues_returns_items_in_index_order(db_session) -> None:
    project_id, slide_id = await _create_project_with_slide(db_session)
    await _seed_dialogues(db_session, slide_id)

    payload = await DialogueResourceService(db_session).list_dialogues(project_id, slide_id)

    assert payload.total == 3
    assert [item.id for item in payload.items] == ["dialogue-1", "dialogue-2", "dialogue-3"]
    assert [item.idx for item in payload.items] == [1, 2, 3]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_dialogue_appends_to_end_with_defaults(db_session) -> None:
    project_id, slide_id = await _create_project_with_slide(db_session)
    await _seed_dialogues(db_session, slide_id)
    service = DialogueResourceService(db_session)

    created = await service.add_dialogue(
        project_id,
        slide_id,
        AddDialogueRequest(
            role=DialogueRole.OTHER_FEMALE,
            content="Fourth",
            emotion=DialogueEmotion.SAD,
            speed=DialogueSpeed.FAST,
        ),
    )

    assert created.idx == 4
    assert created.slide_id == slide_id
    assert created.role == DialogueRole.OTHER_FEMALE
    assert created.content == "Fourth"
    assert created.emotion == DialogueEmotion.SAD
    assert created.speed == DialogueSpeed.FAST
    assert created.audio_path is None
    assert created.created_at == created.updated_at


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_dialogue_updates_fields_and_timestamp(db_session) -> None:
    project_id, slide_id = await _create_project_with_slide(db_session)
    await _seed_dialogues(db_session, slide_id)
    service = DialogueResourceService(db_session)

    updated = await service.update_dialogue(
        project_id,
        slide_id,
        "dialogue-1",
        UpdateDialogueRequest(
            role=DialogueRole.DORAEMON,
            content="Updated",
            emotion=DialogueEmotion.ANGRY,
            speed=DialogueSpeed.SLOW,
        ),
    )

    assert updated.id == "dialogue-1"
    assert updated.role == DialogueRole.DORAEMON
    assert updated.content == "Updated"
    assert updated.emotion == DialogueEmotion.ANGRY
    assert updated.speed == DialogueSpeed.SLOW
    assert updated.updated_at >= datetime(2024, 1, 1, 0, 0, tzinfo=UTC)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_dialogue_resequences_remaining_items(db_session) -> None:
    project_id, slide_id = await _create_project_with_slide(db_session)
    await _seed_dialogues(db_session, slide_id)
    service = DialogueResourceService(db_session)

    await service.delete_dialogue(project_id, slide_id, "dialogue-2")

    remaining = await service.list_dialogues(project_id, slide_id)
    assert [item.id for item in remaining.items] == ["dialogue-1", "dialogue-3"]
    assert [item.idx for item in remaining.items] == [1, 2]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reorder_dialogues_updates_sequence(db_session) -> None:
    project_id, slide_id = await _create_project_with_slide(db_session)
    await _seed_dialogues(db_session, slide_id)
    service = DialogueResourceService(db_session)

    reordered = await service.reorder_dialogues(
        project_id,
        slide_id,
        ["dialogue-3", "dialogue-1", "dialogue-2"],
    )

    assert [(item.id, item.idx) for item in reordered] == [
        ("dialogue-3", 1),
        ("dialogue-1", 2),
        ("dialogue-2", 3),
    ]
    stored = await service.list_dialogues(project_id, slide_id)
    assert [item.id for item in stored.items] == ["dialogue-3", "dialogue-1", "dialogue-2"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reorder_dialogues_rejects_non_matching_ids(db_session) -> None:
    project_id, slide_id = await _create_project_with_slide(db_session)
    await _seed_dialogues(db_session, slide_id)
    other_slide_id = await _create_slide(db_session, title="Other", content="Other")
    db_session.add(
        DialogueModel(
            id="dialogue-other",
            slide_id=other_slide_id,
            role="旁白",
            content="Other slide",
            emotion="无明显情感",
            speed="中速",
            idx=1,
            audio_path=None,
            created_at=datetime(2024, 1, 5, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 5, 0, 0, tzinfo=UTC),
        )
    )
    await db_session.commit()
    service = DialogueResourceService(db_session)

    with pytest.raises(BadRequestError, match="dialogue_ids must match existing dialogues"):
        await service.reorder_dialogues(project_id, slide_id, ["dialogue-1", "dialogue-2"])

    with pytest.raises(BadRequestError, match="dialogue_ids must match existing dialogues"):
        await service.reorder_dialogues(project_id, slide_id, ["dialogue-1", "dialogue-1", "dialogue-3"])

    with pytest.raises(BadRequestError, match="dialogue_ids must match existing dialogues"):
        await service.reorder_dialogues(project_id, slide_id, ["dialogue-1", "dialogue-2", "dialogue-other"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_audio_path_updates_dialogue(db_session) -> None:
    project_id, slide_id = await _create_project_with_slide(db_session)
    await _seed_dialogues(db_session, slide_id)
    service = DialogueResourceService(db_session)

    await service.set_audio_path("dialogue-1", "/tmp/dialogue-1.mp3")

    stored = await service.dialogues.get(slide_id, "dialogue-1")
    assert stored is not None
    assert stored.audio_path == "/tmp/dialogue-1.mp3"
    assert stored.updated_at >= datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    await service.list_dialogues(project_id, slide_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dialogue_service_raises_not_found_for_missing_resources(db_session) -> None:
    service = DialogueResourceService(db_session)
    project_id, slide_id = await _create_project_with_slide(db_session)
    await _seed_dialogues(db_session, slide_id)

    with pytest.raises(NotFoundError, match="Slide not found"):
        await service.list_dialogues(project_id, "missing-slide")

    with pytest.raises(NotFoundError, match="Slide not found"):
        await service.add_dialogue(
            project_id,
            "missing-slide",
            AddDialogueRequest(content="Missing"),
        )

    with pytest.raises(NotFoundError, match="Slide not found"):
        await service.update_dialogue(
            project_id,
            "missing-slide",
            "dialogue-1",
            UpdateDialogueRequest(content="Missing"),
        )

    with pytest.raises(NotFoundError, match="Slide not found"):
        await service.delete_dialogue(project_id, "missing-slide", "dialogue-1")

    with pytest.raises(NotFoundError, match="Slide not found"):
        await service.reorder_dialogues(project_id, "missing-slide", ["dialogue-1"])

    with pytest.raises(NotFoundError, match="Dialogue not found"):
        await service.update_dialogue(
            project_id,
            slide_id,
            "missing-dialogue",
            UpdateDialogueRequest(content="Missing"),
        )

    with pytest.raises(NotFoundError, match="Dialogue not found"):
        await service.delete_dialogue(project_id, slide_id, "missing-dialogue")

    with pytest.raises(NotFoundError, match="Dialogue not found"):
        await service.set_audio_path("missing-dialogue", "/tmp/missing.mp3")
