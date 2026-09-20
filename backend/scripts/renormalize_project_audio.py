#!/usr/bin/env python3
"""Standalone migration: rebuild stored slide audio at a consistent loudness.

WHY THIS EXISTS
---------------
Text-to-speech voices, per-utterance emotion and bundled cue assets all render at
different loudness and nothing compensated for it, so a slide's narration and each
character could differ by 20+ LU (measured: narration -22.9, Doraemon -29.1, Nobita
-33.6 LUFS, cover cue -9.6 LUFS with a +3.5 dBTP clipped peak).

The pipeline fix normalizes every clip before concatenating slide audio, but assets
generated earlier keep their original levels. This script repairs them in place by
rebuilding each ``slide.mp3`` from the stored per-dialogue files. Text-to-speech output
is reused as-is, so no LLM or TTS quota is consumed.

It is intentionally a SINGLE FILE with NO third-party imports, because production runs
a prebuilt Docker image and the operator has neither the repository nor the project's
virtualenv. Copy this one file somewhere and run it.

REQUIREMENTS
------------
  * Python 3.8+ (standard library only: argparse, sqlite3, subprocess, ...)
  * ffmpeg on PATH, built with the loudnorm + ebur128 filters and libmp3lame
    (every standard ffmpeg build since 3.1 has all three)
  * Read access to the SQLite database and read/write access to the data directory
  * Enough free space in the data directory for a temporary copy of one slide's audio

Nothing else: no pip install, no project source, no network access, no database driver.

USAGE IN DOCKER PRODUCTION (recommended)
----------------------------------------
Run it inside the backend container, which already has python, ffmpeg and the cue
assets from the image, and sees the data volume at ``/app/data``::

    # locate the service name (compose project prefix may differ)
    docker compose ps

    # copy the script in
    docker cp renormalize_project_audio.py bananalecture-backend-1:/tmp/

    # 1. preflight: verify dependencies and resolved paths, change nothing
    docker compose exec backend python /tmp/renormalize_project_audio.py --check

    # 2. dry run: show before/after loudness for every slide, change nothing
    docker compose exec backend python /tmp/renormalize_project_audio.py

    # 3. apply, keeping a .bak next to every replaced file
    docker compose exec backend python /tmp/renormalize_project_audio.py --apply

Run it while no generation task is active, since it rewrites files the API serves.

USAGE ON A HOST (source checkout or mounted data volume)
--------------------------------------------------------
    python3 scripts/renormalize_project_audio.py --check --data-dir ./data
    python3 scripts/renormalize_project_audio.py --apply --data-dir ./data

When running on the host, the cue assets usually live only inside the image; mount or
copy ``assets/`` and point ``--assets-root`` at it, or pass ``--no-cue-assets`` after
confirming no slide uses a cover cue (see CAVEATS).

CAVEATS
-------
  * Cover slides normally begin with a cue sound effect that is NOT part of any
    dialogue file, so this script re-adds it from ``assets/<template>/<cue>``. If a
    template configures a cue and the file is missing, that slide FAILS instead of
    silently dropping audio. ``--no-cue-assets`` overrides this, accepting the loss.
  * Prop-role cues (e.g. gadgets.mp3) were already concatenated into the stored
    dialogue audio at generation time, so they are deliberately NOT re-added here.
  * ``--update-dialogue-audio`` also rewrites the per-dialogue preview files. For a
    prop-role clip the cue and speech are fused into one file, so only a single shared
    gain can be applied and that clip keeps a small internal imbalance.
  * Re-running is safe and deterministic: every run regenerates from the untouched
    source clips, and an existing ``.bak`` is never overwritten.
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------------------
# Defaults, kept in sync with the application's AudioGenerationSettings.
# --------------------------------------------------------------------------------------

DEFAULT_TARGET_LUFS = -16.0
DEFAULT_TARGET_TRUE_PEAK_DBTP = -1.5
DEFAULT_TARGET_LRA = 11.0
DEFAULT_TOLERANCE_LU = 0.5
DEFAULT_SAMPLE_RATE = 32000
DEFAULT_CHANNELS = 2
DEFAULT_BITRATE = "128k"
DEFAULT_TEMPLATE_ID = "doraemon"

RESIDUAL_LRA_WARNING_LU = 5.0
"""A merged slide above this loudness range still sounds uneven, so flag it."""

# Template id -> cover cue filename. Mirrors core/templates.py, which is unavailable in
# production images that ship no source. Override with --cover-cue if a template changes.
COVER_CUES = {
    "doraemon": "cues.mp3",
    "xiyouji": None,
}

I_PATTERN = re.compile(r"I:\s+(-?\d+(?:\.\d+)?)\s+LUFS")
LRA_PATTERN = re.compile(r"LRA:\s+(-?\d+(?:\.\d+)?)\s+LU")
TP_PATTERN = re.compile(r"Peak:\s+(-?\d+(?:\.\d+)?)\s+dBFS")
MEASUREMENT_PATTERNS = {
    "input_i": re.compile(r'"input_i"\s*:\s*"([^"]+)"'),
    "input_tp": re.compile(r'"input_tp"\s*:\s*"([^"]+)"'),
    "input_lra": re.compile(r'"input_lra"\s*:\s*"([^"]+)"'),
    "input_thresh": re.compile(r'"input_thresh"\s*:\s*"([^"]+)"'),
    "target_offset": re.compile(r'"target_offset"\s*:\s*"([^"]+)"'),
}
CONFIG_VALUE_PATTERNS = {
    "target_lufs": re.compile(r"^\s*TARGET_LUFS:\s*(-?\d+(?:\.\d+)?)\s*$", re.MULTILINE),
    "target_true_peak": re.compile(r"^\s*TARGET_TRUE_PEAK_DBTP:\s*(-?\d+(?:\.\d+)?)\s*$", re.MULTILINE),
    "target_lra": re.compile(r"^\s*TARGET_LRA:\s*(-?\d+(?:\.\d+)?)\s*$", re.MULTILINE),
    "data_dir": re.compile(r"^\s*DATA_DIR:\s*['\"]?([^'\"\n#]+?)['\"]?\s*$", re.MULTILINE),
    "database_url": re.compile(r"^\s*URL:\s*['\"]?(sqlite[^'\"\n#]*?)['\"]?\s*$", re.MULTILINE),
}
SQLITE_URL_PREFIXES = ("sqlite+aiosqlite:///", "sqlite:///", "sqlite+aiosqlite://", "sqlite://")


class MigrationError(Exception):
    """A condition that prevents processing one slide."""


@dataclass(frozen=True)
class Loudness:
    """Measured loudness of one audio file."""

    integrated: float
    lra: float
    true_peak: float

    def describe(self) -> str:
        return "I {0:7.1f} LUFS   LRA {1:5.1f}   TP {2:6.1f}".format(self.integrated, self.lra, self.true_peak)


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
    template_id: str
    slide_id: str
    slide_type: str
    slide_audio_key: str
    cue_expected_name: str | None
    cue_asset: Path | None
    clips: tuple


def configure_stdout() -> None:
    """Force UTF-8 output: minimal containers often run with an ASCII locale."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def run_command(args: list) -> subprocess.CompletedProcess:
    """Run one command, capturing text output."""
    return subprocess.run(args, capture_output=True, text=True, errors="replace", check=False)


