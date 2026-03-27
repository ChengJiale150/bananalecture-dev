from fastapi import APIRouter

from bananalecture_backend.api.v1.endpoints import audio, base, dialogues, image, projects, slides, tasks, video

api_router = APIRouter()
api_router.include_router(base.router, tags=["base"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(slides.router, tags=["slides"])
api_router.include_router(dialogues.router, tags=["dialogues"])
api_router.include_router(image.router, tags=["image"])
api_router.include_router(audio.router, tags=["audio"])
api_router.include_router(video.router, tags=["video"])
api_router.include_router(tasks.router, tags=["tasks"])
