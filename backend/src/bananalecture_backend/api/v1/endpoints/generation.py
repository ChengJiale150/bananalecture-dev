from fastapi import APIRouter, status

from bananalecture_backend.api.v1.deps import (
    CancelPipelineUseCaseDep,
    GenerationSessionServiceDep,
    PausePipelineUseCaseDep,
    ResumePipelineUseCaseDep,
    RunPipelineUseCaseDep,
)
from bananalecture_backend.core.errors import NotFoundError

router = APIRouter()


@router.post("/projects/{project_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def start_generation(project_id: str, use_case: RunPipelineUseCaseDep) -> dict[str, object]:
    """Start a full generation pipeline (images → dialogues → audio → video)."""
    session_id = await use_case.execute(project_id)
    return {
        "code": status.HTTP_202_ACCEPTED,
        "message": "生成任务已启动",
        "data": {"session_id": session_id, "project_id": project_id},
    }


_NO_SESSION_MSG = "No generation session for this project"


@router.get("/projects/{project_id}/generation")
async def get_generation(
    project_id: str,
    service: GenerationSessionServiceDep,
) -> dict[str, object]:
    """Get the current generation pipeline status for a project."""
    session_obj = await service.get_active_by_project(project_id)
    if session_obj is None:
        raise NotFoundError(_NO_SESSION_MSG)

    response = await service.build_response(session_obj.id)
    return {"code": status.HTTP_200_OK, "message": "success", "data": response.model_dump(mode="json")}


@router.post("/projects/{project_id}/generation/pause")
async def pause_generation(project_id: str, use_case: PausePipelineUseCaseDep) -> dict[str, object]:
    """Pause the generation pipeline."""
    response = await use_case.execute(project_id)
    return {
        "code": status.HTTP_200_OK,
        "message": "生成任务已暂停",
        "data": response.model_dump(mode="json"),
    }


@router.post("/projects/{project_id}/generation/resume", status_code=status.HTTP_202_ACCEPTED)
async def resume_generation(project_id: str, use_case: ResumePipelineUseCaseDep) -> dict[str, object]:
    """Resume a paused or recover a failed generation pipeline."""
    response = await use_case.execute(project_id)
    return {
        "code": status.HTTP_202_ACCEPTED,
        "message": "生成任务已恢复",
        "data": response.model_dump(mode="json"),
    }


@router.delete("/projects/{project_id}/generation")
async def cancel_generation(project_id: str, use_case: CancelPipelineUseCaseDep) -> dict[str, object]:
    """Cancel the generation pipeline."""
    response = await use_case.execute(project_id)
    return {
        "code": status.HTTP_200_OK,
        "message": "生成任务已取消",
        "data": response.model_dump(mode="json"),
    }
