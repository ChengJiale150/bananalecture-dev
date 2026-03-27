from pathlib import Path

from fastapi import status
from fastapi.testclient import TestClient

from bananalecture_backend.core.config import Settings
from bananalecture_backend.infrastructure.storage_layout import StorageLayout
from tests.conftest import FakeDialogueGenerationClient


def test_dialogue_generation_uses_previous_slide_context(
    client: TestClient,
    test_settings: Settings,
    fake_dialogue_client: FakeDialogueGenerationClient,
) -> None:
    project_response = client.post(
        f"{test_settings.API.V1_STR}/projects",
        json={"name": "Physics lesson", "user_id": "admin"},
    )
    project_id = project_response.json()["data"]["id"]

    slides_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides",
        json={
            "slides": [
                {
                    "type": "cover",
                    "title": "Intro",
                    "description": "Welcome",
                    "content": "Physics basics",
                },
                {
                    "type": "content",
                    "title": "Motion",
                    "description": "Topic",
                    "content": "Force and velocity",
                },
            ]
        },
    )
    slides = slides_response.json()["data"]["items"]
    first_slide_id = slides[0]["id"]
    second_slide_id = slides[1]["id"]

    first_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{first_slide_id}/dialogues/generate"
    )
    assert first_response.status_code == status.HTTP_200_OK

    second_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/dialogues/generate"
    )
    assert second_response.status_code == status.HTTP_200_OK

    assert len(fake_dialogue_client.calls) == 2
    assert "这是首页, 前一页口播稿: 无" in str(fake_dialogue_client.calls[0]["prompt"])
    assert "前一页口播稿:" in str(fake_dialogue_client.calls[1]["prompt"])
    assert "大雄：这一页先让我来开场。" in str(fake_dialogue_client.calls[1]["prompt"])
    assert "哆啦A梦：接着我来解释这一页的重点。" in str(fake_dialogue_client.calls[1]["prompt"])


def test_dialogue_generation_ignores_missing_image_file(
    client: TestClient,
    test_settings: Settings,
    fake_dialogue_client: FakeDialogueGenerationClient,
) -> None:
    project_response = client.post(
        f"{test_settings.API.V1_STR}/projects",
        json={"name": "Physics lesson", "user_id": "admin"},
    )
    project_id = project_response.json()["data"]["id"]

    slides_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides",
        json={
            "slides": [
                {
                    "type": "content",
                    "title": "Motion",
                    "description": "Topic",
                    "content": "Force and velocity",
                }
            ]
        },
    )
    slide_id = slides_response.json()["data"]["items"][0]["id"]

    image_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/image/generate")
    assert image_response.status_code == status.HTTP_200_OK

    image_path = Path(test_settings.STORAGE.DATA_DIR, *StorageLayout.slide_image(project_id, slide_id).split("/"))
    image_path.unlink()

    response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/generate")
    assert response.status_code == status.HTTP_200_OK

    assert len(fake_dialogue_client.calls) == 1
    assert fake_dialogue_client.calls[0]["has_image"] is False


def test_dialogue_generation_passes_image_when_present(
    client: TestClient,
    test_settings: Settings,
    fake_dialogue_client: FakeDialogueGenerationClient,
) -> None:
    project_response = client.post(
        f"{test_settings.API.V1_STR}/projects",
        json={"name": "Physics lesson", "user_id": "admin"},
    )
    project_id = project_response.json()["data"]["id"]

    slides_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides",
        json={
            "slides": [
                {
                    "type": "content",
                    "title": "Motion",
                    "description": "Topic",
                    "content": "Force and velocity",
                }
            ]
        },
    )
    slide_id = slides_response.json()["data"]["items"][0]["id"]

    image_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/image/generate")
    assert image_response.status_code == status.HTTP_200_OK

    response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/generate")
    assert response.status_code == status.HTTP_200_OK

    assert len(fake_dialogue_client.calls) == 1
    assert fake_dialogue_client.calls[0]["has_image"] is True
