from base64 import b64encode
from io import BytesIO
from pathlib import Path

from fastapi import status
from fastapi.testclient import TestClient
from PIL import Image

from bananalecture_backend.core.config import Settings
from bananalecture_backend.infrastructure.storage_layout import StorageLayout
from tests.conftest import FakeImageGenerationClient


def _create_project_with_slide(client: TestClient, settings: Settings, content: str) -> tuple[str, str]:
    project_response = client.post(
        f"{settings.API.V1_STR}/projects",
        json={"name": "Image test", "user_id": "admin"},
    )
    assert project_response.status_code == status.HTTP_201_CREATED
    project_id = project_response.json()["data"]["id"]

    slides_response = client.post(
        f"{settings.API.V1_STR}/projects/{project_id}/slides",
        json={
            "slides": [
                {
                    "type": "content",
                    "title": "Visual",
                    "description": "desc",
                    "content": content,
                }
            ]
        },
    )
    assert slides_response.status_code == status.HTTP_201_CREATED
    slide_id = slides_response.json()["data"]["items"][0]["id"]
    return project_id, slide_id


def test_generate_image_uses_slide_content(
    client: TestClient,
    test_settings: Settings,
    fake_image_client: FakeImageGenerationClient,
) -> None:
    project_id, slide_id = _create_project_with_slide(client, test_settings, "A lesson about gravity")

    response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/image/generate")
    assert response.status_code == status.HTTP_200_OK

    assert fake_image_client.calls == [{"prompt": "A lesson about gravity", "reference_image": None}]

    detail_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}")
    assert detail_response.status_code == status.HTTP_200_OK
    stored_slide = detail_response.json()["data"]["slides"][0]
    assert stored_slide["image_path"] == StorageLayout.slide_image(project_id, slide_id)

    file_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/image/file")
    assert file_response.status_code == status.HTTP_200_OK
    assert file_response.headers["content-type"] == "image/webp"
    assert 'filename="' in file_response.headers["content-disposition"]
    assert file_response.headers["content-disposition"].endswith(f'{slide_id}.webp"')
    with Image.open(BytesIO(file_response.content)) as image:
        assert image.format == "WEBP"
    assert Path(test_settings.STORAGE.DATA_DIR, *StorageLayout.slide_image(project_id, slide_id).split("/")).exists()
    assert Path(
        test_settings.STORAGE.DATA_DIR,
        *StorageLayout.slide_image_delivery(project_id, slide_id).split("/"),
    ).exists()


def test_modify_image_uses_existing_image_as_data_url(
    client: TestClient,
    test_settings: Settings,
    fake_image_client: FakeImageGenerationClient,
) -> None:
    project_id, slide_id = _create_project_with_slide(client, test_settings, "Original content")

    generate_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/image/generate"
    )
    assert generate_response.status_code == status.HTTP_200_OK
    fake_image_client.calls.clear()

    modify_response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/image/modify",
        json={"prompt": "Add a bright sun"},
    )
    assert modify_response.status_code == status.HTTP_200_OK

    file_response = client.get(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/image/file")
    assert file_response.status_code == status.HTTP_200_OK
    original_image_path = Path(
        test_settings.STORAGE.DATA_DIR,
        *StorageLayout.slide_image(project_id, slide_id).split("/"),
    )
    assert Path(
        test_settings.STORAGE.DATA_DIR,
        *StorageLayout.slide_image_delivery(project_id, slide_id).split("/"),
    ).exists()
    expected_reference = f"data:image/png;base64,{b64encode(original_image_path.read_bytes()).decode('ascii')}"
    assert fake_image_client.calls == [{"prompt": "Add a bright sun", "reference_image": expected_reference}]


def test_modify_image_requires_existing_image(
    client: TestClient,
    test_settings: Settings,
) -> None:
    project_id, slide_id = _create_project_with_slide(client, test_settings, "No image yet")

    response = client.post(
        f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/image/modify",
        json={"prompt": "Change the style"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == "Image not found"
