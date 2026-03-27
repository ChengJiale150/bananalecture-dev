from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from bananalecture_backend.api.v1.router import api_router
from bananalecture_backend.core.config import Settings, get_settings, settings
from bananalecture_backend.core.errors import BananalectureError
from bananalecture_backend.db.session import DatabaseManager
from bananalecture_backend.infrastructure.storage import StorageService
from bananalecture_backend.infrastructure.task_runtime import InMemoryBackgroundTaskRunner


def create_app(settings_override: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app_settings = settings_override or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database = DatabaseManager(app_settings)
        storage = StorageService(app_settings.STORAGE.DATA_DIR)
        task_runtime = InMemoryBackgroundTaskRunner()
        await database.initialize()
        await storage.initialize()
        application.state.settings = app_settings
        application.state.database = database
        application.state.storage = storage
        application.state.task_runtime = task_runtime
        yield
        await task_runtime.shutdown()
        await database.dispose()

    application = FastAPI(
        title=app_settings.APP.NAME,
        version=app_settings.APP.VERSION,
        openapi_url=f"{app_settings.API.V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # Set all CORS enabled origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    application.include_router(api_router, prefix=app_settings.API.V1_STR)

    @application.exception_handler(BananalectureError)
    async def handle_application_error(_: Request, exc: BananalectureError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.message, "data": None},
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": str(exc.detail), "data": None},
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": "Validation error", "data": jsonable_encoder(exc.errors())},
        )

    return application


app = create_app(settings)


def main() -> None:
    """Entry point for the project."""
    uvicorn.run(
        "bananalecture_backend.main:app",
        host=settings.SERVER.HOST,
        port=settings.SERVER.PORT,
        reload=settings.APP.DEBUG,
    )


if __name__ == "__main__":
    main()
