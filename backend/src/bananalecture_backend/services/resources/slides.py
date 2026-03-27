# ruff: noqa: D102, D107, EM101, TRY003

from sqlalchemy.ext.asyncio import AsyncSession

from bananalecture_backend.core.errors import BadRequestError, NotFoundError
from bananalecture_backend.core.time import utc_now
from bananalecture_backend.db.repositories import DialogueRepository, ProjectRepository, SlideRepository
from bananalecture_backend.models import SlideModel
from bananalecture_backend.schemas.slide import (
    CreateSlidesRequest,
    ReorderedSlide,
    Slide,
    SlideCreate,
    UpdateSlideRequest,
)
from bananalecture_backend.services.utils import new_id


class SlideResourceService:
    """Resource operations for slide entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projects = ProjectRepository(session)
        self.slides = SlideRepository(session)
        self.dialogues = DialogueRepository(session)

    async def replace_slides(self, project_id: str, request: CreateSlidesRequest) -> list[Slide]:
        await self._ensure_project(project_id)
        existing_slides = await self.slides.list_by_project(project_id)
        for slide in existing_slides:
            await self.dialogues.delete_by_slide(slide.id)
        await self.slides.delete_by_project(project_id)

        timestamp = utc_now()
        records = [
            SlideModel(
                id=new_id(),
                project_id=project_id,
                type=slide.type.value,
                title=slide.title,
                description=slide.description,
                content=slide.content,
                idx=index,
                image_path=None,
                audio_path=None,
                created_at=timestamp,
                updated_at=timestamp,
            )
            for index, slide in enumerate(request.slides, start=1)
        ]
        await self.slides.create_many(records)
        await self.session.commit()
        return [Slide.model_validate(record) for record in records]

    async def list_slides(self, project_id: str) -> list[Slide]:
        await self._ensure_project(project_id)
        return [Slide.model_validate(slide) for slide in await self.slides.list_by_project(project_id)]

    async def update_slide(self, project_id: str, slide_id: str, request: UpdateSlideRequest) -> Slide:
        await self._ensure_project(project_id)
        slide = await self._get_slide(project_id, slide_id)
        await self.slides.update(
            slide,
            {
                "type": request.type.value,
                "title": request.title,
                "description": request.description,
                "content": request.content,
                "updated_at": utc_now(),
            },
        )
        await self.session.commit()
        return Slide.model_validate(slide)

    async def delete_slide(self, project_id: str, slide_id: str) -> None:
        await self._ensure_project(project_id)
        slide = await self._get_slide(project_id, slide_id)
        await self.dialogues.delete_by_slide(slide_id)
        await self.slides.delete_one(slide)
        await self.session.commit()
        await self._resequence(project_id)

    async def reorder_slides(self, project_id: str, slide_ids: list[str]) -> list[ReorderedSlide]:
        await self._ensure_project(project_id)
        slides = await self.slides.list_by_project(project_id)
        existing_ids = [slide.id for slide in slides]
        if sorted(existing_ids) != sorted(slide_ids):
            raise BadRequestError("slide_ids must match existing slides")

        updated: list[ReorderedSlide] = []
        for index, slide_id in enumerate(slide_ids, start=1):
            slide = next(slide for slide in slides if slide.id == slide_id)
            await self.slides.update(slide, {"idx": index, "updated_at": utc_now()})
            updated.append(ReorderedSlide(id=slide_id, idx=index))
        await self.session.commit()
        return updated

    async def add_slide(self, project_id: str, request: SlideCreate) -> Slide:
        await self._ensure_project(project_id)
        existing = await self.slides.list_by_project(project_id)
        timestamp = utc_now()
        record = SlideModel(
            id=new_id(),
            project_id=project_id,
            type=request.type.value,
            title=request.title,
            description=request.description,
            content=request.content,
            idx=len(existing) + 1,
            image_path=None,
            audio_path=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        await self.slides.create_one(record)
        await self.session.commit()
        return Slide.model_validate(record)

    async def set_image_path(self, slide_id: str, image_path: str) -> None:
        slide = await self._get_slide_by_id(slide_id)
        await self.slides.update(slide, {"image_path": image_path, "updated_at": utc_now()})

    async def set_audio_path(self, slide_id: str, audio_path: str) -> None:
        slide = await self._get_slide_by_id(slide_id)
        await self.slides.update(slide, {"audio_path": audio_path, "updated_at": utc_now()})

    async def get_image_path(self, project_id: str, slide_id: str) -> str:
        slide = await self._get_slide(project_id, slide_id)
        if slide.image_path is None:
            raise NotFoundError("Image not found")
        return slide.image_path

    async def get_audio_path(self, project_id: str, slide_id: str) -> str:
        slide = await self._get_slide(project_id, slide_id)
        if slide.audio_path is None:
            raise NotFoundError("Audio not found")
        return slide.audio_path

    async def _get_slide(self, project_id: str, slide_id: str) -> SlideModel:
        slide = await self.slides.get(project_id, slide_id)
        if slide is None:
            raise NotFoundError("Slide not found")
        return slide

    async def _get_slide_by_id(self, slide_id: str) -> SlideModel:
        slide = await self.session.get(SlideModel, slide_id)
        if slide is None:
            raise NotFoundError("Slide not found")
        return slide

    async def _ensure_project(self, project_id: str) -> None:
        if await self.projects.get(project_id) is None:
            raise NotFoundError("Project not found")

    async def _resequence(self, project_id: str) -> None:
        slides = await self.slides.list_by_project(project_id)
        for index, slide in enumerate(slides, start=1):
            await self.slides.update(slide, {"idx": index, "updated_at": utc_now()})
        await self.session.commit()
