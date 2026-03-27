# ruff: noqa: D102, D107, EM101, EM102, TRY003, TC001, SLF001, PLR0913

from __future__ import annotations

import asyncio
import shutil
from base64 import b64encode
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image

from bananalecture_backend.application.ports import (
    AssetStore,
    AudioProcessor,
    AudioSynthesizer,
    DialogueGenerator,
    ImageGenerator,
    VideoRenderer,
)
from bananalecture_backend.application.strategies import AudioCueStrategy, DialoguePromptContext, DialoguePromptStrategy
from bananalecture_backend.core.errors import BadRequestError, NotFoundError
from bananalecture_backend.core.time import utc_now
from bananalecture_backend.db.repositories import DialogueRepository, ProjectRepository, SlideRepository
from bananalecture_backend.infrastructure.storage_layout import StorageLayout
from bananalecture_backend.models import DialogueModel, SlideModel
from bananalecture_backend.schemas.dialogue import Dialogue
from bananalecture_backend.schemas.media import PromptRequest
from bananalecture_backend.services.resources import (
    DialogueResourceService,
    ProjectResourceService,
    SlideResourceService,
)
from bananalecture_backend.services.utils import new_id

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from sqlalchemy.ext.asyncio import AsyncSession

    from bananalecture_backend.core.config import Settings


class GenerateSlideImageUseCase:
    """Generate and persist one slide image."""

    def __init__(self, session: AsyncSession, image_generator: ImageGenerator, asset_store: AssetStore) -> None:
        self.session = session
        self.image_generator = image_generator
        self.asset_store = asset_store
        self.slides = SlideRepository(session)
        self.slide_resource = SlideResourceService(session)

    async def execute(self, project_id: str, slide_id: str) -> None:
        slide = await self.slides.get(project_id, slide_id)
        if slide is None:
            raise NotFoundError("Slide not found")
        prompt = slide.content.strip()
        if not prompt:
            raise BadRequestError("Slide content must not be empty")

        image_bytes = await self.image_generator.generate_image(prompt)
        normalized_image = self._normalize_png(image_bytes)
        path = await self.asset_store.write_bytes(StorageLayout.slide_image(project_id, slide_id), normalized_image)
        await self.slide_resource.set_image_path(slide_id, path)
        await self.session.commit()

    def _normalize_png(self, image_bytes: bytes) -> bytes:
        with Image.open(BytesIO(image_bytes)) as image:
            output = BytesIO()
            image.save(output, format="PNG")
        return output.getvalue()


class ModifySlideImageUseCase:
    """Modify an existing slide image from a prompt."""

    def __init__(self, session: AsyncSession, image_generator: ImageGenerator, asset_store: AssetStore) -> None:
        self.session = session
        self.image_generator = image_generator
        self.asset_store = asset_store
        self.slides = SlideRepository(session)
        self.slide_resource = SlideResourceService(session)

    async def execute(self, project_id: str, slide_id: str, request: PromptRequest) -> None:
        prompt_text = request.prompt.strip()
        if not prompt_text:
            raise BadRequestError("Prompt must not be empty")

        slide = await self.slides.get(project_id, slide_id)
        if slide is None:
            raise NotFoundError("Slide not found")
        if slide.image_path is None:
            raise NotFoundError("Image not found")

        current_image = await self.asset_store.read_bytes(slide.image_path)
        reference_image = self._as_data_url(current_image)
        image_bytes = await self.image_generator.generate_image(prompt_text, reference_image)
        normalized_image = GenerateSlideImageUseCase(
            self.session,
            self.image_generator,
            self.asset_store,
        )._normalize_png(image_bytes)
        path = await self.asset_store.write_bytes(StorageLayout.slide_image(project_id, slide_id), normalized_image)
        await self.slide_resource.set_image_path(slide_id, path)
        await self.session.commit()

    def _as_data_url(self, image_bytes: bytes) -> str:
        encoded = b64encode(image_bytes).decode("ascii")
        return f"data:image/png;base64,{encoded}"


