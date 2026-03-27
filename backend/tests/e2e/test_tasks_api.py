import time

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from bananalecture_backend.core.config import Settings


def _create_project(client: TestClient, settings: Settings, name: str = "Physics lesson") -> str:
    response = client.post(f"{settings.API.V1_STR}/projects", json={"name": name, "user_id": "admin"})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["data"]["id"]


def _create_slide(client: TestClient, settings: Settings, project_id: str, title: str = "Motion") -> str:
    response = client.post(
        f"{settings.API.V1_STR}/projects/{project_id}/slides",
        json={
            "slides": [
                {
                    "type": "content",
                    "title": title,
                    "description": "Topic",
                    "content": "Force and velocity",
                }
            ]
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["data"]["items"][0]["id"]


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
def test_get_task_returns_task_payload_for_completed_batch_job(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)
    _create_slide(client, test_settings, project_id)

    create_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/dialogues/batch-generate")
    assert create_response.status_code == status.HTTP_202_ACCEPTED
    task_id = create_response.json()["data"]["task_id"]

    task = _wait_for_task_completion(client, test_settings, task_id)

    detail_response = client.get(f"{test_settings.API.V1_STR}/tasks/{task_id}")
    assert detail_response.status_code == status.HTTP_200_OK
    assert detail_response.json() == {
        "code": status.HTTP_200_OK,
        "message": "success",
        "data": task,
    }
    assert task["id"] == task_id
    assert task["project_id"] == project_id
    assert task["type"] == "dialogue_generation"
    assert task["status"] == "completed"
    assert task["current_step"] == task["total_steps"] == 1
    assert task["error_message"] is None
    assert isinstance(task["created_at"], str)
    assert isinstance(task["updated_at"], str)


@pytest.mark.e2e
def test_cancel_task_marks_running_video_task_cancelled(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)
    slide_id = _create_slide(client, test_settings, project_id)

    image_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/image/generate")
    assert image_response.status_code == status.HTTP_200_OK

    audio_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/audio/generate")
    assert audio_response.status_code == status.HTTP_200_OK

    create_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/video/generate")
    assert create_response.status_code == status.HTTP_202_ACCEPTED
    task_id = create_response.json()["data"]["task_id"]

    cancel_response = client.delete(f"{test_settings.API.V1_STR}/tasks/{task_id}")
    assert cancel_response.status_code == status.HTTP_200_OK
    cancelled = cancel_response.json()["data"]
    assert cancel_response.json()["message"] == "任务已取消"
    assert cancelled["id"] == task_id
    assert cancelled["project_id"] == project_id
    assert cancelled["type"] == "video_generation"
    assert cancelled["status"] == "cancelled"
    assert cancelled["current_step"] == 0
    assert cancelled["total_steps"] == 2
    assert cancelled["error_message"] == "Task cancelled"

    refreshed = _wait_for_task_completion(client, test_settings, task_id)
    assert refreshed["status"] == "cancelled"
    assert refreshed["error_message"] == "Task cancelled"


@pytest.mark.e2e
def test_cancel_task_keeps_completed_status_for_terminal_task(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)
    _create_slide(client, test_settings, project_id)

    create_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/images/batch-generate")
    assert create_response.status_code == status.HTTP_202_ACCEPTED
    task_id = create_response.json()["data"]["task_id"]

    completed = _wait_for_task_completion(client, test_settings, task_id)
    assert completed["status"] == "completed"

    cancel_response = client.delete(f"{test_settings.API.V1_STR}/tasks/{task_id}")
    assert cancel_response.status_code == status.HTTP_200_OK
    assert cancel_response.json()["message"] == "任务已取消"
    assert cancel_response.json()["data"] == completed


@pytest.mark.e2e
def test_tasks_api_returns_not_found_for_missing_task(client: TestClient, test_settings: Settings) -> None:
    for method in (client.get, client.delete):
        response = method(f"{test_settings.API.V1_STR}/tasks/missing-task")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {
            "code": status.HTTP_404_NOT_FOUND,
            "message": "Task not found",
            "data": None,
        }