def check_ffmpeg(ffmpeg: str) -> list:
    """Return a list of human-readable problems with the ffmpeg build."""
    problems = []
    found = shutil.which(ffmpeg) if not Path(ffmpeg).is_file() else ffmpeg
    if found is None:
        problems.append("ffmpeg was not found on PATH (override with --ffmpeg)")
        return problems

    version = run_command([found, "-version"])
    if version.returncode != 0:
        problems.append("ffmpeg exists but failed to run: {0}".format(version.stderr.strip()[:200]))
        return problems

    filters = run_command([found, "-hide_banner", "-filters"])
    if filters.returncode != 0:
        problems.append("could not list ffmpeg filters; is this a usable build?")
        return problems

    for name in ("loudnorm", "ebur128"):
        if not re.search(r"\b{0}\b".format(name), filters.stdout):
            problems.append("ffmpeg is missing the '{0}' filter".format(name))

    demuxers = run_command([found, "-hide_banner", "-demuxers"])
    if not re.search(r"\bconcat\b", demuxers.stdout):
        problems.append("ffmpeg is missing the 'concat' demuxer")

    encoders = run_command([found, "-hide_banner", "-encoders"])
    if "libmp3lame" not in encoders.stdout:
        problems.append("ffmpeg is missing the 'libmp3lame' mp3 encoder")
    return problems


