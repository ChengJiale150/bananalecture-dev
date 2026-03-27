import pytest
from fastapi import status
from fastapi.testclient import TestClient

from bananalecture_backend.core.config import Settings


def _create_project(client: TestClient, settings: Settings, name: str, user_id: str | None = None) -> dict[str, object]:
    payload: dict[str, str] = {"name": name}
    if user_id is not None:
        payload["user_id"] = user_id
    response = client.post(f"{settings.API.V1_STR}/projects", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["data"]


@pytest.mark.e2e
def test_project_crud_and_detail_flow(client: TestClient, test_settings: Settings) -> None:
    project = _create_project(client, test_settings, "Physics lesson", "admin")
    project_id = project["id"]

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
                    "title": "Chapter 1",
                    "description": "Topic",
                    "content": "Motion",
                },
            ]
        },
    )
    assert slides_response.status_code == status.HTTP_201_CREATED

    detail_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}")
    assert detail_response.status_code == status.HTTP_200_OK
    detail_payload = detail_response.json()["data"]
    assert detail_payload["id"] == project_id
    assert detail_payload["user_id"] == "admin"
    assert len(detail_payload["slides"]) == 2
    assert [slide["idx"] for slide in detail_payload["slides"]] == [1, 2]

    update_response = client.put(
        f"{test_settings.API.V1_STR}/projects/{project_id}",
        json={"name": "Physics lesson v2", "messages": "[]"},
    )
    assert update_response.status_code == status.HTTP_200_OK
    update_payload = update_response.json()["data"]
    assert update_payload == {
        "id": project_id,
        "name": "Physics lesson v2",
        "messages": "[]",
        "updated_at": update_payload["updated_at"],
    }

    delete_response = client.delete(f"{test_settings.API.V1_STR}/projects/{project_id}")
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json() == {
        "code": status.HTTP_200_OK,
        "message": "项目删除成功",
        "data": None,
    }

    missing_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}")
    assert missing_response.status_code == status.HTTP_404_NOT_FOUND
    assert missing_response.json() == {
        "code": status.HTTP_404_NOT_FOUND,
        "message": "Project not found",
        "data": None,
    }


@pytest.mark.e2e
def test_project_list_supports_default_user_pagination_and_sorting(client: TestClient, test_settings: Settings) -> None:
    default_user_project = _create_project(client, test_settings, "Default user project")
    _create_project(client, test_settings, "Zulu", "admin")
    _create_project(client, test_settings, "Alpha", "admin")
    _create_project(client, test_settings, "Hidden", "other-user")

    default_user_list_response = client.get(f"{test_settings.API.V1_STR}/admin/projects")
    assert default_user_list_response.status_code == status.HTTP_200_OK
    default_user_items = default_user_list_response.json()["data"]["items"]
    assert {item["id"] for item in default_user_items} >= {default_user_project["id"]}

    paged_response = client.get(
        f"{test_settings.API.V1_STR}/admin/projects",
        params={"page": 2, "page_size": 1, "sort_by": "name", "order": "asc"},
    )
    assert paged_response.status_code == status.HTTP_200_OK
    payload = paged_response.json()["data"]
    assert payload["pagination"] == {
        "page": 2,
        "page_size": 1,
        "total": 3,
        "total_pages": 3,
    }
    assert [item["name"] for item in payload["items"]] == ["Default user project"]


@pytest.mark.e2e
def test_project_api_returns_validation_errors_for_bad_requests(client: TestClient, test_settings: Settings) -> None:
    project = _create_project(client, test_settings, "Validation target", "admin")
    project_id = project["id"]

    empty_update_response = client.put(f"{test_settings.API.V1_STR}/projects/{project_id}", json={})
    assert empty_update_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert empty_update_response.json()["code"] == status.HTTP_422_UNPROCESSABLE_CONTENT

    bad_page_response = client.get(f"{test_settings.API.V1_STR}/admin/projects", params={"page": 0})
    assert bad_page_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert bad_page_response.json()["message"] == "Validation error"

    bad_sort_response = client.get(
        f"{test_settings.API.V1_STR}/admin/projects",
        params={"sort_by": "id", "order": "up"},
    )
    assert bad_sort_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert bad_sort_response.json()["message"] == "Validation error"


@pytest.mark.e2e
def test_project_api_returns_not_found_for_missing_resources(client: TestClient, test_settings: Settings) -> None:
    for method, path in (
        ("get", f"{test_settings.API.V1_STR}/projects/missing-project"),
        ("put", f"{test_settings.API.V1_STR}/projects/missing-project"),
        ("delete", f"{test_settings.API.V1_STR}/projects/missing-project"),
    ):
        if method == "put":
            response = client.put(path, json={"name": "Updated"})
        else:
            response = getattr(client, method)(path)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {
            "code": status.HTTP_404_NOT_FOUND,
            "message": "Project not found",
            "data": None,
        }
