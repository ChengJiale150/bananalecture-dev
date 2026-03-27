# ruff: noqa: D102, D107

import asyncio
from collections.abc import Coroutine


class InMemoryBackgroundTaskRunner:
    """In-memory registry for background asyncio tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._shutdown_timeout_seconds = 5.0

    def start(self, task_id: str, work: Coroutine[object, object, None]) -> None:
        task = asyncio.create_task(work)
        self._tasks[task_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(task_id, None))

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.cancel()
        return True

    async def shutdown(self) -> None:
        """Cancel and await all registered tasks during application shutdown."""
        tasks = list(self._tasks.values())
        if not tasks:
            return

        for task in tasks:
            task.cancel()

        done, pending = await asyncio.wait(tasks, timeout=self._shutdown_timeout_seconds)
        if done:
            await asyncio.gather(*done, return_exceptions=True)
        for task in pending:
            task.add_done_callback(lambda _: None)


TaskRuntime = InMemoryBackgroundTaskRunner
