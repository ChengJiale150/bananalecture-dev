from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from bananalecture_backend.api.v1.deps import (
    AssetStoreDep,
    GenerateSlideImageUseCaseDep,
    ModifySlideImageUseCaseDep,
    QueueBatchImageGenerationUseCaseDep,
    SlideResourceServiceDep,
)
from bananalecture_backend.schemas.media import PromptRequest

router = APIRouter()


@router.post("/projects/{project_id}/slides/{slide_id}/image/generate")
async def generate_image(
    project_id: str,
    slide_id: str,
    use_case: GenerateSlideImageUseCaseDep,
) -> dict[str, object]:
    """Generate an image for a slide."""
    await use_case.execute(project_id, slide_id)
    return {"code": status.HTTP_200_OK, "message": "图片生成成功", "data": None}


@router.post("/projects/{project_id}/slides/{slide_id}/image/modify")
async def modify_image(
    project_id: str,
    slide_id: str,
    request: PromptRequest,
    use_case: ModifySlideImageUseCaseDep,
) -> dict[str, object]:
    """Modify an image."""
    await use_case.execute(project_id, slide_id, request)
    return {"code": status.HTTP_200_OK, "message": "图片修改成功", "data": None}


@router.post("/projects/{project_id}/images/batch-generate", status_code=status.HTTP_202_ACCEPTED)
async def batch_generate_images(
    project_id: str,
    use_case: QueueBatchImageGenerationUseCaseDep,
) -> dict[str, object]:
    """Queue image generation for all slides."""
    task_id = await use_case.execute(project_id)
    return {
        "code": status.HTTP_202_ACCEPTED,
        "message": "批量生成图片任务已创建",
        "data": {"task_id": task_id, "project_id": project_id},
    }


@router.get("/projects/{project_id}/slides/{slide_id}/image/file")
async def get_image_file(
    project_id: str,
    slide_id: str,
    service: SlideResourceServiceDep,
    asset_store: AssetStoreDep,
) -> FileResponse:
    """Return the generated image file."""
    path = asset_store.resolve_file(await service.get_image_path(project_id, slide_id))
    return FileResponse(path=path, media_type="image/png", filename=f"{slide_id}.png")
