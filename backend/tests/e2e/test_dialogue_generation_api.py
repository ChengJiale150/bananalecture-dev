from pathlib import Path

from fastapi import status
from fastapi.testclient import TestClient

from bananalecture_backend.api.v1 import deps
from bananalecture_backend.application.ports import AudioTemplateClients, DialogueTemplateClients
from bananalecture_backend.application.strategies import DefaultDialoguePromptStrategy
from bananalecture_backend.core.config import Settings
from bananalecture_backend.core.templates import DEFAULT_TEMPLATE_ID, TemplateConfig, get_template_config
from bananalecture_backend.infrastructure.storage_layout import StorageLayout
from bananalecture_backend.main import create_app
from tests.conftest import FakeDialogueGenerationClient


class RecordingTemplateClientResolver:
    """Resolver double recording the templates it is asked to resolve."""

    def __init__(self) -> None:
        self.seen_templates: list[TemplateConfig | None] = []
        self.dialogue_generator = FakeDialogueGenerationClient()
        default_config = get_template_config(DEFAULT_TEMPLATE_ID)
        assert default_config is not None
        self.prompt_strategy = DefaultDialoguePromptStrategy(default_config.cue_config)

    def resolve_dialogue_clients(self, template: TemplateConfig | None) -> DialogueTemplateClients:
        self.seen_templates.append(template)
        return DialogueTemplateClients(
            dialogue_generator=self.dialogue_generator,
            prompt_strategy=self.prompt_strategy,
        )

    def resolve_audio_clients(self, template: TemplateConfig | None) -> AudioTemplateClients:
        raise AssertionError("audio resolution is not used by dialogue generation")


def test_dialogue_generation_uses_previous_slide_context(
    client: TestClient,
    test_settings: Settings,
    fake_dialogue_client: FakeDialogueGenerationClient,
) -> None:
    project_response = client.post(
        f"{test_settings.API.V1_STR}/projects",
        json={"name": "Physics lesson"},
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
        json={"name": "Physics lesson"},
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
        json={"name": "Physics lesson"},
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


def test_single_slide_dialogue_generation_uses_project_template_clients(test_settings: Settings) -> None:
    resolver = RecordingTemplateClientResolver()
    app = create_app(test_settings)
    app.dependency_overrides[deps.get_template_client_resolver] = lambda: resolver

    with TestClient(app, headers={"X-User-Id": "test-user"}) as client:
        project_response = client.post(
            f"{test_settings.API.V1_STR}/projects",
            json={"name": "Journey to the West", "template_id": "xiyouji"},
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
        slide_id = slides_response.json()["data"]["items"][0]["id"]

        response = client.post(f"{test_settings.API.V1_STR}/projects/{project_id}/slides/{slide_id}/dialogues/generate")
        assert response.status_code == status.HTTP_200_OK

    assert len(resolver.seen_templates) == 1
    seen_template = resolver.seen_templates[0]
    assert seen_template is not None
    assert seen_template.id == "xiyouji"
    assert len(resolver.dialogue_generator.calls) == 1
