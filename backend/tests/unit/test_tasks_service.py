import asyncio
from datetime import UTC

import pytest

from bananalecture_backend.application.use_cases.tasks import CancelTaskUseCase, launch_task
from bananalecture_backend.core.errors import NotFoundError
from bananalecture_backend.db.repositories import TaskRepository
from bananalecture_backend.infrastructure.task_runtime import InMemoryBackgroundTaskRunner
from bananalecture_backend.schemas.project import CreateProjectRequest
from bananalecture_backend.schemas.task import TaskStatus, TaskType
from bananalecture_backend.services.resources import ProjectResourceService, TaskRecordService


async def _create_project(db_session, *, name: str = "Deck", user_id: str = "admin") -> str:
    project = await ProjectResourceService(db_session).create_project(CreateProjectRequest(name=name, user_id=user_id))
    return project.id


async def _get_stored_task(database_manager, task_id: str):
    async with database_manager.session_factory() as session:
        return await TaskRepository(session).get(task_id)


async def _wait_for_task_status(
    database_manager,
    task_id: str,
    expected_status: TaskStatus,
    *,
    timeout_seconds: float = 1.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        task = await _get_stored_task(database_manager, task_id)
        if task is not None and task.status == expected_status.value:
            return
        await asyncio.sleep(0.01)
    pytest.fail(f"task {task_id} did not reach status {expected_status.value}")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_task_persists_expected_defaults(db_session) -> None:
    project_id = await _create_project(db_session)

    task = await TaskRecordService(db_session).create_task(project_id, TaskType.AUDIO_GENERATION, 3)

    stored = await TaskRecordService(db_session).tasks.get(task.id)
    assert stored is not None
    assert task.id.startswith("task-")
    assert task.project_id == project_id
    assert task.type == TaskType.AUDIO_GENERATION
    assert task.status == TaskStatus.PENDING
    assert task.current_step == 0
    assert task.total_steps == 3
    assert task.error_message is None
    assert task.created_at == task.updated_at
    assert stored.created_at == task.created_at
    assert stored.updated_at == task.updated_at
    assert task.created_at.tzinfo == UTC


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_task_returns_task_and_raises_not_found_for_missing_task(db_session) -> None:
    project_id = await _create_project(db_session)
    created = await TaskRecordService(db_session).create_task(project_id, TaskType.IMAGE_GENERATION, 2)

    loaded = await TaskRecordService(db_session).get_task(created.id)

    assert loaded.id == created.id
    assert loaded.project_id == project_id
    assert loaded.type == TaskType.IMAGE_GENERATION

    with pytest.raises(NotFoundError, match="Task not found"):
        await TaskRecordService(db_session).get_task("missing-task")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_task_marks_non_terminal_task_cancelled_and_calls_runtime(db_session) -> None:
    project_id = await _create_project(db_session)
    service = TaskRecordService(db_session)
    task = await service.create_task(project_id, TaskType.VIDEO_GENERATION, 1)
    runtime = InMemoryBackgroundTaskRunner()

    cancelled_task_ids: list[str] = []

    def _cancel(task_id: str) -> bool:
        cancelled_task_ids.append(task_id)
        return True

    runtime.cancel = _cancel

    cancelled = await CancelTaskUseCase(db_session, runtime).execute(task.id)

    stored = await service.tasks.get(task.id)
    assert stored is not None
    assert cancelled.id == task.id
    assert cancelled.status == TaskStatus.CANCELLED
    assert cancelled.error_message == "Task cancelled"
    assert stored.status == TaskStatus.CANCELLED.value
    assert stored.error_message == "Task cancelled"
    assert stored.updated_at >= stored.created_at
    assert cancelled_task_ids == [task.id]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_task_returns_terminal_task_without_runtime_cancel(db_session) -> None:
    project_id = await _create_project(db_session)
    service = TaskRecordService(db_session)
    task = await service.create_task(project_id, TaskType.DIALOGUE_GENERATION, 2)
    stored = await service.tasks.get(task.id)
    assert stored is not None
    stored.status = TaskStatus.COMPLETED.value
    stored.current_step = stored.total_steps
    stored.updated_at = stored.created_at
    await db_session.commit()

    runtime = InMemoryBackgroundTaskRunner()
    runtime.cancel = lambda _: pytest.fail("runtime.cancel should not be called for terminal tasks")

    cancelled = await CancelTaskUseCase(db_session, runtime).execute(task.id)

    refreshed = await service.tasks.get(task.id)
    assert refreshed is not None
    assert cancelled.status == TaskStatus.COMPLETED
    assert cancelled.current_step == refreshed.total_steps
    assert cancelled.error_message is None
    assert refreshed.status == TaskStatus.COMPLETED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_task_raises_not_found_for_missing_task(db_session) -> None:
    with pytest.raises(NotFoundError, match="Task not found"):
        await CancelTaskUseCase(db_session, InMemoryBackgroundTaskRunner()).execute("missing-task")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_launch_task_marks_task_completed_after_successful_work(db_session, database_manager) -> None:
    project_id = await _create_project(db_session)
    task = await TaskRecordService(db_session).create_task(project_id, TaskType.IMAGE_GENERATION, 4)
    runtime = InMemoryBackgroundTaskRunner()
    work_started = asyncio.Event()

    async def work(_: str, __) -> None:
        work_started.set()

    launch_task(task, runtime, database_manager.session_factory, work)

    await work_started.wait()
    runner = runtime._tasks[task.id]
    await runner
    await _wait_for_task_status(database_manager, task.id, TaskStatus.COMPLETED)

    stored = await _get_stored_task(database_manager, task.id)
    assert stored is not None
    assert stored.status == TaskStatus.COMPLETED.value
    assert stored.current_step == stored.total_steps == 4
    assert stored.error_message is None
    assert task.id not in runtime._tasks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_launch_task_marks_task_failed_when_work_raises(db_session, database_manager) -> None:
    project_id = await _create_project(db_session)
    task = await TaskRecordService(db_session).create_task(project_id, TaskType.AUDIO_GENERATION, 2)
    runtime = InMemoryBackgroundTaskRunner()

    async def work(_: str, __) -> None:
        raise RuntimeError("generation exploded")

    launch_task(task, runtime, database_manager.session_factory, work)

    runner = runtime._tasks[task.id]
    await runner
    await _wait_for_task_status(database_manager, task.id, TaskStatus.FAILED)

    stored = await _get_stored_task(database_manager, task.id)
    assert stored is not None
    assert stored.status == TaskStatus.FAILED.value
    assert stored.error_message == "generation exploded"
    assert task.id not in runtime._tasks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_launch_task_marks_task_cancelled_when_runtime_cancels_it(db_session, database_manager) -> None:
    project_id = await _create_project(db_session)
    task = await TaskRecordService(db_session).create_task(project_id, TaskType.VIDEO_GENERATION, 1)
    runtime = InMemoryBackgroundTaskRunner()
    work_started = asyncio.Event()

    async def work(_: str, __) -> None:
        work_started.set()
        await asyncio.sleep(5)

    launch_task(task, runtime, database_manager.session_factory, work)

    await work_started.wait()
    assert runtime.cancel(task.id) is True
    runner = runtime._tasks[task.id]
    with pytest.raises(asyncio.CancelledError):
        await runner
    await _wait_for_task_status(database_manager, task.id, TaskStatus.CANCELLED)

    stored = await _get_stored_task(database_manager, task.id)
    assert stored is not None
    assert stored.status == TaskStatus.CANCELLED.value
    assert stored.error_message == "Task cancelled"
    assert task.id not in runtime._tasks
