from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from bananalecture_backend.api.v1.deps import (
    AssetStoreDep,
    ProjectResourceServiceDep,
    QueueProjectVideoGenerationUseCaseDep,
)

router = APIRouter()


@router.post("/projects/{project_id}/video/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_video(
    project_id: str,
    use_case: QueueProjectVideoGenerationUseCaseDep,
) -> dict[str, object]:
    """Queue video generation."""
    task_id = await use_case.execute(project_id)
    return {
        "code": status.HTTP_202_ACCEPTED,
        "message": "视频生成任务已创建",
        "data": {"task_id": task_id, "project_id": project_id},
    }


@router.get("/projects/{project_id}/video/file")
async def get_video_file(
    project_id: str,
    service: ProjectResourceServiceDep,
    asset_store: AssetStoreDep,
) -> FileResponse:
    """Return generated project video."""
    path = asset_store.resolve_file(await service.get_video_path(project_id))
    return FileResponse(path=path, media_type="video/mp4", filename="project-video.mp4")
