from fastapi import APIRouter, status

from bananalecture_backend.api.v1.deps import SlideResourceServiceDep
from bananalecture_backend.schemas.slide import (
    CreateSlidesRequest,
    ReorderSlidesRequest,
    SlideCreate,
    UpdateSlideRequest,
)

router = APIRouter()


@router.post("/projects/{project_id}/slides", status_code=status.HTTP_201_CREATED)
async def create_slides(
    project_id: str,
    request: CreateSlidesRequest,
    service: SlideResourceServiceDep,
) -> dict[str, object]:
    """Create or replace project slides."""
    slides = await service.replace_slides(project_id, request)
    return {
        "code": status.HTTP_201_CREATED,
        "message": "幻灯片列表创建成功",
        "data": {"items": [slide.model_dump() for slide in slides]},
    }


@router.get("/projects/{project_id}/slides")
async def list_slides(project_id: str, service: SlideResourceServiceDep) -> dict[str, object]:
    """List slides for a project."""
    slides = await service.list_slides(project_id)
    return {
        "code": status.HTTP_200_OK,
        "message": "success",
        "data": {"items": [slide.model_dump() for slide in slides]},
    }


@router.put("/projects/{project_id}/slides/{slide_id}")
async def update_slide(
    project_id: str,
    slide_id: str,
    request: UpdateSlideRequest,
    service: SlideResourceServiceDep,
) -> dict[str, object]:
    """Update a slide."""
    slide = await service.update_slide(project_id, slide_id, request)
    return {"code": status.HTTP_200_OK, "message": "幻灯片更新成功", "data": slide.model_dump()}


@router.delete("/projects/{project_id}/slides/{slide_id}")
async def delete_slide(project_id: str, slide_id: str, service: SlideResourceServiceDep) -> dict[str, object]:
    """Delete a slide."""
    await service.delete_slide(project_id, slide_id)
    return {"code": status.HTTP_200_OK, "message": "幻灯片删除成功", "data": None}


@router.post("/projects/{project_id}/slides/reorder")
async def reorder_slides(
    project_id: str,
    request: ReorderSlidesRequest,
    service: SlideResourceServiceDep,
) -> dict[str, object]:
    """Reorder slides."""
    slides = await service.reorder_slides(project_id, request.slide_ids)
    return {
        "code": status.HTTP_200_OK,
        "message": "幻灯片排序更新成功",
        "data": {"slides": [slide.model_dump() for slide in slides]},
    }


@router.post("/projects/{project_id}/slides/add", status_code=status.HTTP_201_CREATED)
async def add_slide(project_id: str, request: SlideCreate, service: SlideResourceServiceDep) -> dict[str, object]:
    """Add a slide to the end of the project."""
    slide = await service.add_slide(project_id, request)
    return {"code": status.HTTP_201_CREATED, "message": "幻灯片添加成功", "data": slide.model_dump()}