class GenerateSlideDialoguesUseCase:
    """Generate and persist one slide's dialogue list."""

    def __init__(
        self,
        session: AsyncSession,
        dialogue_generator: DialogueGenerator,
        prompt_strategy: DialoguePromptStrategy,
        asset_store: AssetStore | None = None,
    ) -> None:
        self.session = session
        self.dialogue_generator = dialogue_generator
        self.prompt_strategy = prompt_strategy
        self.asset_store = asset_store
        self.slides = SlideRepository(session)
        self.dialogues = DialogueRepository(session)

    async def execute(self, project_id: str, slide_id: str) -> list[Dialogue]:
        slide = await self.slides.get(project_id, slide_id)
        if slide is None:
            raise NotFoundError("Slide not found")

        prompt = await self._build_generation_prompt(project_id, slide)
        image_bytes = await self._read_slide_image(slide.image_path)
        generated = await self.dialogue_generator.generate_dialogues(prompt, image_bytes)
        await self.dialogues.delete_by_slide(slide_id)
        timestamp = utc_now()
        records = [
            DialogueModel(
                id=new_id(),
                slide_id=slide_id,
                role=item.role.value,
                content=item.content,
                emotion=item.emotion.value,
                speed=item.speed.value,
                idx=index,
                audio_path=None,
                created_at=timestamp,
                updated_at=timestamp,
            )
            for index, item in enumerate(generated, start=1)
        ]
        await self.dialogues.create_many(records)
        await self.session.commit()
        return DialogueResourceService(self.session).to_schema_list(records)

    async def _build_generation_prompt(self, project_id: str, slide: SlideModel) -> str:
        previous_script = await self._get_previous_slide_script(project_id, slide.id)
        return self.prompt_strategy.build(
            DialoguePromptContext(
                slide_type=slide.type,
                title=slide.title,
                description=slide.description,
                content=slide.content,
                previous_script=previous_script,
            )
        )

    async def _get_previous_slide_script(self, project_id: str, slide_id: str) -> str | None:
        slides = await self.slides.list_by_project(project_id)
        current_index = next((index for index, item in enumerate(slides) if item.id == slide_id), None)
        if current_index is None or current_index == 0:
            return None

        previous_slide = slides[current_index - 1]
        previous_dialogues = await self.dialogues.list_by_slide(previous_slide.id)
        if not previous_dialogues:
            return None
        return "\n".join(f"{dialogue.role}：{dialogue.content}" for dialogue in previous_dialogues)  # noqa: RUF001

    async def _read_slide_image(self, image_path: str | None) -> bytes | None:
        if self.asset_store is None or image_path is None:
            return None
        try:
            return await self.asset_store.read_bytes(image_path)
        except NotFoundError:
            return None


class GenerateSlideAudioUseCase:
    """Generate dialogue audio files and one merged slide audio."""

    def __init__(
        self,
        session: AsyncSession,
        asset_store: AssetStore,
        audio_synthesizer: AudioSynthesizer,
        audio_processor: AudioProcessor,
        dialogue_generator: DialogueGenerator,
        prompt_strategy: DialoguePromptStrategy,
        audio_cue_strategy: AudioCueStrategy,
        settings: Settings,
    ) -> None:
        self.session = session
        self.asset_store = asset_store
        self.audio_synthesizer = audio_synthesizer
        self.audio_processor = audio_processor
        self.dialogue_generator = dialogue_generator
        self.prompt_strategy = prompt_strategy
        self.audio_cue_strategy = audio_cue_strategy
        self.settings = settings
        self.slides = SlideRepository(session)
        self.dialogues = DialogueRepository(session)
        self.dialogue_resource = DialogueResourceService(session)
        self.slide_resource = SlideResourceService(session)

    async def execute(self, project_id: str, slide_id: str) -> None:
        slide = await self.slides.get(project_id, slide_id)
        if slide is None:
            raise NotFoundError("Slide not found")
        dialogues = await self.dialogues.list_by_slide(slide_id)
        if not dialogues:
            await GenerateSlideDialoguesUseCase(
                self.session,
                self.dialogue_generator,
                self.prompt_strategy,
                self.asset_store,
            ).execute(project_id, slide_id)
            dialogues = await self.dialogues.list_by_slide(slide_id)
        if not dialogues:
            raise BadRequestError("Slide dialogues must not be empty")

        dialogue_paths: list[Path] = []
        temp_files: list[Path] = []
        try:
            for dialogue in dialogues:
                audio_bytes = await self.audio_synthesizer.generate_audio(
                    text=dialogue.content,
                    role=dialogue.role,
                    emotion=dialogue.emotion,
                    speed=dialogue.speed,
                )
                dialogue_relative_path = StorageLayout.dialogue_audio(project_id, slide_id, dialogue.id)
                dialogue_output_path = await self.asset_store.prepare_output_file(dialogue_relative_path)

                prefix_assets = self.audio_cue_strategy.dialogue_prefix_assets(dialogue.role)
                if prefix_assets:
                    raw_relative_path = StorageLayout.dialogue_raw_audio(project_id, slide_id, dialogue.id)
                    await self.asset_store.write_bytes(raw_relative_path, audio_bytes)
                    raw_path = self.asset_store.resolve_file(raw_relative_path)
                    temp_files.append(raw_path)
                    await self.audio_processor.concatenate_mp3_files(
                        [*prefix_assets, raw_path],
                        dialogue_output_path,
                    )
                else:
                    await self.asset_store.write_bytes(dialogue_relative_path, audio_bytes)

                await self.dialogue_resource.set_audio_path(dialogue.id, dialogue_relative_path)
                dialogue_paths.append(dialogue_output_path)

            slide_relative_path = StorageLayout.slide_audio(project_id, slide_id)
            slide_output_path = await self.asset_store.prepare_output_file(slide_relative_path)
            slide_inputs = [*self.audio_cue_strategy.slide_prefix_assets(slide.type), *dialogue_paths]
            await self.audio_processor.concatenate_mp3_files(slide_inputs, slide_output_path)
            await self.slide_resource.set_audio_path(slide_id, slide_relative_path)
            await self.session.commit()
        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    await asyncio.to_thread(temp_file.unlink)


