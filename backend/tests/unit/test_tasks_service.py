import asyncio
from datetime import UTC, timedelta

import pytest

from bananalecture_backend.application.use_cases.tasks import CancelTaskUseCase, PauseTaskUseCase, launch_task
from bananalecture_backend.core.config import Settings
from bananalecture_backend.core.errors import NotFoundError
from bananalecture_backend.core.time import utc_now
from bananalecture_backend.db.repositories import TaskRepository
from bananalecture_backend.infrastructure.task_runtime import InMemoryBackgroundTaskRunner
from bananalecture_backend.schemas.project import CreateProjectRequest
from bananalecture_backend.schemas.task import TaskStatus, TaskType
from bananalecture_backend.services.resources import ProjectResourceService, TaskRecordService


async def _create_project(db_session, *, name: str = "Deck", user_id: str = "admin") -> str:
    project = await ProjectResourceService(db_session).create_project(user_id, CreateProjectRequest(name=name))
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
async def test_cancel_task_marks_non_terminal_task_cancelled_and_calls_runtime(
    db_session, test_settings: Settings
) -> None:
    project_id = await _create_project(db_session)
    service = TaskRecordService(db_session)
    task = await service.create_task(project_id, TaskType.VIDEO_GENERATION, 1)
    runtime = InMemoryBackgroundTaskRunner()

    cancelled_task_ids: list[str] = []

    def _cancel(task_id: str) -> bool:
        cancelled_task_ids.append(task_id)
        return True

    runtime.cancel = _cancel

    cancelled = await CancelTaskUseCase(db_session, runtime, test_settings).execute(task.id)

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
async def test_cancel_task_returns_terminal_task_without_runtime_cancel(db_session, test_settings: Settings) -> None:
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

    cancelled = await CancelTaskUseCase(db_session, runtime, test_settings).execute(task.id)

    refreshed = await service.tasks.get(task.id)
    assert refreshed is not None
    assert cancelled.status == TaskStatus.COMPLETED
    assert cancelled.current_step == refreshed.total_steps
    assert cancelled.error_message is None
    assert refreshed.status == TaskStatus.COMPLETED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cancel_task_raises_not_found_for_missing_task(db_session, test_settings: Settings) -> None:
    with pytest.raises(NotFoundError, match="Task not found"):
        await CancelTaskUseCase(db_session, InMemoryBackgroundTaskRunner(), test_settings).execute("missing-task")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_launch_task_marks_task_completed_after_successful_work(
    db_session, database_manager, test_settings: Settings
) -> None:
    project_id = await _create_project(db_session)
    task = await TaskRecordService(db_session).create_task(project_id, TaskType.IMAGE_GENERATION, 4)
    runtime = InMemoryBackgroundTaskRunner()
    work_started = asyncio.Event()

    async def work(_: str, __) -> None:
        work_started.set()

    launch_task(task, runtime, database_manager.session_factory, test_settings, work)

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
async def test_launch_task_marks_task_failed_when_work_raises(
    db_session, database_manager, test_settings: Settings
) -> None:
    project_id = await _create_project(db_session)
    task = await TaskRecordService(db_session).create_task(project_id, TaskType.AUDIO_GENERATION, 2)
    runtime = InMemoryBackgroundTaskRunner()

    async def work(_: str, __) -> None:
        raise RuntimeError("generation exploded")

    launch_task(task, runtime, database_manager.session_factory, test_settings, work)

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
async def test_launch_task_marks_task_cancelled_when_runtime_cancels_it(
    db_session, database_manager, test_settings: Settings
) -> None:
    project_id = await _create_project(db_session)
    task = await TaskRecordService(db_session).create_task(project_id, TaskType.VIDEO_GENERATION, 1)
    runtime = InMemoryBackgroundTaskRunner()
    work_started = asyncio.Event()

    async def work(_: str, __) -> None:
        work_started.set()
        await asyncio.sleep(5)

    launch_task(task, runtime, database_manager.session_factory, test_settings, work)

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


