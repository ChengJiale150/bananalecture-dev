import asyncio

import pytest

from bananalecture_backend.infrastructure.task_runtime import InMemoryBackgroundTaskRunner


@pytest.mark.asyncio
async def test_task_runtime_shutdown_cancels_registered_tasks() -> None:
    runtime = InMemoryBackgroundTaskRunner()
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def worker() -> None:
        started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    runtime.start("task-1", worker())
    await started.wait()

    await runtime.shutdown()

    assert cancelled.is_set()
    assert "task-1" not in runtime._tasks
