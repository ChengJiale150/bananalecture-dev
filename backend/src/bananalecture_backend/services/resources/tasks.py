# ruff: noqa: D102, D107, EM101, TRY003

from sqlalchemy.ext.asyncio import AsyncSession

from bananalecture_backend.core.errors import NotFoundError
from bananalecture_backend.core.time import utc_now
from bananalecture_backend.db.repositories import TaskRepository
from bananalecture_backend.models import TaskModel
from bananalecture_backend.schemas.task import Task, TaskStatus, TaskType
from bananalecture_backend.services.utils import new_id


class TaskRecordService:
    """Resource operations for task records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tasks = TaskRepository(session)

    async def create_task(self, project_id: str, task_type: TaskType, total_steps: int) -> Task:
        timestamp = utc_now()
        task = TaskModel(
            id=f"task-{new_id()}",
            project_id=project_id,
            type=task_type.value,
            status=TaskStatus.PENDING.value,
            current_step=0,
            total_steps=total_steps,
            error_message=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        await self.tasks.create(task)
        await self.session.commit()
        return Task.model_validate(task)

    async def get_task(self, task_id: str) -> Task:
        task = await self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        return Task.model_validate(task)

    async def mark_running(self, task_id: str) -> None:
        await self._update_task(
            task_id,
            {"status": TaskStatus.RUNNING.value, "updated_at": utc_now()},
            allowed_current_statuses={TaskStatus.PENDING.value},
        )

    async def mark_progress(self, task_id: str, current_step: int) -> None:
        await self._update_task(
            task_id,
            {"current_step": current_step, "updated_at": utc_now()},
            skipped_current_statuses={TaskStatus.CANCELLED.value},
        )

    async def mark_completed(self, task_id: str) -> None:
        task = await self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        if task.status == TaskStatus.CANCELLED.value:
            return
        await self.tasks.update(
            task,
            {
                "status": TaskStatus.COMPLETED.value,
                "current_step": task.total_steps,
                "updated_at": utc_now(),
            },
        )
        await self.session.commit()

    async def mark_failed(self, task_id: str, error_message: str) -> None:
        await self._update_task(
            task_id,
            {
                "status": TaskStatus.FAILED.value,
                "error_message": error_message,
                "updated_at": utc_now(),
            },
            skipped_current_statuses={TaskStatus.CANCELLED.value},
        )

    async def mark_cancelled(self, task_id: str, error_message: str = "Task cancelled") -> None:
        await self._update_task(
            task_id,
            {
                "status": TaskStatus.CANCELLED.value,
                "error_message": error_message,
                "updated_at": utc_now(),
            },
            skipped_current_statuses={TaskStatus.CANCELLED.value},
        )

    async def _update_task(
        self,
        task_id: str,
        values: dict[str, object],
        *,
        allowed_current_statuses: set[str] | None = None,
        skipped_current_statuses: set[str] | None = None,
    ) -> None:
        task = await self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        if allowed_current_statuses is not None and task.status not in allowed_current_statuses:
            return
        if skipped_current_statuses is not None and task.status in skipped_current_statuses:
            return
        await self.tasks.update(task, values)
        await self.session.commit()