# ----- Pause tests -----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_paused_changes_running_task_to_paused(db_session) -> None:
    project_id = await _create_project(db_session)
    service = TaskRecordService(db_session)
    task = await service.create_task(project_id, TaskType.IMAGE_GENERATION, 3)
    await service.mark_running(task.id)

    await service.mark_paused(task.id)

    stored = await service.tasks.get(task.id)
    assert stored is not None
    assert stored.status == TaskStatus.PAUSED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_paused_skips_cancelled_or_completed_tasks(db_session) -> None:
    project_id = await _create_project(db_session)
    service = TaskRecordService(db_session)
    task = await service.create_task(project_id, TaskType.DIALOGUE_GENERATION, 2)

    # Completed task
    stored = await service.tasks.get(task.id)
    assert stored is not None
    stored.status = TaskStatus.COMPLETED.value
    await db_session.commit()
    await service.mark_paused(task.id)
    refreshed = await service.tasks.get(task.id)
    assert refreshed is not None
    assert refreshed.status == TaskStatus.COMPLETED.value

    # Cancelled task
    task2 = await service.create_task(project_id, TaskType.DIALOGUE_GENERATION, 2)
    stored2 = await service.tasks.get(task2.id)
    assert stored2 is not None
    stored2.status = TaskStatus.CANCELLED.value
    await db_session.commit()
    await service.mark_paused(task2.id)
    refreshed2 = await service.tasks.get(task2.id)
    assert refreshed2 is not None
    assert refreshed2.status == TaskStatus.CANCELLED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_running_accepts_paused_and_failed_status(db_session) -> None:
    project_id = await _create_project(db_session)
    service = TaskRecordService(db_session)
    task = await service.create_task(project_id, TaskType.IMAGE_GENERATION, 3)

    # PENDING → RUNNING (original behavior)
    await service.mark_running(task.id)
    stored = await service.tasks.get(task.id)
    assert stored is not None
    assert stored.status == TaskStatus.RUNNING.value

    # RUNNING → PAUSED → RUNNING
    await service.mark_paused(task.id)
    await service.mark_running(task.id)
    stored = await service.tasks.get(task.id)
    assert stored is not None
    assert stored.status == TaskStatus.RUNNING.value

    # FAILED → RUNNING
    stored.status = TaskStatus.FAILED.value
    await db_session.commit()
    await service.mark_running(task.id)
    stored = await service.tasks.get(task.id)
    assert stored is not None
    assert stored.status == TaskStatus.RUNNING.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pause_task_use_case_marks_running_task_paused(db_session, test_settings: Settings) -> None:
    project_id = await _create_project(db_session)
    service = TaskRecordService(db_session)
    task = await service.create_task(project_id, TaskType.AUDIO_GENERATION, 3)
    await service.mark_running(task.id)
    runtime = InMemoryBackgroundTaskRunner()
    runtime.start(task.id, asyncio.sleep(10))

    paused = await PauseTaskUseCase(db_session, runtime, test_settings).execute(task.id)

    assert paused.status == TaskStatus.PAUSED
    stored = await service.tasks.get(task.id)
    assert stored is not None
    assert stored.status == TaskStatus.PAUSED.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pause_task_use_case_no_ops_for_terminal_tasks(db_session, test_settings: Settings) -> None:
    project_id = await _create_project(db_session)
    service = TaskRecordService(db_session)
    runtime = InMemoryBackgroundTaskRunner()

    # Completed task
    task = await service.create_task(project_id, TaskType.IMAGE_GENERATION, 2)
    stored = await service.tasks.get(task.id)
    assert stored is not None
    stored.status = TaskStatus.COMPLETED.value
    await db_session.commit()
    result = await PauseTaskUseCase(db_session, runtime, test_settings).execute(task.id)
    assert result.status == TaskStatus.COMPLETED

    # Failed task
    task2 = await service.create_task(project_id, TaskType.IMAGE_GENERATION, 2)
    stored2 = await service.tasks.get(task2.id)
    assert stored2 is not None
    stored2.status = TaskStatus.FAILED.value
    await db_session.commit()
    result2 = await PauseTaskUseCase(db_session, runtime, test_settings).execute(task2.id)
    assert result2.status == TaskStatus.FAILED


# ----- Runtime pause/resume tests -----


@pytest.mark.unit
@pytest.mark.asyncio
async def test_runtime_pause_and_resume_controls_event(db_session) -> None:
    runtime = InMemoryBackgroundTaskRunner()

    async def dummy() -> None:
        pass

    runtime.start("task-1", dummy())
    await asyncio.sleep(0)

    # Initially event is set (not paused)
    assert runtime.pause("task-1") is True
    # Resume unblocks
    assert runtime.resume("task-1") is True
    # Pausing non-existent task returns False
    assert runtime.pause("task-none") is False
    assert runtime.resume("task-none") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wait_if_paused_does_not_block_when_not_paused(db_session) -> None:
    runtime = InMemoryBackgroundTaskRunner()

    async def dummy() -> None:
        pass

    runtime.start("task-1", dummy())
    await asyncio.sleep(0)

    # When not paused, wait_if_paused returns immediately
    await runtime.wait_if_paused("task-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_wait_if_paused_blocks_and_resume_unblocks(db_session) -> None:
    runtime = InMemoryBackgroundTaskRunner()
    task_id = "task-blocking"

    # Use a work coroutine that stays alive
    work_running = asyncio.Event()

    async def long_work() -> None:
        work_running.set()
        await asyncio.sleep(300)  # Keep alive

    runtime.start(task_id, long_work())
    await work_running.wait()

    # Now that task is alive, pause it (clear the event)
    runtime.pause(task_id)

    unblocked = asyncio.Event()

    async def waiter() -> None:
        await runtime.wait_if_paused(task_id)
        unblocked.set()

    waiter_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.05)
    assert not unblocked.is_set()

    # Resume unblocks it
    runtime.resume(task_id)
    await asyncio.wait_for(unblocked.wait(), timeout=1.0)
    assert unblocked.is_set()
    waiter_task.cancel()
    # Clean up the running task
    runtime.cancel(task_id)