def load_config_values(config_path: Path | None) -> dict:
    """Best-effort read of the few scalar settings this script needs.

    A full YAML parser is unavailable (standard library only), so only uniquely named
    scalar keys are read. Every value is range-checked before use and command-line
    arguments always win.
    """
    values = {}
    if config_path is None or not config_path.is_file():
        return values
    try:
        text = config_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return values

    for key, pattern in CONFIG_VALUE_PATTERNS.items():
        match = pattern.search(text)
        if match is None:
            continue
        raw = match.group(1).strip()
        if key in ("data_dir", "database_url"):
            values[key] = raw
            continue
        try:
            number = float(raw)
        except ValueError:
            continue
        if not math.isfinite(number):
            continue
        if key == "target_lufs" and not -40.0 <= number <= -5.0:
            continue
        if key == "target_true_peak" and not -6.0 <= number <= 0.0:
            continue
        if key == "target_lra" and not 1.0 <= number <= 30.0:
            continue
        values[key] = number
    return values


def resolve_database_path(explicit: str | None, config_values: dict, data_dir: Path, data_dir_explicit: bool) -> Path:
    """Decide which SQLite file to open.

    Precedence: ``--database`` wins outright, then the configured SQLite URL, then
    ``<data-dir>/data.db``. An explicit ``--data-dir`` skips the configured URL so that
    an unrelated config.yaml in the current directory cannot redirect the database.
    """
    if explicit:
        return Path(explicit).expanduser()
    url = config_values.get("database_url")
    if url and not data_dir_explicit:
        for prefix in SQLITE_URL_PREFIXES:
            if url.startswith(prefix):
                candidate = url[len(prefix) :]
                if candidate:
                    return Path(candidate).expanduser()
    return data_dir / "data.db"


def resolve_assets_root(explicit: str | None) -> Path | None:
    """Locate the directory holding per-template asset folders."""
    if explicit:
        return Path(explicit).expanduser()
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent / "assets",  # source checkout: backend/scripts/.. -> backend/assets
        Path("/app/assets"),  # production image
        Path.cwd() / "assets",
        Path.cwd().parent / "assets",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def measure_slide_audio(ffmpeg: str, path: Path) -> Loudness | None:
    """Measure integrated loudness, LRA and true peak of a whole file."""
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ]
    )
    integrated = I_PATTERN.findall(result.stderr)
    lra = LRA_PATTERN.findall(result.stderr)
    peak = TP_PATTERN.search(result.stderr)
    if not integrated or peak is None:
        return None
    return Loudness(
        integrated=float(integrated[-1]),
        lra=float(lra[-1]) if lra else 0.0,
        true_peak=float(peak.group(1)),
    )


def measure_loudnorm(ffmpeg: str, path: Path, target_lufs: float, target_tp: float, target_lra: float) -> dict | None:
    """Run the loudnorm analysis pass and return its measurements."""
    result = run_command(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "loudnorm=I={0}:TP={1}:LRA={2}:print_format=json".format(target_lufs, target_tp, target_lra),
            "-f",
            "null",
            "-",
        ]
    )
    measurements = {}
    for key, pattern in MEASUREMENT_PATTERNS.items():
        match = pattern.search(result.stderr)
        if match is None:
            return None
        try:
            value = float(match.group(1))
        except ValueError:
            return None
        if not math.isfinite(value):
            return None
        measurements[key] = match.group(1)
    return measurements


