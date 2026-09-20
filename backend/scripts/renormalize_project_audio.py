"""Batch re-normalize stored project audio created before loudness normalization.

The pipeline now loudness-normalizes every clip before concatenating slide audio, but
assets generated earlier keep their original, wildly uneven levels (narration, each
character voice and bundled sound effects can differ by 20+ LU). This script repairs
those assets *without* re-running text-to-speech or dialogue generation:

  1. read the ordered dialogue list for every slide from the database,
  2. loudness-normalize each existing dialogue ``audio.mp3`` and slide cue asset,
  3. concatenate them into a fresh ``slide.mp3``,
  4. measure before/after loudness and (with ``--apply``) replace the file.

Safe by default: runs as a dry run, keeps a ``.bak`` copy of every replaced file, and
skips clips already sitting on the target so repeated runs do not stack encode loss.

Run it while no generation task is active, since it rewrites files the API serves.

Examples:
    # report what would change, write nothing
    uv run python scripts/renormalize_project_audio.py

    # rewrite every project's slide audio
    uv run python scripts/renormalize_project_audio.py --apply

    # scope to one project and also fix the per-dialogue preview files
    uv run python scripts/renormalize_project_audio.py --apply \\
        --project-id f76c60b5-fd01-466b-b765-f97473de21cb --update-dialogue-audio

    # match an EBU R128 broadcast target instead of the configured one
    uv run python scripts/renormalize_project_audio.py --apply --target-lufs -23
"""

from __future__ import annotations

import argparse
import asyncio
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select

from bananalecture_backend.application.strategies import DefaultAudioCueStrategy
from bananalecture_backend.core.config import ROOT_DIR, Settings
from bananalecture_backend.core.errors import BananalectureError, NotFoundError
from bananalecture_backend.core.templates import DEFAULT_TEMPLATE_ID, TemplateConfig, get_template_config
from bananalecture_backend.db.repositories import DialogueRepository, SlideRepository
from bananalecture_backend.db.session import DatabaseManager
from bananalecture_backend.infrastructure.audio_processing import AudioProcessingService
from bananalecture_backend.infrastructure.storage import StorageService
from bananalecture_backend.models import ProjectModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

TEMP_DIR_PREFIX = "renormalize-"
DEFAULT_TOLERANCE_LU = 0.5
"""A clip already within this distance of the target is reused instead of re-encoded."""

RESIDUAL_LRA_WARNING_LU = 5.0
"""Merged audio above this loudness range still sounds uneven, so flag it."""

