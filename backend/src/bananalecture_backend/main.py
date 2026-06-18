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
from bananalecture_backend.core.logging_config import get_global_logger, setup_logging
from bananalecture_backend.db.session import DatabaseManager
from bananalecture_backend.infrastructure.storage import StorageService
from bananalecture_backend.infrastructure.task_runtime import InMemoryBackgroundTaskRunner


def create_app(settings_override: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app_settings = settings_override or get_settings()
    setup_logging(app_settings)
    global_logger = get_global_logger()

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
        global_logger.bind(
            version=app_settings.APP.VERSION,
            environment=app_settings.APP.ENVIRONMENT,
        ).info("application_started")
        yield
        global_logger.info("application_shutdown")
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
    async def handle_application_error(request: Request, exc: BananalectureError) -> JSONResponse:
        server_error_threshold = 500
        level = "ERROR" if exc.status_code >= server_error_threshold else "WARNING"
        global_logger.bind(
            method=request.method,
            path=request.url.path,
            status_code=exc.status_code,
            error_message=exc.message,
        ).log(level, "application_error")
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": exc.message, "data": None},
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        server_error_threshold = 500
        if exc.status_code >= server_error_threshold:
            global_logger.bind(
                method=request.method,
                path=request.url.path,
                status_code=exc.status_code,
                error_message=str(exc.detail),
            ).error("http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": str(exc.detail), "data": None},
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        global_logger.bind(
            method=request.method,
            path=request.url.path,
            errors=jsonable_encoder(exc.errors()),
        ).warning("validation_error")
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