def build_loudnorm_filter(measurements: dict, target_lufs: float, target_tp: float, target_lra: float) -> str:
    """Build the second-pass loudnorm filter using the measured values."""
    return (
        "loudnorm=I={0}:TP={1}:LRA={2}:measured_I={3}:measured_TP={4}:measured_LRA={5}"
        ":measured_thresh={6}:offset={7}:linear=true:print_format=summary"
    ).format(
        target_lufs,
        target_tp,
        target_lra,
        measurements["input_i"],
        measurements["input_tp"],
        measurements["input_lra"],
        measurements["input_thresh"],
        measurements["target_offset"],
    )


class AudioTools:
    """ffmpeg operations, with the encoding settings copied from the application."""

    def __init__(
        self,
        ffmpeg: str,
        target_lufs: float,
        target_tp: float,
        target_lra: float,
        sample_rate: int,
        channels: int,
        bitrate: str,
    ) -> None:
        self.ffmpeg = ffmpeg
        self.target_lufs = target_lufs
        self.target_tp = target_tp
        self.target_lra = target_lra
        self.sample_rate = sample_rate
        self.channels = channels
        self.bitrate = bitrate

    def _encode_args(self) -> list:
        return [
            "-c:a",
            "libmp3lame",
            "-b:a",
            self.bitrate,
            "-ac",
            str(self.channels),
            "-ar",
            str(self.sample_rate),
            "-vn",
            "-f",
            "mp3",
        ]

    def normalize(self, source: Path, target: Path) -> None:
        """Two-pass loudness-normalize one file into ``target``."""
        measurements = measure_loudnorm(self.ffmpeg, source, self.target_lufs, self.target_tp, self.target_lra)
        args = [self.ffmpeg, "-y", "-hide_banner", "-nostats", "-i", str(source)]
        if measurements is None:
            # Silence yields no usable measurement; normalizing it would drive the gain
            # to infinity and emit NaN samples, which aborts inside libmp3lame.
            print("      note: {0} is unmeasurable (silent?); re-encoding without gain".format(source.name))
        else:
            args += ["-af", build_loudnorm_filter(measurements, self.target_lufs, self.target_tp, self.target_lra)]
        args += self._encode_args() + [str(target)]

        result = run_command(args)
        if result.returncode != 0 or not target.is_file():
            raise MigrationError("ffmpeg failed to normalize {0}: {1}".format(source, _tail(result.stderr)))

    def concatenate(self, inputs: list, target: Path) -> None:
        """Concatenate mp3 inputs into ``target`` via the concat demuxer."""
        manifest = target.parent / "concat-manifest.txt"
        lines = ["file '{0}'".format(str(item.resolve()).replace("'", "'\\''")) for item in inputs]
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        args = [
            self.ffmpeg,
            "-y",
            "-hide_banner",
            "-nostats",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest),
        ]
        args += self._encode_args() + [str(target)]
        result = run_command(args)
        if result.returncode != 0 or not target.is_file():
            raise MigrationError("ffmpeg failed to concatenate {0}: {1}".format(target.name, _tail(result.stderr)))


def _tail(text: str, limit: int = 300) -> str:
    """Return the last part of a command's error output."""
    stripped = (text or "").strip().splitlines()
    return " / ".join(stripped[-3:])[:limit]


def connect_database(database: Path) -> sqlite3.Connection:
    """Open the application's SQLite database.

    Opened read-write on purpose: the application runs SQLite in WAL mode, and a
    read-only connection cannot create the ``-shm`` file it needs. Only SELECT
    statements are ever issued here.
    """
    if not database.is_file():
        raise MigrationError("database not found: {0}\nPass --database if it lives elsewhere.".format(database))
    try:
        connection = sqlite3.connect(str(database))
    except sqlite3.Error as exc:
        raise MigrationError("cannot open database {0}: {1}".format(database, exc))
    connection.row_factory = sqlite3.Row
    return connection


