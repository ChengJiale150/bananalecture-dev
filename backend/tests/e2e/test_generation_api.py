import time

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from bananalecture_backend.core.config import Settings


def _create_project(client: TestClient, settings: Settings, name: str = "Physics lesson") -> str:
    response = client.post(f"{settings.API.V1_STR}/projects", json={"name": name})
    assert response.status_code == status.HTTP_201_CREATED
    project_id = response.json()["data"]["id"]
    slide_response = client.post(
        f"{settings.API.V1_STR}/projects/{project_id}/slides",
        json={"slides": [{"type": "content", "title": "Motion", "description": "Topic", "content": "Force"}]},
    )
    assert slide_response.status_code == status.HTTP_201_CREATED
    return project_id


def _wait_for_pipeline_completion(
    client: TestClient,
    settings: Settings,
    project_id: str,
    timeout_seconds: float = 5.0,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(f"{settings.API.V1_STR}/projects/{project_id}/generation")
        if response.status_code == status.HTTP_200_OK:
            data = response.json()["data"]
            if data["status"] in {"completed", "failed", "cancelled"}:
                return data
        time.sleep(0.2)
    response = client.get(f"{settings.API.V1_STR}/projects/{project_id}/generation")
    data = response.json()["data"]
    client.delete(f"{settings.API.V1_STR}/projects/{project_id}/generation")
    pytest.fail(f"pipeline for project {project_id} did not finish in time, last status: {data.get('status')}")


@pytest.mark.e2e
def test_start_generation_creates_session(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)

    response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/generate")

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()["data"]
    assert data["session_id"].startswith("gs-")
    assert data["project_id"] == project_id

    _wait_for_pipeline_completion(client, test_settings, project_id)


@pytest.mark.e2e
def test_get_generation_returns_pipeline_status(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)
    client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/generate")

    pipeline = _wait_for_pipeline_completion(client, test_settings, project_id)

    assert pipeline["status"] == "completed"
    assert len(pipeline["phases"]) == 4
    for phase in pipeline["phases"]:
        assert phase["status"] == "completed"


@pytest.mark.e2e
def test_get_generation_returns_404_when_not_started(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)

    response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/generation")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.e2e
def test_cancel_generation_marks_session_cancelled(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)
    client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/generate")
    time.sleep(0.1)

    response = client.delete(f"{test_settings.API.V1_STR}/projects/{project_id}/generation")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert data["status"] == "cancelled"


@pytest.mark.e2e
def test_pause_and_resume_generation(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)
    client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/generate")
    time.sleep(0.2)

    pause_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/generation/pause")
    assert pause_response.status_code == status.HTTP_200_OK
    assert pause_response.json()["data"]["status"] == "paused"

    resume_response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/generation/resume")
    assert resume_response.status_code == status.HTTP_202_ACCEPTED
    assert resume_response.json()["data"]["status"] == "running"

    pipeline = _wait_for_pipeline_completion(client, test_settings, project_id)
    assert pipeline["status"] == "completed"
