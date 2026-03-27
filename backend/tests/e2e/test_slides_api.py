from datetime import datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from bananalecture_backend.core.config import Settings


def _create_project(client: TestClient, settings: Settings, name: str = "Physics lesson") -> str:
    response = client.post(f"{settings.API.V1_STR}/projects", json={"name": name, "user_id": "admin"})
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["data"]["id"]


def _create_slides(client: TestClient, settings: Settings, project_id: str) -> list[dict[str, object]]:
    response = client.post(
        f"{settings.API.V1_STR}/projects/{project_id}/slides",
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
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["data"]["items"]


@pytest.mark.e2e
def test_slides_api_crud_reorder_and_add_flow(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)
    created = _create_slides(client, test_settings, project_id)
    first_slide_id = created[0]["id"]
    second_slide_id = created[1]["id"]

    assert [slide["idx"] for slide in created] == [1, 2]
    assert [slide["image_path"] for slide in created] == [None, None]
    assert [slide["audio_path"] for slide in created] == [None, None]

    list_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/slides")
    assert list_response.status_code == status.HTTP_200_OK
    assert [slide["id"] for slide in list_response.json()["data"]["items"]] == [first_slide_id, second_slide_id]

    update_response = client.put(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{first_slide_id}",
        json={
            "type": "summary",
            "title": "Recap",
            "description": "Summary",
            "content": "Key takeaways",
        },
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated_slide = update_response.json()["data"]
    assert updated_slide["id"] == first_slide_id
    assert updated_slide["type"] == "summary"
    assert updated_slide["title"] == "Recap"
    assert datetime.fromisoformat(updated_slide["updated_at"]) >= datetime.fromisoformat(created[0]["updated_at"])

    reorder_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/reorder",
        json={"slide_ids": [second_slide_id, first_slide_id]},
    )
    assert reorder_response.status_code == status.HTTP_200_OK
    assert reorder_response.json()["data"]["slides"] == [
        {"id": second_slide_id, "idx": 1},
        {"id": first_slide_id, "idx": 2},
    ]

    reordered_list_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/slides")
    assert reordered_list_response.status_code == status.HTTP_200_OK
    assert [slide["id"] for slide in reordered_list_response.json()["data"]["items"]] == [
        second_slide_id,
        first_slide_id,
    ]

    add_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/add",
        json={
            "type": "ending",
            "title": "Outro",
            "description": "Goodbye",
            "content": "Thanks",
        },
    )
    assert add_response.status_code == status.HTTP_201_CREATED
    added_slide = add_response.json()["data"]
    assert added_slide["type"] == "ending"
    assert added_slide["idx"] == 3

    delete_response = client.delete(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{second_slide_id}")
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json() == {
        "code": status.HTTP_200_OK,
        "message": "幻灯片删除成功",
        "data": None,
    }

    final_list_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/slides")
    assert final_list_response.status_code == status.HTTP_200_OK
    final_items = final_list_response.json()["data"]["items"]
    assert [slide["id"] for slide in final_items] == [first_slide_id, added_slide["id"]]
    assert [slide["idx"] for slide in final_items] == [1, 2]


@pytest.mark.e2e
def test_slides_api_replace_overwrites_existing_slides(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)
    original = _create_slides(client, test_settings, project_id)

    replace_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides",
        json={
            "slides": [
                {
                    "type": "summary",
                    "title": "Summary",
                    "description": "Wrap up",
                    "content": "Main points",
                }
            ]
        },
    )
    assert replace_response.status_code == status.HTTP_201_CREATED
    replaced_items = replace_response.json()["data"]["items"]
    assert len(replaced_items) == 1
    assert replaced_items[0]["idx"] == 1
    assert replaced_items[0]["id"] not in {slide["id"] for slide in original}

    list_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/slides")
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.json()["data"]["items"] == replaced_items


@pytest.mark.e2e
def test_slides_api_returns_errors_for_missing_resources_and_bad_requests(
    client: TestClient,
    test_settings: Settings,
) -> None:
    project_id = _create_project(client, test_settings)
    slides = _create_slides(client, test_settings, project_id)
    existing_slide_id = slides[0]["id"]

    for method, path, payload, expected_status, expected_message in (
        (
            "get",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides",
            None,
            status.HTTP_404_NOT_FOUND,
            "Project not found",
        ),
        (
            "post",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides",
            {"slides": []},
            status.HTTP_404_NOT_FOUND,
            "Project not found",
        ),
        (
            "post",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides/add",
            {"title": "Only", "description": "Only", "content": "Only"},
            status.HTTP_404_NOT_FOUND,
            "Project not found",
        ),
        (
            "put",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides/{existing_slide_id}",
            {"title": "Updated"},
            status.HTTP_404_NOT_FOUND,
            "Project not found",
        ),
        (
            "delete",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides/{existing_slide_id}",
            None,
            status.HTTP_404_NOT_FOUND,
            "Project not found",
        ),
        (
            "post",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides/reorder",
            {"slide_ids": [existing_slide_id]},
            status.HTTP_404_NOT_FOUND,
            "Project not found",
        ),
        (
            "put",
            f"{test_settings.API.V1_STR}/projects/{project_id}/slides/missing-slide",
            {"title": "Updated"},
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "delete",
            f"{test_settings.API.V1_STR}/projects/{project_id}/slides/missing-slide",
            None,
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
    ):
        if method in {"post", "put"}:
            response = getattr(client, method)(path, json=payload)
        else:
            response = getattr(client, method)(path)
        assert response.status_code == expected_status
        assert response.json() == {
            "code": expected_status,
            "message": expected_message,
            "data": None,
        }

    bad_reorder_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/reorder",
        json={"slide_ids": [existing_slide_id]},
    )
    assert bad_reorder_response.status_code == status.HTTP_400_BAD_REQUEST
    assert bad_reorder_response.json() == {
        "code": status.HTTP_400_BAD_REQUEST,
        "message": "slide_ids must match existing slides",
        "data": None,
    }

    invalid_type_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/add",
        json={"type": "invalid", "title": "Only", "description": "Only", "content": "Only"},
    )
    assert invalid_type_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert invalid_type_response.json()["message"] == "Validation error"

    invalid_reorder_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/reorder",
        json={},
    )
    assert invalid_reorder_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert invalid_reorder_response.json()["message"] == "Validation error"
