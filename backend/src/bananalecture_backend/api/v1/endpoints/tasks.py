from fastapi import APIRouter, status

from bananalecture_backend.api.v1.deps import (
    CancelTaskUseCaseDep,
    PauseTaskUseCaseDep,
    ResumeTaskUseCaseDep,
    TaskRecordServiceDep,
)

router = APIRouter()


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, service: TaskRecordServiceDep) -> dict[str, object]:
    """Get task status."""
    task = await service.get_task(task_id)
    return {"code": status.HTTP_200_OK, "message": "success", "data": task.model_dump(mode="json")}


@router.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str, use_case: PauseTaskUseCaseDep) -> dict[str, object]:
    """Pause a running task gracefully."""
    task = await use_case.execute(task_id)
    return {"code": status.HTTP_200_OK, "message": "任务已暂停", "data": task.model_dump(mode="json")}


@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str, use_case: ResumeTaskUseCaseDep) -> dict[str, object]:
    """Resume a paused or failed task from its last checkpoint."""
    task = await use_case.execute(task_id)
    return {"code": status.HTTP_202_ACCEPTED, "message": "任务已恢复", "data": task.model_dump(mode="json")}


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str, use_case: CancelTaskUseCaseDep) -> dict[str, object]:
    """Cancel a task if it is still running."""
    task = await use_case.execute(task_id)
    return {"code": status.HTTP_200_OK, "message": "任务已取消", "data": task.model_dump(mode="json")}