def collect_jobs(
    connection: sqlite3.Connection, project_ids: set, slide_ids: set, assets_root: Path | None, cover_cues: dict
) -> tuple:
    """Read the database and build one rebuild plan per slide that has merged audio."""
    jobs = []
    notes = []

    columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
    has_template = "template_id" in columns

    project_query = "SELECT id, name, user_id{0} FROM projects ORDER BY created_at".format(
        ", template_id" if has_template else ""
    )
    projects = connection.execute(project_query).fetchall()

    for project in projects:
        if project_ids and project["id"] not in project_ids:
            continue
        template_id = (project["template_id"] if has_template else None) or DEFAULT_TEMPLATE_ID

        cue_name = cover_cues.get(template_id, "__unknown__")
        if cue_name == "__unknown__":
            notes.append(
                "project {0}: unknown template '{1}', assuming no cover cue".format(project["id"], template_id)
            )
            cue_name = None

        slides = connection.execute(
            "SELECT id, type, audio_path FROM slides WHERE project_id = ? ORDER BY idx, created_at",
            (project["id"],),
        ).fetchall()

        for slide in slides:
            if slide["audio_path"] is None:
                continue
            if slide_ids and slide["id"] not in slide_ids:
                continue

            # Only cover slides carry a cue prefix; other slide types concatenate the
            # dialogue audio alone, so a cue must never be added to them.
            cue_expected = cue_name if slide["type"] == "cover" else None
            cue_asset = None
            if cue_expected:
                if assets_root is None:
                    notes.append(
                        "project {0}: assets directory not found, cannot resolve '{1}'".format(
                            project["id"], cue_expected
                        )
                    )
                else:
                    candidate = assets_root / template_id / cue_expected
                    cue_asset = candidate if candidate.is_file() else None

            dialogues = connection.execute(
                "SELECT id, role, audio_path FROM dialogues WHERE slide_id = ? ORDER BY idx, created_at",
                (slide["id"],),
            ).fetchall()
            clips = tuple(
                DialogueClip(dialogue_id=row["id"], role=row["role"], audio_key=row["audio_path"])
                for row in dialogues
                if row["audio_path"]
            )
            if not clips:
                notes.append("slide {0}: merged audio exists but no dialogue audio, skipping".format(slide["id"]))
                continue

            jobs.append(
                SlideJob(
                    project_id=project["id"],
                    project_name=project["name"],
                    project_user_id=project["user_id"],
                    template_id=template_id,
                    slide_id=slide["id"],
                    slide_type=slide["type"],
                    slide_audio_key=slide["audio_path"],
                    cue_expected_name=cue_expected,
                    cue_asset=cue_asset,
                    clips=clips,
                )
            )
    return jobs, notes