_I_PATTERN = re.compile(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS")
_LRA_PATTERN = re.compile(r"LRA:\s+(-?\d+(?:\.\d+)?)\s+LU")
_TP_PATTERN = re.compile(r"Peak:\s+(-?\d+(?:\.\d+)?)\s+dBFS")


@dataclass(frozen=True)
class Loudness:
    """Measured loudness of one audio file."""

    integrated: float
    lra: float
    true_peak: float

    def describe(self) -> str:
        """Render a compact single-line report."""
        return f"{self.integrated:7.1f} LUFS   LRA {self.lra:5.1f}   TP {self.true_peak:6.1f}"


@dataclass(frozen=True)
class DialogueClip:
    """One stored per-dialogue audio file."""

    dialogue_id: str
    role: str
    audio_key: str


@dataclass(frozen=True)
class SlideJob:
    """Everything needed to rebuild one slide's merged audio."""

    project_id: str
    project_name: str
    project_user_id: str
    slide_id: str
    slide_type: str
    slide_audio_key: str
    cue_assets: tuple[Path, ...]
    clips: tuple[DialogueClip, ...]


@dataclass(frozen=True)
class SlideOutcome:
    """Result of processing one slide."""

    job: SlideJob
    status: str
    detail: str
    before: Loudness | None
    after: Loudness | None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Batch re-normalize stored slide audio without re-running TTS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    parser.add_argument(
        "--project-id",
        action="append",
        default=[],
        metavar="ID",
        help="limit to a project id; repeatable (default: all projects)",
    )
    parser.add_argument("--slide-id", action="append", default=[], metavar="ID", help="limit to a slide id; repeatable")
    parser.add_argument("--target-lufs", type=float, default=None, help="override the configured loudness target")
    parser.add_argument(
        "--update-dialogue-audio",
        action="store_true",
        help="also normalize the per-dialogue preview files (approximate for prop cues)",
    )
    parser.add_argument("--no-backup", dest="backup", action="store_false", help="do not keep .bak copies")
    parser.add_argument(
        "--force",
        action="store_true",
        help=f"re-normalize even clips already within {DEFAULT_TOLERANCE_LU} LU of the target",
    )
    parser.add_argument("--data-dir", default=None, help="override STORAGE.DATA_DIR")
    parser.add_argument("--database-url", default=None, help="override DATABASE.URL")
    parser.add_argument("--verbose", action="store_true", help="keep application log output")
    parser.set_defaults(backup=True)
    return parser.parse_args(argv)


def build_settings(args: argparse.Namespace) -> Settings:
    """Load settings from config.yaml/.env and apply command-line overrides."""
    settings = Settings()
    if args.data_dir:
        storage = settings.STORAGE.model_copy(update={"DATA_DIR": args.data_dir})
        settings = settings.model_copy(update={"STORAGE": storage})
    if args.database_url:
        database = settings.DATABASE.model_copy(update={"URL": args.database_url})
        settings = settings.model_copy(update={"DATABASE": database})
    if args.target_lufs is not None:
        normalization = settings.AUDIO_GENERATION.NORMALIZATION.model_copy(
            update={"TARGET_LUFS": args.target_lufs, "ENABLED": True}
        )
        audio = settings.AUDIO_GENERATION.model_copy(update={"NORMALIZATION": normalization})
        settings = settings.model_copy(update={"AUDIO_GENERATION": audio})
    return settings


def measure_audio(ffmpeg_bin: str, path: Path) -> Loudness | None:
    """Measure integrated loudness, LRA and true peak. Returns ``None`` when unmeasurable."""
    result = subprocess.run(
        [
            ffmpeg_bin,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    integrated = _I_PATTERN.findall(result.stderr)
    lra = _LRA_PATTERN.findall(result.stderr)
    peak = _TP_PATTERN.search(result.stderr)
    if not integrated or peak is None:
        return None
    return Loudness(
        integrated=float(integrated[-1]),
        lra=float(lra[-1]) if lra else 0.0,
        true_peak=float(peak.group(1)),
    )


def build_cue_strategy(template: TemplateConfig) -> DefaultAudioCueStrategy:
    """Build the cue strategy for one template."""
    return DefaultAudioCueStrategy(ROOT_DIR / "assets" / template.assets_dir, template.cue_config)


async def collect_jobs(
    session_factory: async_sessionmaker[AsyncSession],
    project_ids: set[str],
    slide_ids: set[str],
) -> tuple[list[SlideJob], list[str]]:
    """Read the database and build one rebuild plan per slide that has merged audio."""
    jobs: list[SlideJob] = []
    notes: list[str] = []
    template_cache: dict[str, TemplateConfig | None] = {}

    async with session_factory() as session:
        statement = select(ProjectModel).order_by(ProjectModel.created_at.asc())
        if project_ids:
            statement = statement.where(ProjectModel.id.in_(project_ids))
        projects = (await session.execute(statement)).scalars().all()

        for project in projects:
            template_id = project.template_id or DEFAULT_TEMPLATE_ID
            if template_id not in template_cache:
                template_cache[template_id] = get_template_config(template_id)
            template = template_cache[template_id]
            if template is None:
                notes.append(f"project {project.id}: unknown template {template_id!r}, skipping")
                continue
            cue_strategy = build_cue_strategy(template)

            slides = await SlideRepository(session).list_by_project(project.id)
            for slide in slides:
                if slide.audio_path is None:
                    continue
                if slide_ids and slide.id not in slide_ids:
                    continue

                dialogues = await DialogueRepository(session).list_by_slide(slide.id)
                clips = tuple(
                    DialogueClip(dialogue_id=item.id, role=item.role, audio_key=item.audio_path)
                    for item in dialogues
                    if item.audio_path is not None
                )
                if not clips:
                    notes.append(f"slide {slide.id}: merged audio exists but no dialogue audio, skipping")
                    continue

                jobs.append(
                    SlideJob(
                        project_id=project.id,
                        project_name=project.name,
                        project_user_id=project.user_id,
                        slide_id=slide.id,
                        slide_type=slide.type,
                        slide_audio_key=slide.audio_path,
                        cue_assets=tuple(cue_strategy.slide_prefix_assets(slide.type)),
                        clips=clips,
                    )
                )
    return jobs, notes


class Renormalizer:
    """Rebuild slide audio at a consistent loudness using existing dialogue files."""

    def __init__(
        self,
        *,
        settings: Settings,
        storage: StorageService,
        audio: AudioProcessingService,
        ffmpeg_bin: str,
        apply: bool,
        backup: bool,
        force: bool,
        update_dialogue_audio: bool,
        tolerance: float = DEFAULT_TOLERANCE_LU,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.audio = audio
        self.ffmpeg_bin = ffmpeg_bin
        self.apply = apply
        self.backup = backup
        self.force = force
        self.update_dialogue_audio = update_dialogue_audio
        self.tolerance = tolerance
        self.target_lufs = settings.AUDIO_GENERATION.NORMALIZATION.TARGET_LUFS
        self._cue_cache: dict[Path, Path] = {}

    async def process_slide(self, job: SlideJob) -> SlideOutcome:
        """Rebuild one slide's merged audio, isolating failures to that slide."""
        temp_dir = await self.storage.create_temp_dir(TEMP_DIR_PREFIX)
        try:
            slide_audio_path = self._resolve(job.slide_audio_key)
            before = measure_audio(self.ffmpeg_bin, slide_audio_path)

            inputs: list[Path] = []
            for asset in job.cue_assets:
                if not asset.exists():
                    message = f"cue asset is missing: {asset}"
                    raise FileNotFoundError(message)
                inputs.append(await self._normalize_cue(asset, temp_dir))
            for index, clip in enumerate(job.clips, start=1):
                source = self._resolve(clip.audio_key)
                inputs.append(await self._normalize_clip(source, temp_dir, f"dialogue-{index:03d}"))

            staged = temp_dir / "slide.mp3"
            await self.audio.concatenate_mp3_files(inputs, staged)
            after = measure_audio(self.ffmpeg_bin, staged)

            if not self.apply:
                return SlideOutcome(job, "planned", "dry run", before, after)

            if self.update_dialogue_audio:
                for index, clip in enumerate(job.clips, start=1):
                    await self._rewrite_dialogue_audio(clip, temp_dir, index)

            self._backup(slide_audio_path)
            await asyncio.to_thread(shutil.copyfile, staged, slide_audio_path)
            return SlideOutcome(job, "applied", "rewritten", before, after)
        except (BananalectureError, OSError, RuntimeError) as exc:
            return SlideOutcome(job, "failed", str(exc), None, None)
        finally:
            await asyncio.to_thread(shutil.rmtree, temp_dir, ignore_errors=True)

    async def _normalize_cue(self, asset: Path, temp_dir: Path) -> Path:
        """Normalize a shared cue asset once per run and reuse the result."""
        cached = self._cue_cache.get(asset)
        if cached is not None and cached.exists():
            return cached
        normalized = await self._normalize_clip(asset, temp_dir, f"cue-{asset.stem}")
        self._cue_cache[asset] = normalized
        return normalized

    async def _normalize_clip(self, source: Path, temp_dir: Path, tag: str) -> Path:
        """Return a clip on the loudness target, reusing the source when already on it."""
        if not source.exists():
            message = f"audio input is missing: {source}"
            raise FileNotFoundError(message)
        if not self.force:
            current = measure_audio(self.ffmpeg_bin, source)
            if current is not None and abs(current.integrated - self.target_lufs) <= self.tolerance:
                return source
        target = temp_dir / f"{tag}.mp3"
        await self.audio.normalize_loudness(source, target)
        return target

    async def _rewrite_dialogue_audio(self, clip: DialogueClip, temp_dir: Path, index: int) -> None:
        """Normalize one stored per-dialogue preview file in place."""
        source = self._resolve(clip.audio_key)
        normalized = await self._normalize_clip(source, temp_dir, f"dialogue-preview-{index:03d}")
        if normalized == source:
            return
        self._backup(source)
        await asyncio.to_thread(shutil.copyfile, normalized, source)

    def _resolve(self, key: str) -> Path:
        """Resolve a storage key, naming the missing key when it is absent."""
        try:
            return self.storage.resolve_file(key)
        except NotFoundError as exc:
            message = f"stored file is missing: {key}"
            raise FileNotFoundError(message) from exc

    def _backup(self, target: Path) -> None:
        """Copy the pristine original aside once, never overwriting an earlier backup."""
        if not self.backup:
            return
        backup = target.with_name(f"{target.name}.bak")
        if backup.exists():
            return
        shutil.copyfile(target, backup)


def report(outcomes: list[SlideOutcome], notes: list[str], *, apply: bool, target_lufs: float) -> int:
    """Print the per-slide report and return a process exit code."""
    current_project: str | None = None
    for outcome in outcomes:
        job = outcome.job
        if job.project_id != current_project:
            current_project = job.project_id
            print(f"\n== {job.project_user_id} / {job.project_name}  ({job.project_id}) ==")
        cues = f", {len(job.cue_assets)} cue asset(s)" if job.cue_assets else ""
        print(f"  slide {job.slide_id}  [{job.slide_type}]  {len(job.clips)} dialogue clip(s){cues}")

        if outcome.before is not None:
            print(f"    before   {outcome.before.describe()}")
        else:
            print("    before   (unmeasurable)")
        if outcome.after is not None:
            print(f"    after    {outcome.after.describe()}")
        else:
            print("    after    (unmeasurable)")

        if outcome.status == "failed":
            print(f"    FAILED   {outcome.detail}")
            continue

        print(f"    {outcome.status.upper():8s} {outcome.detail}")
        after = outcome.after
        if after is not None and after.lra > RESIDUAL_LRA_WARNING_LU:
            print(f"    WARNING  loudness range still {after.lra:.1f} LU; inspect this slide manually")
        if after is not None and after.integrated > -1.0:
            print(f"    WARNING  integrated loudness {after.integrated:.1f} LUFS looks invalid")

    failed = [item for item in outcomes if item.status == "failed"]
    planned = [item for item in outcomes if item.status == "planned"]
    applied = [item for item in outcomes if item.status == "applied"]

    print("\n" + "-" * 72)
    for note in notes:
        print(f"note: {note}")
    verb = "applied" if apply else "planned"
    print(f"target loudness: {target_lufs:.1f} LUFS")
    print(f"slides: {len(outcomes)} total, {len(applied) if apply else len(planned)} {verb}, {len(failed)} failed")
    if not apply and planned:
        print("dry run: no files were modified. Re-run with --apply to write changes.")
    if applied:
        print("backups written next to each replaced file as *.bak")
    return 1 if failed else 0


async def run(args: argparse.Namespace) -> int:
    """Collect rebuild plans and execute them."""
    settings = build_settings(args)
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        print("error: ffmpeg is not installed or not on PATH", file=sys.stderr)
        return 2

    normalization = settings.AUDIO_GENERATION.NORMALIZATION
    print(f"data dir : {settings.STORAGE.DATA_DIR}")
    print(f"database : {settings.DATABASE.URL}")
    print(f"target   : {normalization.TARGET_LUFS} LUFS / TP {normalization.TARGET_TRUE_PEAK_DBTP} dBTP")
    if not args.apply:
        print("mode     : DRY RUN (pass --apply to write changes)")
    elif args.update_dialogue_audio:
        print("mode     : APPLY (slide audio + per-dialogue preview files)")

    database = DatabaseManager(settings)
    await database.initialize()
    storage = StorageService(settings.STORAGE.DATA_DIR)
    await storage.initialize()
    try:
        jobs, notes = await collect_jobs(
            database.session_factory,
            set(args.project_id),
            set(args.slide_id),
        )
    finally:
        await database.dispose()

    if not jobs:
        print("\nNo slide audio matched. Nothing to do.")
        for note in notes:
            print(f"note: {note}")
        return 0

    print(f"\nFound {len(jobs)} slide(s) with merged audio across {len({job.project_id for job in jobs})} project(s).")

    renormalizer = Renormalizer(
        settings=settings,
        storage=storage,
        audio=AudioProcessingService(settings),
        ffmpeg_bin=ffmpeg_bin,
        apply=args.apply,
        backup=args.backup,
        force=args.force,
        update_dialogue_audio=args.update_dialogue_audio,
    )
    outcomes = [await renormalizer.process_slide(job) for job in jobs]
    return report(outcomes, notes, apply=args.apply, target_lufs=normalization.TARGET_LUFS)


def main() -> int:
    """Entry point."""
    args = parse_args()
    if not args.verbose:
        logger.remove()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
