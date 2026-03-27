# ruff: noqa: D102

from __future__ import annotations


class StorageLayout:
    """Canonical logical storage keys for persisted project assets."""

    @staticmethod
    def slide_image(project_id: str, slide_id: str) -> str:
        return f"projects/{project_id}/slides/{slide_id}/image/original.png"

    @staticmethod
    def slide_audio(project_id: str, slide_id: str) -> str:
        return f"projects/{project_id}/slides/{slide_id}/audio/slide.mp3"

    @staticmethod
    def dialogue_audio(project_id: str, slide_id: str, dialogue_id: str) -> str:
        return f"projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}/audio.mp3"

    @staticmethod
    def dialogue_raw_audio(project_id: str, slide_id: str, dialogue_id: str) -> str:
        return f"projects/{project_id}/slides/{slide_id}/dialogues/{dialogue_id}/audio.raw.mp3"

    @staticmethod
    def project_video(project_id: str, filename: str) -> str:
        return f"projects/{project_id}/video/{filename}"