class Renormalizer:
    """Rebuild slide audio at a consistent loudness from existing dialogue files."""

    def __init__(self, args: argparse.Namespace, tools: AudioTools, data_dir: Path) -> None:
        self.args = args
        self.tools = tools
        self.data_dir = data_dir
        self._cue_cache = {}

    def _resolve(self, key: str) -> Path:
        """Resolve a storage key to an on-disk path."""
        candidate = self.data_dir / key
        if not candidate.is_file():
            raise MigrationError("stored file is missing: {0}".format(candidate))
        return candidate

    def _make_temp_dir(self) -> Path:
        base = self.data_dir / "_tmp"
        try:
            base.mkdir(parents=True, exist_ok=True)
            return Path(tempfile.mkdtemp(prefix="renormalize-", dir=str(base)))
        except OSError:
            return Path(tempfile.mkdtemp(prefix="renormalize-"))

    def process(self, job: SlideJob) -> tuple:
        """Process one slide, isolating failures to that slide."""
        temp_dir = self._make_temp_dir()
        try:
            slide_audio = self._resolve(job.slide_audio_key)
            before = measure_slide_audio(self.tools.ffmpeg, slide_audio)

            inputs = []
            if job.cue_expected_name and not self.args.no_cue_assets:
                if job.cue_asset is None:
                    raise MigrationError(
                        "cover cue '{0}' for template '{1}' was not found under {2}; "
                        "pass --assets-root or --no-cue-assets".format(
                            job.cue_expected_name, job.template_id, self.args.assets_root or "(auto-detected)"
                        )
                    )
                inputs.append(self._normalize_cue(job.cue_asset, temp_dir))

            for index, clip in enumerate(job.clips, start=1):
                inputs.append(
                    self._normalize_clip(self._resolve(clip.audio_key), temp_dir, "dialogue-{0:03d}".format(index))
                )

            staged = temp_dir / "slide.mp3"
            self.tools.concatenate(inputs, staged)
            after = measure_slide_audio(self.tools.ffmpeg, staged)

            if not self.args.apply:
                return ("planned", "dry run", before, after)

            if self.args.update_dialogue_audio:
                for index, clip in enumerate(job.clips, start=1):
                    self._rewrite_dialogue_audio(clip, temp_dir, index)

            self._backup(slide_audio)
            shutil.copyfile(str(staged), str(slide_audio))
            return ("applied", "rewritten", before, after)
        except MigrationError as exc:
            return ("failed", str(exc), None, None)
        except OSError as exc:
            return ("failed", "filesystem error: {0}".format(exc), None, None)
        finally:
            shutil.rmtree(str(temp_dir), ignore_errors=True)

    def _normalize_cue(self, asset: Path, temp_dir: Path) -> Path:
        """Normalize a shared cue asset once per run and reuse the result."""
        cached = self._cue_cache.get(asset)
        if cached is not None and cached.is_file():
            return cached
        normalized = self._normalize_clip(asset, temp_dir, "cue-{0}".format(asset.stem))
        self._cue_cache[asset] = normalized
        return normalized

    def _normalize_clip(self, source: Path, temp_dir: Path, tag: str) -> Path:
        """Return a clip on the loudness target, reusing the source when already on it."""
        if not self.args.force:
            current = measure_slide_audio(self.tools.ffmpeg, source)
            if current is not None and abs(current.integrated - self.tools.target_lufs) <= self.args.tolerance:
                return source
        target = temp_dir / "{0}.mp3".format(tag)
        self.tools.normalize(source, target)
        return target

    def _rewrite_dialogue_audio(self, clip: DialogueClip, temp_dir: Path, index: int) -> None:
        """Normalize one stored per-dialogue preview file in place."""
        source = self._resolve(clip.audio_key)
        normalized = self._normalize_clip(source, temp_dir, "dialogue-preview-{0:03d}".format(index))
        if normalized == source:
            return
        self._backup(source)
        shutil.copyfile(str(normalized), str(source))

    def _backup(self, target: Path) -> None:
        """Copy the pristine original aside once, never overwriting an earlier backup."""
        if not self.args.backup:
            return
        backup = target.with_name(target.name + ".bak")
        if backup.exists():
            return
        shutil.copyfile(str(target), str(backup))


