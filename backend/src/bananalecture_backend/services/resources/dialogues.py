# ruff: noqa: D102, D107, EM101, TRY003

from sqlalchemy.ext.asyncio import AsyncSession

from bananalecture_backend.core.errors import BadRequestError, NotFoundError
from bananalecture_backend.core.time import utc_now
from bananalecture_backend.db.repositories import DialogueRepository, SlideRepository
from bananalecture_backend.models import DialogueModel
from bananalecture_backend.schemas.dialogue import (
    AddDialogueRequest,
    Dialogue,
    DialogueListData,
    ReorderedDialogue,
    UpdateDialogueRequest,
)
from bananalecture_backend.services.utils import new_id


class DialogueResourceService:
    """Resource operations for dialogue entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.slides = SlideRepository(session)
        self.dialogues = DialogueRepository(session)

    async def list_dialogues(self, project_id: str, slide_id: str) -> DialogueListData:
        await self._ensure_slide(project_id, slide_id)
        items = self.to_schema_list(await self.dialogues.list_by_slide(slide_id))
        return DialogueListData(items=items, total=len(items))

    async def add_dialogue(self, project_id: str, slide_id: str, request: AddDialogueRequest) -> Dialogue:
        await self._ensure_slide(project_id, slide_id)
        existing = await self.dialogues.list_by_slide(slide_id)
        timestamp = utc_now()
        record = DialogueModel(
            id=new_id(),
            slide_id=slide_id,
            role=request.role.value,
            content=request.content,
            emotion=request.emotion.value,
            speed=request.speed.value,
            idx=len(existing) + 1,
            audio_path=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        await self.dialogues.create_one(record)
        await self.session.commit()
        return self._to_schema(record)

    async def update_dialogue(
        self,
        project_id: str,
        slide_id: str,
        dialogue_id: str,
        request: UpdateDialogueRequest,
    ) -> Dialogue:
        await self._ensure_slide(project_id, slide_id)
        dialogue = await self.dialogues.get(slide_id, dialogue_id)
        if dialogue is None:
            raise NotFoundError("Dialogue not found")
        await self.dialogues.update(
            dialogue,
            {
                "role": request.role.value,
                "content": request.content,
                "emotion": request.emotion.value,
                "speed": request.speed.value,
                "updated_at": utc_now(),
            },
        )
        await self.session.commit()
        return self._to_schema(dialogue)

    async def delete_dialogue(self, project_id: str, slide_id: str, dialogue_id: str) -> None:
        await self._ensure_slide(project_id, slide_id)
        dialogue = await self.dialogues.get(slide_id, dialogue_id)
        if dialogue is None:
            raise NotFoundError("Dialogue not found")
        await self.dialogues.delete_one(dialogue)
        await self.session.commit()
        await self._resequence(slide_id)

    async def reorder_dialogues(
        self,
        project_id: str,
        slide_id: str,
        dialogue_ids: list[str],
    ) -> list[ReorderedDialogue]:
        await self._ensure_slide(project_id, slide_id)
        existing = await self.dialogues.list_by_slide(slide_id)
        existing_ids = [dialogue.id for dialogue in existing]
        if sorted(existing_ids) != sorted(dialogue_ids):
            raise BadRequestError("dialogue_ids must match existing dialogues")

        reordered: list[ReorderedDialogue] = []
        for index, dialogue_id in enumerate(dialogue_ids, start=1):
            dialogue = next(dialogue for dialogue in existing if dialogue.id == dialogue_id)
            await self.dialogues.update(dialogue, {"idx": index, "updated_at": utc_now()})
            reordered.append(ReorderedDialogue(id=dialogue_id, idx=index))
        await self.session.commit()
        return reordered

    async def set_audio_path(self, dialogue_id: str, audio_path: str) -> None:
        dialogue = await self._get_dialogue_by_id(dialogue_id)
        await self.dialogues.update(dialogue, {"audio_path": audio_path, "updated_at": utc_now()})

    async def get_audio_path(self, project_id: str, slide_id: str, dialogue_id: str) -> str:
        await self._ensure_slide(project_id, slide_id)
        dialogue = await self.dialogues.get(slide_id, dialogue_id)
        if dialogue is None or dialogue.audio_path is None:
            raise NotFoundError("Audio not found")
        return dialogue.audio_path

    async def _ensure_slide(self, project_id: str, slide_id: str) -> None:
        if await self.slides.get(project_id, slide_id) is None:
            raise NotFoundError("Slide not found")

    async def _get_dialogue_by_id(self, dialogue_id: str) -> DialogueModel:
        dialogue = await self.session.get(DialogueModel, dialogue_id)
        if dialogue is None:
            raise NotFoundError("Dialogue not found")
        return dialogue

    async def _resequence(self, slide_id: str) -> None:
        items = await self.dialogues.list_by_slide(slide_id)
        for index, dialogue in enumerate(items, start=1):
            await self.dialogues.update(dialogue, {"idx": index, "updated_at": utc_now()})
        await self.session.commit()

    def to_schema_list(self, records: list[DialogueModel]) -> list[Dialogue]:
        return [self._to_schema(record) for record in records]

    def _to_schema(self, record: DialogueModel) -> Dialogue:
        return Dialogue.model_validate(
            {
                "id": record.id,
                "slide_id": record.slide_id,
                "role": record.role,
                "content": record.content,
                "emotion": record.emotion,
                "speed": record.speed,
                "idx": record.idx,
                "audio_path": record.audio_path,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
        )
