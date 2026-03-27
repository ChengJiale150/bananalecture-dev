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


def _add_dialogue(
    client: TestClient,
    settings: Settings,
    project_id: str,
    slide_id: str,
    *,
    role: str = "旁白",
    content: str = "讲解内容",
    emotion: str = "无明显情感",
    speed: str = "中速",
) -> dict[str, object]:
    response = client.post(
        f"{settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/add",
        json={
            "role": role,
            "content": content,
            "emotion": emotion,
            "speed": speed,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["data"]


@pytest.mark.e2e
def test_dialogues_api_crud_and_reorder_flow(client: TestClient, test_settings: Settings) -> None:
    project_id = _create_project(client, test_settings)
    slide_id = _create_slide(client, test_settings, project_id)

    first = _add_dialogue(client, test_settings, project_id, slide_id, role="大雄", content="第一句", emotion="开心的")
    second = _add_dialogue(client, test_settings, project_id, slide_id, role="哆啦A梦", content="第二句", speed="快速")
    third = _add_dialogue(client, test_settings, project_id, slide_id, content="第三句", speed="慢速")

    assert [first["idx"], second["idx"], third["idx"]] == [1, 2, 3]
    assert first["audio_path"] is None

    list_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues")
    assert list_response.status_code == status.HTTP_200_OK
    listed = list_response.json()["data"]
    assert listed["total"] == 3
    assert [item["id"] for item in listed["items"]] == [first["id"], second["id"], third["id"]]

    update_response = client.put(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/{first['id']}",
        json={
            "role": "哆啦A梦",
            "content": "更新后的第一句",
            "emotion": "惊讶的",
            "speed": "快速",
        },
    )
    assert update_response.status_code == status.HTTP_200_OK
    updated = update_response.json()["data"]
    assert updated["id"] == first["id"]
    assert updated["role"] == "哆啦A梦"
    assert updated["content"] == "更新后的第一句"
    assert updated["emotion"] == "惊讶的"
    assert updated["speed"] == "快速"

    reorder_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/reorder",
        json={"dialogue_ids": [third["id"], first["id"], second["id"]]},
    )
    assert reorder_response.status_code == status.HTTP_200_OK
    assert reorder_response.json()["data"]["dialogues"] == [
        {"id": third["id"], "idx": 1},
        {"id": first["id"], "idx": 2},
        {"id": second["id"], "idx": 3},
    ]

    reordered_list = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues")
    assert reordered_list.status_code == status.HTTP_200_OK
    assert [item["id"] for item in reordered_list.json()["data"]["items"]] == [
        third["id"],
        first["id"],
        second["id"],
    ]

    delete_response = client.delete(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/{first['id']}"
    )
    assert delete_response.status_code == status.HTTP_200_OK
    assert delete_response.json() == {
        "code": status.HTTP_200_OK,
        "message": "对话删除成功",
        "data": None,
    }

    final_list = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues")
    assert final_list.status_code == status.HTTP_200_OK
    final_items = final_list.json()["data"]["items"]
    assert [item["id"] for item in final_items] == [third["id"], second["id"]]
    assert [item["idx"] for item in final_items] == [1, 2]


@pytest.mark.e2e
def test_dialogues_api_returns_errors_for_missing_resources_and_bad_requests(
    client: TestClient,
    test_settings: Settings,
) -> None:
    project_id = _create_project(client, test_settings)
    slide_id = _create_slide(client, test_settings, project_id)
    existing_dialogue = _add_dialogue(client, test_settings, project_id, slide_id)

    for method, path, payload, expected_status, expected_message in (
        (
            "get",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides/{slide_id}/dialogues",
            None,
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "post",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides/{slide_id}/dialogues/add",
            {"content": "Missing"},
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "put",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides/{slide_id}/dialogues/{existing_dialogue['id']}",
            {"content": "Updated"},
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "delete",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides/{slide_id}/dialogues/{existing_dialogue['id']}",
            None,
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "post",
            f"{test_settings.API.V1_STR}/projects/missing-project/slides/{slide_id}/dialogues/reorder",
            {"dialogue_ids": [existing_dialogue["id"]]},
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "get",
            f"{test_settings.API.V1_STR}/projects/{project_id}/slides/missing-slide/dialogues",
            None,
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "post",
            f"{test_settings.API.V1_STR}/projects/{project_id}/slides/missing-slide/dialogues/add",
            {"content": "Missing"},
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "put",
            f"{test_settings.API.V1_STR}/projects/{project_id}/slides/missing-slide/dialogues/{existing_dialogue['id']}",
            {"content": "Updated"},
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "delete",
            f"{test_settings.API.V1_STR}/projects/{project_id}/slides/missing-slide/dialogues/{existing_dialogue['id']}",
            None,
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "post",
            f"{test_settings.API.V1_STR}/projects/{project_id}/slides/missing-slide/dialogues/reorder",
            {"dialogue_ids": [existing_dialogue["id"]]},
            status.HTTP_404_NOT_FOUND,
            "Slide not found",
        ),
        (
            "put",
            f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/missing-dialogue",
            {"content": "Updated"},
            status.HTTP_404_NOT_FOUND,
            "Dialogue not found",
        ),
        (
            "delete",
            f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/missing-dialogue",
            None,
            status.HTTP_404_NOT_FOUND,
            "Dialogue not found",
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
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/reorder",
        json={"dialogue_ids": [existing_dialogue["id"], "missing-dialogue"]},
    )
    assert bad_reorder_response.status_code == status.HTTP_400_BAD_REQUEST
    assert bad_reorder_response.json() == {
        "code": status.HTTP_400_BAD_REQUEST,
        "message": "dialogue_ids must match existing dialogues",
        "data": None,
    }

    invalid_add_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/add",
        json={
            "role": "invalid",
            "content": "Bad role",
            "emotion": "无明显情感",
            "speed": "中速",
        },
    )
    assert invalid_add_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert invalid_add_response.json()["message"] == "Validation error"

    invalid_update_response = client.put(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/{existing_dialogue['id']}",
        json={
            "role": "旁白",
            "content": "Updated",
            "emotion": "invalid",
            "speed": "中速",
        },
    )
    assert invalid_update_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert invalid_update_response.json()["message"] == "Validation error"

    invalid_reorder_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/reorder",
        json={},
    )
    assert invalid_reorder_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert invalid_reorder_response.json()["message"] == "Validation error"
