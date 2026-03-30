## Project Structure

```
├── src/
│   └── bananalecture_backend/      # Main source package
│       ├── main.py          # Application entry point
│       ├── api/             # API layer (routes, endpoints)
│       ├── application/     # Application layer (ports, use cases)
│       ├── core/            # Core components (config)
│       ├── clients/         # External API / model clients
│       ├── db/              # Database layer
│       ├── infrastructure/  # Storage, runtime, ffmpeg-backed adapters
│       ├── models/          # Database models
│       ├── schemas/         # Pydantic request/response schemas
│       └── services/        # Resource-oriented services
│           └── resources/   # CRUD and local resource rules only
├── tests/                   # Test suite
│   ├── architecture/        # Architectural guardrail tests (pytest-archon)
│   ├── e2e/                 # End-to-end integration tests
│   └── unit/                # Unit tests
├── justfile                 # Task automation commands
└── pyproject.toml           # Project configuration and dependencies
```

## Architecture

- **App Shape**: This is a layered FastAPI monolith. Keep the main flow as `endpoint -> resource service / use case -> repository / port -> model / client / infrastructure`.
- **Resource Services**: `services/resources/` only contains resource-oriented operations and local invariants for `projects`, `slides`, `dialogues`, and task records. They may depend on `db`, `models`, `schemas`, and `core.errors`, but must not depend on `clients`, `infrastructure`, or `application.use_cases`.
- **Application Layer**: `application/use_cases/` owns workflow orchestration such as image generation, dialogue generation, audio generation, video generation, and background task queueing. One use case should represent one explicit application action.
- **Ports**: `application/ports/` defines stable interfaces such as generators, processors, renderers, and asset storage. Use cases depend on these ports instead of calling `build_*` factories directly.
- **Composition Root**: `src/bananalecture_backend/api/v1/deps.py` is the composition root. Concrete implementations from `clients/` and `infrastructure/` must be wired there via FastAPI dependency injection.
- **Startup**: `src/bananalecture_backend/main.py` creates the app and initializes three shared runtime resources during lifespan: database manager, local storage service, and in-memory task runtime.
- **Persistence**: The default database is SQLite via async SQLAlchemy. Generated assets are stored on the local filesystem under `DATA_DIR`.
- **API Surface**: The main REST resources are `projects`, `slides`, `dialogues`, `media`, and `tasks` under `/api/v1`.
- **Task Model**: Background work is intentionally lightweight. Tasks are tracked in the database, but execution is driven by in-process asyncio tasks.

## Code Style

#### FastAPI Best Practices
- **Pydantic Validation**: Use Pydantic models for request/response schemas with automatic data validation
- **Dependency Injection**: Use FastAPI's dependency injection system for shared logic (DB connections, auth, etc.)
- **Async First**: Prefer `async/await`, avoid `run_in_executor` for non-blocking I/O operations
- **Clean Layering**: Router → Resource Service / Use Case → Repository / Port. Keep path operation functions lean and avoid endpoint imports of `clients` or `infrastructure`.
- **Use Cases vs Resources**: CRUD, reorder, and direct resource field updates belong in `services/resources/`. Any operation that invokes external models, ffmpeg, storage orchestration, or task queueing belongs in `application/use_cases/`.
- **Port Discipline**: Do not call `build_*_client` or `build_*_service` outside `api/v1/deps.py`. Tests should prefer fake port implementations or FastAPI dependency overrides over monkeypatching module-level builder functions.
- **Error Handling**: Use `HTTPException` only at the framework boundary when necessary; business exceptions should be raised in resource services or use cases via `core.errors`.

### Type Hinting
-   **Strict Typing**: We use `mypy` in strict mode. All functions and methods must have type annotations.
-   **Modern Syntax**: Use Python 3.10+ syntax (e.g., `str | None` instead of `Optional[str]`, `list[str]` instead of `List[str]`).
-   **Pydantic**: Use Pydantic models for data validation and configuration schemas.

## Development

### Environment
- **Python Management**: We use `uv` to manage the Python environment and dependencies.
- **Run Python**: Use `uv run` to execute Python scripts (NEVER use `python3` or `python`).
- **Add Dependencies**: Use `uv add <package>` to add new dependencies (NEVER directly modify `pyproject.toml`).

### Common Commands
We use `just` as our command runner to provide a consistent development interface:
- `just check`: Run all quality gates (format, lint, type-check, test).

### Workflow
1. **Understand**: Read relevant code to collect associated context to fully understand user instructions, coding styles, and architectural paradigms.
2. **Test First (TDD)**: Write unit tests first to define the expected behavior of new features or modifications. Run `uv run pytest <test_file>` to confirm they fail as expected.
3. **Modify**: Implement the changes or new features following the current layering: resource changes in `services/resources/`, workflow changes in `application/use_cases/`, external integrations behind `application/ports/`.
4. **Verify**: Run `uv run pytest <test_file>` again to ensure the implementation passes the new tests and doesn't break existing ones.
5. **Check**: Run `just check` to ensure overall code quality (format, lint, type-check, test) and catch any regressions.
