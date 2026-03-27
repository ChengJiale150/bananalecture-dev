from bananalecture_backend.schemas.common import APIModel


class PromptRequest(APIModel):
    """Prompt payload for image operations."""

    prompt: str


class TaskReference(APIModel):
    """Task creation payload."""

    task_id: str
    project_id: str