class GenerateProjectVideoUseCase:
    """Generate and persist one project's video output."""

    def __init__(
        self,
        session: AsyncSession,
        asset_store: AssetStore,
        video_renderer: VideoRenderer,
        settings: Settings,
    ) -> None:
        self.session = session
        self.asset_store = asset_store
        self.video_renderer = video_renderer
        self.settings = settings
        self.projects = ProjectRepository(session)
        self.slides = SlideRepository(session)
        self.project_resource = ProjectResourceService(session)

    async def execute(
        self,
        project_id: str,
        on_slide_rendered: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        slide_assets = await self._validate_inputs(project_id)
        # Release the read transaction before the long ffmpeg phase so other
        # requests, such as task cancellation, can update SQLite concurrently.
        await self.session.rollback()
        await asyncio.sleep(self.settings.TASKS.VIDEO_TASK_DELAY_SECONDS)
        output_relative_path = StorageLayout.project_video(project_id, self.settings.VIDEO_GENERATION.OUTPUT_FILENAME)
        output_path = await self.asset_store.prepare_output_file(output_relative_path)
        temp_dir = await self.asset_store.create_temp_dir(self.settings.VIDEO_GENERATION.TEMP_DIR_PREFIX)

        try:
            clip_paths: list[Path] = []
            for index, asset in enumerate(slide_assets, start=1):
                clip_path = temp_dir / f"{index:03d}.mp4"
                await self.video_renderer.render_static_slide_clip(asset.image_path, asset.audio_path, clip_path)
                clip_paths.append(clip_path)
                if on_slide_rendered is not None:
                    await on_slide_rendered(index)

            await self.video_renderer.concatenate_mp4_files(clip_paths, output_path)
        finally:
            await asyncio.to_thread(shutil.rmtree, temp_dir, ignore_errors=True)

        await self.project_resource.set_video_path(project_id, output_relative_path)
        await self.session.commit()

    async def validate_inputs(self, project_id: str) -> int:
        slide_assets = await self._validate_inputs(project_id)
        return len(slide_assets)

    async def _validate_inputs(self, project_id: str) -> list[_VideoSlideAsset]:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundError("Project not found")

        slides = await self.slides.list_by_project(project_id)
        if not slides:
            raise BadRequestError("Project must contain at least one slide")

        assets: list[_VideoSlideAsset] = []
        for slide in slides:
            if slide.image_path is None:
                raise BadRequestError(f"Slide {slide.id} image must be generated before video generation")
            if slide.audio_path is None:
                raise BadRequestError(f"Slide {slide.id} audio must be generated before video generation")

            try:
                image_path = self.asset_store.resolve_file(slide.image_path)
            except NotFoundError as exc:
                raise NotFoundError(f"Slide {slide.id} image file not found") from exc

            try:
                audio_path = self.asset_store.resolve_file(slide.audio_path)
            except NotFoundError as exc:
                raise NotFoundError(f"Slide {slide.id} audio file not found") from exc

            assets.append(_VideoSlideAsset(slide_id=slide.id, image_path=image_path, audio_path=audio_path))

        return assets


class _VideoSlideAsset:
    """Resolved media inputs for one slide video clip."""

    def __init__(self, slide_id: str, image_path: Path, audio_path: Path) -> None:
        self.slide_id = slide_id
        self.image_path = image_path
        self.audio_path = audio_path
