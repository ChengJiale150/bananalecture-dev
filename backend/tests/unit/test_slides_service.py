from datetime import UTC, datetime

import pytest

from bananalecture_backend.core.errors import BadRequestError, NotFoundError
from bananalecture_backend.models import DialogueModel, SlideModel
from bananalecture_backend.schemas.project import CreateProjectRequest
from bananalecture_backend.schemas.slide import CreateSlidesRequest, SlideCreate, SlideType, UpdateSlideRequest
from bananalecture_backend.services.resources import ProjectResourceService, SlideResourceService


async def _create_project(db_session, *, name: str = "Deck", user_id: str = "admin") -> str:
    project = await ProjectResourceService(db_session).create_project(CreateProjectRequest(name=name, user_id=user_id))
    return project.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replace_slides_creates_indexed_slides_with_defaults(db_session) -> None:
    project_id = await _create_project(db_session)
    service = SlideResourceService(db_session)

    slides = await service.replace_slides(
        project_id,
        CreateSlidesRequest(
            slides=[
                SlideCreate(type=SlideType.COVER, title="Intro", description="Welcome", content="Physics basics"),
                SlideCreate(type=SlideType.CONTENT, title="Motion", description="Topic", content="Velocity"),
            ]
        ),
    )

    stored = await service.slides.list_by_project(project_id)
    assert [slide.idx for slide in slides] == [1, 2]
    assert [slide.type for slide in slides] == [SlideType.COVER, SlideType.CONTENT]
    assert [slide.title for slide in slides] == ["Intro", "Motion"]
    assert all(slide.image_path is None for slide in slides)
    assert all(slide.audio_path is None for slide in slides)
    assert all(slide.created_at == slide.updated_at for slide in slides)
    assert [slide.id for slide in stored] == [slide.id for slide in slides]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replace_slides_overwrites_existing_slides_and_deletes_dialogues(db_session) -> None:
    project_id = await _create_project(db_session)
    service = SlideResourceService(db_session)
    original = await service.replace_slides(
        project_id,
        CreateSlidesRequest(slides=[SlideCreate(title="Old", description="Old", content="Old")]),
    )
    db_session.add(
        DialogueModel(
            id="dialogue-1",
            slide_id=original[0].id,
            role="旁白",
            content="Old dialogue",
            emotion="无明显情感",
            speed="中速",
            idx=1,
            audio_path=None,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
    )
    await db_session.commit()

    replacement = await service.replace_slides(
        project_id,
        CreateSlidesRequest(
            slides=[
                SlideCreate(type=SlideType.SUMMARY, title="New", description="Fresh", content="Fresh"),
                SlideCreate(type=SlideType.ENDING, title="Outro", description="Bye", content="Bye"),
            ]
        ),
    )

    stored_slides = await service.slides.list_by_project(project_id)
    assert [slide.id for slide in stored_slides] == [slide.id for slide in replacement]
    assert [slide.idx for slide in stored_slides] == [1, 2]
    assert await service.dialogues.list_by_slide(original[0].id) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_slides_returns_items_in_index_order(db_session) -> None:
    project_id = await _create_project(db_session)
    db_session.add_all(
        [
            SlideModel(
                id="slide-2",
                project_id=project_id,
                type="content",
                title="Second",
                description="Second",
                content="Second",
                idx=2,
                image_path=None,
                audio_path=None,
                created_at=datetime(2024, 1, 2, 0, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 2, 0, 0, tzinfo=UTC),
            ),
            SlideModel(
                id="slide-1",
                project_id=project_id,
                type="cover",
                title="First",
                description="First",
                content="First",
                idx=1,
                image_path=None,
                audio_path=None,
                created_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            ),
        ]
    )
    await db_session.commit()

    slides = await SlideResourceService(db_session).list_slides(project_id)

    assert [slide.id for slide in slides] == ["slide-1", "slide-2"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_slide_updates_fields_and_timestamp(db_session) -> None:
    project_id = await _create_project(db_session)
    service = SlideResourceService(db_session)
    created = await service.add_slide(
        project_id,
        SlideCreate(type=SlideType.CONTENT, title="Old", description="Old", content="Old"),
    )

    updated = await service.update_slide(
        project_id,
        created.id,
        UpdateSlideRequest(type=SlideType.SUMMARY, title="New", description="New", content="New"),
    )

    assert updated.id == created.id
    assert updated.type == SlideType.SUMMARY
    assert updated.title == "New"
    assert updated.description == "New"
    assert updated.content == "New"
    assert updated.updated_at >= created.updated_at


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_slide_removes_dialogues_and_resequences_remaining_slides(db_session) -> None:
    project_id = await _create_project(db_session)
    service = SlideResourceService(db_session)
    slides = await service.replace_slides(
        project_id,
        CreateSlidesRequest(
            slides=[
                SlideCreate(title="First", description="First", content="First"),
                SlideCreate(title="Second", description="Second", content="Second"),
                SlideCreate(title="Third", description="Third", content="Third"),
            ]
        ),
    )
    db_session.add(
        DialogueModel(
            id="dialogue-delete",
            slide_id=slides[1].id,
            role="旁白",
            content="Delete with slide",
            emotion="无明显情感",
            speed="中速",
            idx=1,
            audio_path=None,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
    )
    await db_session.commit()

    await service.delete_slide(project_id, slides[1].id)

    remaining = await service.slides.list_by_project(project_id)
    assert [slide.id for slide in remaining] == [slides[0].id, slides[2].id]
    assert [slide.idx for slide in remaining] == [1, 2]
    assert await service.dialogues.list_by_slide(slides[1].id) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reorder_slides_updates_sequence(db_session) -> None:
    project_id = await _create_project(db_session)
    service = SlideResourceService(db_session)
    slides = await service.replace_slides(
        project_id,
        CreateSlidesRequest(
            slides=[
                SlideCreate(title="First", description="First", content="First"),
                SlideCreate(title="Second", description="Second", content="Second"),
                SlideCreate(title="Third", description="Third", content="Third"),
            ]
        ),
    )

    reordered = await service.reorder_slides(project_id, [slides[2].id, slides[0].id, slides[1].id])

    assert [(slide.id, slide.idx) for slide in reordered] == [
        (slides[2].id, 1),
        (slides[0].id, 2),
        (slides[1].id, 3),
    ]
    stored = await service.list_slides(project_id)
    assert [slide.id for slide in stored] == [slides[2].id, slides[0].id, slides[1].id]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reorder_slides_rejects_non_matching_slide_ids(db_session) -> None:
    project_id = await _create_project(db_session)
    service = SlideResourceService(db_session)
    slides = await service.replace_slides(
        project_id,
        CreateSlidesRequest(
            slides=[
                SlideCreate(title="First", description="First", content="First"),
                SlideCreate(title="Second", description="Second", content="Second"),
            ]
        ),
    )

    with pytest.raises(BadRequestError, match="slide_ids must match existing slides"):
        await service.reorder_slides(project_id, [slides[0].id])

    with pytest.raises(BadRequestError, match="slide_ids must match existing slides"):
        await service.reorder_slides(project_id, [slides[0].id, slides[0].id])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_slide_appends_to_end(db_session) -> None:
    project_id = await _create_project(db_session)
    service = SlideResourceService(db_session)
    await service.replace_slides(
        project_id,
        CreateSlidesRequest(
            slides=[
                SlideCreate(title="First", description="First", content="First"),
                SlideCreate(title="Second", description="Second", content="Second"),
            ]
        ),
    )

    created = await service.add_slide(
        project_id,
        SlideCreate(type=SlideType.ENDING, title="Third", description="Third", content="Third"),
    )

    assert created.idx == 3
    assert created.type == SlideType.ENDING
    assert created.image_path is None
    assert created.audio_path is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_image_and_audio_paths_update_slide(db_session) -> None:
    project_id = await _create_project(db_session)
    service = SlideResourceService(db_session)
    created = await service.add_slide(project_id, SlideCreate(title="Only", description="Only", content="Only"))

    await service.set_image_path(created.id, "/tmp/image.png")
    await service.set_audio_path(created.id, "/tmp/audio.mp3")

    stored = await service.slides.get(project_id, created.id)
    assert stored is not None
    assert stored.image_path == "/tmp/image.png"
    assert stored.audio_path == "/tmp/audio.mp3"
    assert stored.updated_at >= created.updated_at


@pytest.mark.unit
@pytest.mark.asyncio
async def test_slide_service_raises_not_found_for_missing_resources(db_session) -> None:
    service = SlideResourceService(db_session)
    project_id = await _create_project(db_session)
    existing_slide = await service.add_slide(project_id, SlideCreate(title="Only", description="Only", content="Only"))

    with pytest.raises(NotFoundError, match="Project not found"):
        await service.replace_slides("missing-project", CreateSlidesRequest(slides=[]))

    with pytest.raises(NotFoundError, match="Project not found"):
        await service.list_slides("missing-project")

    with pytest.raises(NotFoundError, match="Project not found"):
        await service.add_slide("missing-project", SlideCreate(title="Only", description="Only", content="Only"))

    with pytest.raises(NotFoundError, match="Project not found"):
        await service.update_slide("missing-project", existing_slide.id, UpdateSlideRequest(title="Updated"))

    with pytest.raises(NotFoundError, match="Project not found"):
        await service.delete_slide("missing-project", existing_slide.id)

    with pytest.raises(NotFoundError, match="Project not found"):
        await service.reorder_slides("missing-project", [existing_slide.id])

    with pytest.raises(NotFoundError, match="Slide not found"):
        await service.update_slide(project_id, "missing-slide", UpdateSlideRequest(title="Updated"))

    with pytest.raises(NotFoundError, match="Slide not found"):
        await service.delete_slide(project_id, "missing-slide")

    with pytest.raises(NotFoundError, match="Slide not found"):
        await service.set_image_path("missing-slide", "/tmp/image.png")

    with pytest.raises(NotFoundError, match="Slide not found"):
        await service.set_audio_path("missing-slide", "/tmp/audio.mp3")
