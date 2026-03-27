from datetime import UTC, datetime

import pytest

from bananalecture_backend.core.errors import NotFoundError
from bananalecture_backend.models import ProjectModel, SlideModel
from bananalecture_backend.schemas.project import CreateProjectRequest, UpdateProjectRequest
from bananalecture_backend.services.resources import ProjectResourceService


async def _create_project(
    service: ProjectResourceService,
    *,
    name: str,
    user_id: str = "admin",
) -> str:
    project = await service.create_project(CreateProjectRequest(name=name, user_id=user_id))
    return project.id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_project_persists_expected_defaults(db_session) -> None:
    service = ProjectResourceService(db_session)

    project = await service.create_project(CreateProjectRequest(name="Physics lesson", user_id="teacher-1"))

    stored = await service.projects.get(project.id)
    assert stored is not None
    assert project.user_id == "teacher-1"
    assert project.name == "Physics lesson"
    assert project.messages is None
    assert project.video_path is None
    assert project.created_at == project.updated_at
    assert stored.id == project.id
    assert stored.created_at == project.created_at
    assert stored.updated_at == project.updated_at


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_projects_filters_by_user_and_builds_pagination(db_session) -> None:
    service = ProjectResourceService(db_session)
    first_id = await _create_project(service, name="Alpha", user_id="admin")
    second_id = await _create_project(service, name="Beta", user_id="admin")
    await _create_project(service, name="Gamma", user_id="other-user")

    items, pagination = await service.list_projects(
        user_id="admin",
        page=2,
        page_size=1,
        sort_by="name",
        order="asc",
    )

    assert [item.id for item in items] == [second_id]
    assert pagination.page == 2
    assert pagination.page_size == 1
    assert pagination.total == 2
    assert pagination.total_pages == 2
    assert items[0].name == "Beta"
    assert items[0].id != first_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_project_detail_returns_project_with_ordered_slides(db_session) -> None:
    service = ProjectResourceService(db_session)
    project_id = await _create_project(service, name="Deck")
    db_session.add_all(
        [
            SlideModel(
                id="slide-b",
                project_id=project_id,
                type="content",
                title="Second",
                description="B",
                content="B",
                idx=2,
                image_path=None,
                audio_path=None,
                created_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            ),
            SlideModel(
                id="slide-a",
                project_id=project_id,
                type="cover",
                title="First",
                description="A",
                content="A",
                idx=1,
                image_path=None,
                audio_path=None,
                created_at=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
                updated_at=datetime(2023, 1, 1, 0, 0, tzinfo=UTC),
            ),
        ]
    )
    await db_session.commit()

    detail = await service.get_project_detail(project_id)

    assert detail.id == project_id
    assert [slide.id for slide in detail.slides] == ["slide-a", "slide-b"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_project_can_change_name_or_messages(db_session) -> None:
    service = ProjectResourceService(db_session)
    project_id = await _create_project(service, name="Original")
    before = await service.get_project_detail(project_id)

    renamed = await service.update_project(project_id, UpdateProjectRequest(name="Renamed"))
    remessaged = await service.update_project(project_id, UpdateProjectRequest(messages='["hello"]'))
    both = await service.update_project(
        project_id,
        UpdateProjectRequest(name="Final", messages='["world"]'),
    )

    assert renamed.name == "Renamed"
    assert renamed.messages is None
    assert renamed.updated_at >= before.updated_at
    assert remessaged.name == "Renamed"
    assert remessaged.messages == '["hello"]'
    assert remessaged.updated_at >= renamed.updated_at
    assert both.name == "Final"
    assert both.messages == '["world"]'
    assert both.updated_at >= remessaged.updated_at


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_project_removes_project_and_cascades_slides(db_session) -> None:
    service = ProjectResourceService(db_session)
    project_id = await _create_project(service, name="Delete me")
    db_session.add(
        SlideModel(
            id="slide-1",
            project_id=project_id,
            type="content",
            title="Slide",
            description="desc",
            content="body",
            idx=1,
            image_path=None,
            audio_path=None,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        )
    )
    await db_session.commit()

    await service.delete_project(project_id)

    assert await service.projects.get(project_id) is None
    assert await service.slides.list_by_project(project_id) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_project_service_raises_not_found_for_missing_project(db_session) -> None:
    service = ProjectResourceService(db_session)

    with pytest.raises(NotFoundError, match="Project not found"):
        await service.get_project_detail("missing-project")

    with pytest.raises(NotFoundError, match="Project not found"):
        await service.update_project("missing-project", UpdateProjectRequest(name="Updated"))

    with pytest.raises(NotFoundError, match="Project not found"):
        await service.delete_project("missing-project")
