from bananalecture_backend.services.resources import GenerationSessionService, TaskRecordService
from bananalecture_backend.schemas.task import TaskType


async def _create_project(db_session):
    from bananalecture_backend.schemas.project import CreateProjectRequest
    from bananalecture_backend.services.resources import ProjectResourceService

    project = await ProjectResourceService(db_session).create_project("admin", CreateProjectRequest(name="Test"))
    return project.id


async def _create_slide(db_session, project_id):
    from bananalecture_backend.models.entities import SlideModel
    from bananalecture_backend.core.time import utc_now
    import uuid

    slide = SlideModel(
        id=str(uuid.uuid4()),
        project_id=project_id,
        type="content",
        title="Test Slide",
        description="Test Description",
        content="Test Content",
        idx=0,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(slide)
    await db_session.commit()
    return slide.id


import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_session_persists_defaults(db_session) -> None:
    project_id = await _create_project(db_session)
    svc = GenerationSessionService(db_session)

    session_model = await svc.create_session(project_id)

    assert session_model.id.startswith("gs-")
    assert session_model.project_id == project_id
    assert session_model.status == "running"
    assert session_model.current_phase == 0
    assert session_model.current_task_id is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_active_by_project_returns_none_when_no_session(db_session) -> None:
    project_id = await _create_project(db_session)
    svc = GenerationSessionService(db_session)

    result = await svc.get_active_by_project(project_id)

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_phase_updates_session(db_session) -> None:
    project_id = await _create_project(db_session)
    svc = GenerationSessionService(db_session)
    session_obj = await svc.create_session(project_id)

    await svc.mark_phase(session_obj.id, 1, task_id="task-123")

    refreshed = await svc.get_session(session_obj.id)
    assert refreshed.current_phase == 1
    assert refreshed.current_task_id == "task-123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_completed_sets_status(db_session) -> None:
    project_id = await _create_project(db_session)
    svc = GenerationSessionService(db_session)
    session_obj = await svc.create_session(project_id)

    await svc.mark_completed(session_obj.id)

    refreshed = await svc.get_session(session_obj.id)
    assert refreshed.status == "completed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_failed_stores_error(db_session) -> None:
    project_id = await _create_project(db_session)
    svc = GenerationSessionService(db_session)
    session_obj = await svc.create_session(project_id)

    await svc.mark_failed(session_obj.id, "Something went wrong")

    refreshed = await svc.get_session(session_obj.id)
    assert refreshed.status == "failed"
    assert refreshed.error_message == "Something went wrong"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_paused_and_running(db_session) -> None:
    project_id = await _create_project(db_session)
    svc = GenerationSessionService(db_session)
    session_obj = await svc.create_session(project_id)

    await svc.mark_paused(session_obj.id)
    refreshed = await svc.get_session(session_obj.id)
    assert refreshed.status == "paused"

    await svc.mark_running(session_obj.id)
    refreshed = await svc.get_session(session_obj.id)
    assert refreshed.status == "running"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_response_contains_all_phases(db_session) -> None:
    project_id = await _create_project(db_session)
    svc = GenerationSessionService(db_session)
    session_obj = await svc.create_session(project_id)

    response = await svc.build_response(session_obj.id)

    assert response.session_id == session_obj.id
    assert response.project_id == project_id
    assert response.status == "running"
    assert response.current_phase == 0
    assert len(response.phases) == 4
    assert response.phases[0].phase == "images"
    assert response.phases[1].phase == "dialogues"
    assert response.phases[2].phase == "audio"
    assert response.phases[3].phase == "video"
    assert response.phases[0].status == "running"
    assert response.phases[1].status == "pending"
    assert response.phases[2].status == "pending"
    assert response.phases[3].status == "pending"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_response_shows_task_progress(db_session) -> None:
    project_id = await _create_project(db_session)
    await _create_slide(db_session, project_id)
    svc = GenerationSessionService(db_session)
    tasks_svc = TaskRecordService(db_session)

    session_obj = await svc.create_session(project_id)
    task = await tasks_svc.create_task(project_id, TaskType.IMAGE_GENERATION, 3)
    await svc.mark_phase(session_obj.id, 0, task_id=task.id)

    response = await svc.build_response(session_obj.id)

    phase0 = response.phases[0]
    assert phase0.task.task_id == task.id
    assert phase0.task.status == "pending"
    assert phase0.task.total_steps == 3
    assert phase0.task.current_step == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_session_raises_not_found(db_session) -> None:
    svc = GenerationSessionService(db_session)
    from bananalecture_backend.core.errors import NotFoundError

    with pytest.raises(NotFoundError, match="Generation session not found"):
        await svc.get_session("gs-nonexistent")
