from fastapi import APIRouter, status

from bananalecture_backend.api.v1.deps import SettingsDep
from bananalecture_backend.services.health import HealthService

router = APIRouter()


@router.get("/")
async def root() -> dict[str, object]:
    """API root endpoint."""
    return {
        "code": status.HTTP_200_OK,
        "message": "success",
        "data": {"message": "BananaLecture API v1"},
    }


@router.get("/health")
async def health_check(settings: SettingsDep) -> dict[str, object]:
    """Health check endpoint."""
    return {
        "code": status.HTTP_200_OK,
        "message": "success",
        "data": HealthService(settings).get_status(),
    }