def report(outcomes: list, notes: list, args: argparse.Namespace, tools: AudioTools) -> int:
    """Print the per-slide report and return a process exit code."""
    current_project = None
    for status, detail, before, after, job in outcomes:
        if job.project_id != current_project:
            current_project = job.project_id
            print("\n== {0} / {1}  ({2}) ==".format(job.project_user_id, job.project_name, job.project_id))
        cues = ""
        if job.cue_expected_name and not args.no_cue_assets:
            cues = ", cover cue {0}".format(job.cue_expected_name)
        print("  slide {0}  [{1}]  {2} dialogue clip(s){3}".format(job.slide_id, job.slide_type, len(job.clips), cues))
        print("    before   {0}".format(before.describe() if before else "(unmeasurable)"))
        print("    after    {0}".format(after.describe() if after else "(unmeasurable)"))

        if status == "failed":
            print("    FAILED   {0}".format(detail))
            continue
        print("    {0:8s} {1}".format(status.upper(), detail))
        if after is not None and after.lra > RESIDUAL_LRA_WARNING_LU:
            print("    WARNING  loudness range still {0:.1f} LU; inspect this slide manually".format(after.lra))

    failed = [item for item in outcomes if item[0] == "failed"]
    planned = [item for item in outcomes if item[0] == "planned"]
    applied = [item for item in outcomes if item[0] == "applied"]

    print("\n" + "-" * 72)
    for note in notes:
        print("note: {0}".format(note))
    print("target loudness: {0} LUFS / TP {1} dBTP".format(tools.target_lufs, tools.target_tp))
    print(
        "slides: {0} total, {1} {2}, {3} failed".format(
            len(outcomes),
            len(applied) if args.apply else len(planned),
            "applied" if args.apply else "planned",
            len(failed),
        )
    )
    if not args.apply and planned:
        print("dry run: no files were modified. Re-run with --apply to write changes.")
    if applied:
        print("backups written next to each replaced file as *.bak (delete them once verified)")
    return 1 if failed else 0


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild stored slide audio at a consistent loudness (standalone, stdlib only).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    parser.add_argument("--check", action="store_true", help="verify dependencies and resolved paths, then exit")
    parser.add_argument("--data-dir", default=None, help="storage root containing projects/ and the database")
    parser.add_argument("--database", default=None, help="path to the SQLite database (default: <data-dir>/data.db)")
    parser.add_argument("--assets-root", default=None, help="directory holding per-template asset folders")
    parser.add_argument("--config", default=None, help="config.yaml to read target values from (best effort)")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg executable (default: from PATH)")

    parser.add_argument("--target-lufs", type=float, default=None, help="override the loudness target")
    parser.add_argument("--target-true-peak", type=float, default=None, help="override the true-peak ceiling in dBTP")
    parser.add_argument("--target-lra", type=float, default=None, help="override the loudness-range target")
    parser.add_argument(
        "--tolerance", type=float, default=DEFAULT_TOLERANCE_LU, help="reuse clips already this close to target"
    )
    parser.add_argument("--force", action="store_true", help="normalize even clips already on target")
    parser.add_argument("--no-backup", dest="backup", action="store_false", help="do not keep .bak copies")
    parser.add_argument(
        "--no-cue-assets", action="store_true", help="never add cover cue assets (drops them from the mix)"
    )
    parser.add_argument(
        "--update-dialogue-audio", action="store_true", help="also normalize per-dialogue preview files"
    )
    parser.add_argument(
        "--project-id", action="append", default=[], metavar="ID", help="limit to a project id; repeatable"
    )
    parser.add_argument("--slide-id", action="append", default=[], metavar="ID", help="limit to a slide id; repeatable")

    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--channels", type=int, default=DEFAULT_CHANNELS)
    parser.add_argument("--bitrate", default=DEFAULT_BITRATE)
    parser.add_argument(
        "--cover-cue",
        action="append",
        default=[],
        metavar="TEMPLATE=FILE",
        help="declare a cover cue, e.g. doraemon=cues.mp3; use TEMPLATE= to declare none",
    )
    parser.set_defaults(backup=True)
    return parser.parse_args(argv)


