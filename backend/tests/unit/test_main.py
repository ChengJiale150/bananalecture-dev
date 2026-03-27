import pytest
from fastapi import status
from fastapi.testclient import TestClient

from bananalecture_backend.core.config import Settings
from bananalecture_backend.schemas.project import UpdateProjectRequest


@pytest.mark.unit
def test_read_root(client: TestClient, test_settings: Settings) -> None:
    """Test the API root endpoint."""
    response = client.get(f"{test_settings.API.V1_STR}/")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["code"] == status.HTTP_200_OK
    assert body["data"] == {"message": "BananaLecture API v1"}


@pytest.mark.unit
def test_read_health(client: TestClient, test_settings: Settings) -> None:
    """Test the health check endpoint."""
    response = client.get(f"{test_settings.API.V1_STR}/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"] == {"status": "ok", "version": test_settings.APP.VERSION}


@pytest.mark.unit
def test_update_project_requires_payload() -> None:
    """Project update payload must include at least one field."""
    with pytest.raises(ValueError):
        UpdateProjectRequest()
