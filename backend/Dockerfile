FROM python:3.12-alpine

RUN apk add --no-cache ffmpeg

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --compile-bytecode

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "bananalecture_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
