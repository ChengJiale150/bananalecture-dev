from fastapi import APIRouter, status

from bananalecture_backend.api.v1.deps import (
    DialogueResourceServiceDep,
    GenerateSlideDialoguesUseCaseDep,
    QueueBatchDialogueGenerationUseCaseDep,
)
from bananalecture_backend.schemas.dialogue import AddDialogueRequest, ReorderDialoguesRequest, UpdateDialogueRequest

router = APIRouter()


@router.post("/projects/{project_id}/slides/{slide_id}/dialogues/generate")
async def generate_dialogues(
    project_id: str,
    slide_id: str,
    use_case: GenerateSlideDialoguesUseCaseDep,
) -> dict[str, object]:
    """Generate dialogues for a slide."""
    dialogues = await use_case.execute(project_id, slide_id)
    return {
        "code": status.HTTP_200_OK,
        "message": "对话生成成功",
        "data": {"slide_id": slide_id, "dialogues": [dialogue.model_dump() for dialogue in dialogues]},
    }


@router.post("/projects/{project_id}/dialogues/batch-generate", status_code=status.HTTP_202_ACCEPTED)
async def batch_generate_dialogues(
    project_id: str,
    use_case: QueueBatchDialogueGenerationUseCaseDep,
) -> dict[str, object]:
    """Create a background task for batch dialogue generation."""
    task_id = await use_case.execute(project_id)
    return {
        "code": status.HTTP_202_ACCEPTED,
        "message": "批量生成对话任务已创建",
        "data": {"task_id": task_id, "project_id": project_id},
    }


@router.get("/projects/{project_id}/slides/{slide_id}/dialogues")
async def list_dialogues(project_id: str, slide_id: str, service: DialogueResourceServiceDep) -> dict[str, object]:
    """List dialogues for a slide."""
    payload = await service.list_dialogues(project_id, slide_id)
    return {"code": status.HTTP_200_OK, "message": "success", "data": payload.model_dump()}


@router.put("/projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}")
async def update_dialogue(
    project_id: str,
    slide_id: str,
    dialogue_id: str,
    request: UpdateDialogueRequest,
    service: DialogueResourceServiceDep,
) -> dict[str, object]:
    """Update a dialogue."""
    dialogue = await service.update_dialogue(project_id, slide_id, dialogue_id, request)
    return {"code": status.HTTP_200_OK, "message": "对话更新成功", "data": dialogue.model_dump()}


@router.delete("/projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}")
async def delete_dialogue(
    project_id: str,
    slide_id: str,
    dialogue_id: str,
    service: DialogueResourceServiceDep,
) -> dict[str, object]:
    """Delete a dialogue."""
    await service.delete_dialogue(project_id, slide_id, dialogue_id)
    return {"code": status.HTTP_200_OK, "message": "对话删除成功", "data": None}


@router.post("/projects/{project_id}/slides/{slide_id}/dialogues/reorder")
async def reorder_dialogues(
    project_id: str,
    slide_id: str,
    request: ReorderDialoguesRequest,
    service: DialogueResourceServiceDep,
) -> dict[str, object]:
    """Reorder dialogues."""
    dialogues = await service.reorder_dialogues(project_id, slide_id, request.dialogue_ids)
    return {
        "code": status.HTTP_200_OK,
        "message": "对话排序更新成功",
        "data": {"dialogues": [dialogue.model_dump() for dialogue in dialogues]},
    }


@router.post("/projects/{project_id}/slides/{slide_id}/dialogues/add", status_code=status.HTTP_201_CREATED)
async def add_dialogue(
    project_id: str,
    slide_id: str,
    request: AddDialogueRequest,
    service: DialogueResourceServiceDep,
) -> dict[str, object]:
    """Add a dialogue."""
    dialogue = await service.add_dialogue(project_id, slide_id, request)
    return {"code": status.HTTP_201_CREATED, "message": "对话添加成功", "data": dialogue.model_dump()}
