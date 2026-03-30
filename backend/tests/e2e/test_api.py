import time

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from bananalecture_backend.core.config import Settings


def _wait_for_task_completion(
    client: TestClient,
    settings: Settings,
    task_id: str,
    timeout_seconds: float = 2.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(f"{settings.API.V1_STR}/tasks/{task_id}")
        assert response.status_code == status.HTTP_200_OK
        task = response.json()["data"]
        if task["status"] in {"completed", "failed", "cancelled"}:
            return task
        time.sleep(0.05)
    pytest.fail(f"task {task_id} did not finish in time")


@pytest.mark.e2e
def test_full_bananalecture_workflow(client: TestClient, test_settings: Settings) -> None:
    """Exercise the main BananaLecture API workflow."""
    project_response = client.post(
        f"{test_settings.API.V1_STR}/projects",
        json={"name": "Physics lesson", "user_id": "admin"},
    )
    assert project_response.status_code == status.HTTP_201_CREATED
    project = project_response.json()["data"]
    project_id = project["id"]

    list_response = client.get(f"{test_settings.API.V1_STR}/admin/projects")
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.json()["data"]["pagination"]["total"] == 1

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
    assert slides_response.status_code == status.HTTP_201_CREATED
    slides = slides_response.json()["data"]["items"]
    first_slide_id = slides[0]["id"]
    second_slide_id = slides[1]["id"]

    reorder_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/reorder",
        json={"slide_ids": [second_slide_id, first_slide_id]},
    )
    assert reorder_response.status_code == status.HTTP_200_OK
    assert reorder_response.json()["data"]["slides"][0]["id"] == second_slide_id

    add_dialogue_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/dialogues/add",
        json={
            "role": "大雄",
            "content": "今天学什么？",
            "emotion": "开心的",
            "speed": "中速",
        },
    )
    assert add_dialogue_response.status_code == status.HTTP_201_CREATED
    dialogue_id = add_dialogue_response.json()["data"]["id"]

    generate_dialogues_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/dialogues/generate"
    )
    assert generate_dialogues_response.status_code == status.HTTP_200_OK
    generated_dialogues = generate_dialogues_response.json()["data"]["dialogues"]
    assert len(generated_dialogues) == 2

    dialogues_response = client.get(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/dialogues"
    )
    assert dialogues_response.status_code == status.HTTP_200_OK
    assert dialogues_response.json()["data"]["total"] == 2

    batch_dialogues_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/dialogues/batch-generate")
    assert batch_dialogues_response.status_code == status.HTTP_202_ACCEPTED
    batch_dialogue_task = batch_dialogues_response.json()["data"]["task_id"]
    task = _wait_for_task_completion(client, test_settings, batch_dialogue_task)
    assert task["status"] == "completed"

    image_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/image/generate"
    )
    assert image_response.status_code == status.HTTP_200_OK

    image_file_response = client.get(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/image/file"
    )
    assert image_file_response.status_code == status.HTTP_200_OK
    assert image_file_response.headers["content-type"] == "image/webp"

    audio_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/audio/generate"
    )
    assert audio_response.status_code == status.HTTP_200_OK

    slide_audio_response = client.get(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/audio/file"
    )
    assert slide_audio_response.status_code == status.HTTP_200_OK
    assert slide_audio_response.headers["content-type"] == "audio/mpeg"

    refreshed_dialogues = client.get(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/dialogues"
    ).json()["data"]["items"]
    first_generated_dialogue_id = refreshed_dialogues[0]["id"]
    dialogue_audio_response = client.get(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/dialogues/{first_generated_dialogue_id}/audio/file"
    )
    assert dialogue_audio_response.status_code == status.HTTP_200_OK
    assert dialogue_audio_response.headers["content-type"] == "audio/mpeg"

    batch_images_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/images/batch-generate")
    assert batch_images_response.status_code == status.HTTP_202_ACCEPTED
    image_task = _wait_for_task_completion(
        client,
        test_settings,
        batch_images_response.json()["data"]["task_id"],
    )
    assert image_task["status"] == "completed"

    batch_audio_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/audio/batch-generate")
    assert batch_audio_response.status_code == status.HTTP_202_ACCEPTED
    audio_task = _wait_for_task_completion(
        client,
        test_settings,
        batch_audio_response.json()["data"]["task_id"],
    )
    assert audio_task["status"] == "completed"

    video_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/video/generate")
    assert video_response.status_code == status.HTTP_202_ACCEPTED
    video_task_id = video_response.json()["data"]["task_id"]

    cancel_response = client.delete(f"{test_settings.API.V1_STR}/tasks/{video_task_id}")
    assert cancel_response.status_code == status.HTTP_200_OK
    cancelled_task_payload = cancel_response.json()["data"]
    assert cancelled_task_payload["id"] == video_task_id
    assert cancelled_task_payload["status"] == "cancelled"
    assert cancelled_task_payload["error_message"] == "Task cancelled"

    cancelled_task = _wait_for_task_completion(client, test_settings, video_task_id)
    assert cancelled_task["status"] == "cancelled"
    assert cancelled_task["error_message"] == "Task cancelled"

    second_video_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/video/generate")
    assert second_video_response.status_code == status.HTTP_202_ACCEPTED
    second_video_task = _wait_for_task_completion(
        client,
        test_settings,
        second_video_response.json()["data"]["task_id"],
    )
    assert second_video_task["status"] == "completed"

    video_file_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/video/file")
    assert video_file_response.status_code == status.HTTP_200_OK
    assert video_file_response.headers["content-type"] == "video/mp4"

    detail_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}")
    assert detail_response.status_code == status.HTTP_200_OK
    detail_payload = detail_response.json()["data"]
    assert len(detail_payload["slides"]) == 2
    assert detail_payload["video_path"] == f"projects/{project_id}/video/project-video.mp4"

    update_project_response = client.put(
        f"{test_settings.API.V1_STR}/projects/{project_id}",
        json={"name": "Physics lesson v2", "messages": "[]"},
    )
    assert update_project_response.status_code == status.HTTP_200_OK
    update_payload = update_project_response.json()["data"]
    assert update_payload["id"] == project_id
    assert update_payload["name"] == "Physics lesson v2"
    assert update_payload["messages"] == "[]"
    assert "updated_at" in update_payload
    assert set(update_payload) == {"id", "name", "messages", "updated_at"}

    delete_dialogue_response = client.delete(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}/dialogues/{dialogue_id}"
    )
    assert delete_dialogue_response.status_code == status.HTTP_404_NOT_FOUND

    delete_project_response = client.delete(f"{test_settings.API.V1_STR}/projects/{project_id}")
    assert delete_project_response.status_code == status.HTTP_200_OK

    missing_project_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}")
    assert missing_project_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.e2e
def test_video_generation_returns_error_when_slide_assets_are_missing(
    client: TestClient,
    test_settings: Settings,
) -> None:
    project_response = client.post(
        f"{test_settings.API.V1_STR}/projects",
        json={"name": "Physics lesson", "user_id": "admin"},
    )
    assert project_response.status_code == status.HTTP_201_CREATED
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
    assert slides_response.status_code == status.HTTP_201_CREATED
    slide_id = slides_response.json()["data"]["items"][0]["id"]

    response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/video/generate")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "code": status.HTTP_400_BAD_REQUEST,
        "message": f"Slide {slide_id} image must be generated before video generation",
        "data": None,
    }