def resolve_settings(args: argparse.Namespace) -> tuple:
    """Resolve config file, data dir, database, assets root and loudness targets."""
    config_path = Path(args.config).expanduser() if args.config else None
    if config_path is None:
        for candidate in (Path("/app/config.yaml"), Path.cwd() / "config.yaml"):
            if candidate.is_file():
                config_path = candidate
                break
    config_values = load_config_values(config_path)

    data_dir_explicit = args.data_dir is not None
    raw_data_dir = args.data_dir or config_values.get("data_dir") or "/app/data"
    data_dir = Path(raw_data_dir).expanduser()
    if not data_dir.is_absolute() and not data_dir_explicit and config_path is not None:
        # Anchor a configured relative path to the config file, matching how the
        # application resolves it from its working directory.
        data_dir = config_path.parent / data_dir
    database = resolve_database_path(args.database, config_values, data_dir, data_dir_explicit)
    assets_root = resolve_assets_root(args.assets_root)

    cover_cues = dict(COVER_CUES)
    for override in args.cover_cue:
        template_id, _, filename = override.partition("=")
        cover_cues[template_id.strip()] = filename.strip() or None

    tools = AudioTools(
        ffmpeg=args.ffmpeg,
        target_lufs=args.target_lufs
        if args.target_lufs is not None
        else config_values.get("target_lufs", DEFAULT_TARGET_LUFS),
        target_tp=(
            args.target_true_peak
            if args.target_true_peak is not None
            else config_values.get("target_true_peak", DEFAULT_TARGET_TRUE_PEAK_DBTP)
        ),
        target_lra=args.target_lra
        if args.target_lra is not None
        else config_values.get("target_lra", DEFAULT_TARGET_LRA),
        sample_rate=args.sample_rate,
        channels=args.channels,
        bitrate=args.bitrate,
    )
    return config_path, data_dir, database, assets_root, cover_cues, tools


def main(argv: list = None) -> int:
    configure_stdout()
    args = parse_args(argv if argv is not None else sys.argv[1:])
    config_path, data_dir, database, assets_root, cover_cues, tools = resolve_settings(args)

    print("python    : {0}".format(sys.version.split()[0]))
    print("ffmpeg    : {0}".format(shutil.which(args.ffmpeg) or args.ffmpeg))
    print("config    : {0}".format(config_path if config_path else "(none found, using defaults)"))
    print("data dir  : {0}".format(data_dir))
    print("database  : {0}".format(database))
    print("assets    : {0}".format(assets_root if assets_root else "(not found)"))
    print("target    : {0} LUFS / TP {1} dBTP / LRA {2}".format(tools.target_lufs, tools.target_tp, tools.target_lra))

    problems = check_ffmpeg(args.ffmpeg)
    if not data_dir.is_dir():
        problems.append("data directory does not exist: {0}".format(data_dir))
    if not database.is_file():
        problems.append("database does not exist: {0}".format(database))
    if problems:
        print("\npreflight failed:")
        for problem in problems:
            print("  - {0}".format(problem))
        return 2

    if args.check:
        print("\npreflight OK: dependencies and paths look usable. No files were changed.")
        return 0

    if not args.apply:
        print("mode      : DRY RUN (pass --apply to write changes)")
    elif args.update_dialogue_audio:
        print("mode      : APPLY (slide audio + per-dialogue preview files)")

    try:
        connection = connect_database(database)
    except MigrationError as exc:
        print("\nerror: {0}".format(exc))
        return 2

    try:
        jobs, notes = collect_jobs(connection, set(args.project_id), set(args.slide_id), assets_root, cover_cues)
    except sqlite3.Error as exc:
        print("\nerror: failed to read the database schema: {0}".format(exc))
        return 2
    finally:
        connection.close()

    if not jobs:
        print("\nNo slide audio matched. Nothing to do.")
        for note in notes:
            print("note: {0}".format(note))
        return 0

    print(
        "\nFound {0} slide(s) with merged audio across {1} project(s).".format(
            len(jobs), len({job.project_id for job in jobs})
        )
    )

    renormalizer = Renormalizer(args, tools, data_dir)
    outcomes = []
    for job in jobs:
        status, detail, before, after = renormalizer.process(job)
        outcomes.append((status, detail, before, after, job))
    return report(outcomes, notes, args, tools)


if __name__ == "__main__":
    sys.exit(main())
