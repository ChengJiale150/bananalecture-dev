from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from bananalecture_backend.api.v1.deps import (
    AssetStoreDep,
    DialogueResourceServiceDep,
    GenerateSlideAudioUseCaseDep,
    QueueBatchAudioGenerationUseCaseDep,
    SlideResourceServiceDep,
)

router = APIRouter()


@router.post("/projects/{project_id}/slides/{slide_id}/audio/generate")
async def generate_slide_audio(
    project_id: str,
    slide_id: str,
    use_case: GenerateSlideAudioUseCaseDep,
) -> dict[str, object]:
    """Generate dialogue and slide audio."""
    await use_case.execute(project_id, slide_id)
    return {"code": status.HTTP_200_OK, "message": "幻灯片音频生成成功", "data": None}


@router.post("/projects/{project_id}/audio/batch-generate", status_code=status.HTTP_202_ACCEPTED)
async def batch_generate_audio(
    project_id: str,
    use_case: QueueBatchAudioGenerationUseCaseDep,
) -> dict[str, object]:
    """Queue audio generation for all slides."""
    task_id = await use_case.execute(project_id)
    return {
        "code": status.HTTP_202_ACCEPTED,
        "message": "批量生成音频任务已创建",
        "data": {"task_id": task_id, "project_id": project_id},
    }


@router.get("/projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}/audio/file")
async def get_dialogue_audio_file(
    project_id: str,
    slide_id: str,
    dialogue_id: str,
    service: DialogueResourceServiceDep,
    asset_store: AssetStoreDep,
) -> FileResponse:
    """Return a generated dialogue audio file."""
    path = asset_store.resolve_file(await service.get_audio_path(project_id, slide_id, dialogue_id))
    return FileResponse(path=path, media_type="audio/mpeg", filename=f"{dialogue_id}.mp3")


@router.get("/projects/{project_id}/slides/{slide_id}/audio/file")
async def get_slide_audio_file(
    project_id: str,
    slide_id: str,
    service: SlideResourceServiceDep,
    asset_store: AssetStoreDep,
) -> FileResponse:
    """Return generated slide audio."""
    path = asset_store.resolve_file(await service.get_audio_path(project_id, slide_id))
    return FileResponse(path=path, media_type="audio/mpeg", filename=f"{slide_id}.mp3")
