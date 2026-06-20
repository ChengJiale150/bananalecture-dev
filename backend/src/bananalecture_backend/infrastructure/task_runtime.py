# ruff: noqa: D102, D107

import asyncio
from collections.abc import Coroutine


class InMemoryBackgroundTaskRunner:
    """In-memory registry for background asyncio tasks with pause/resume support."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._events: dict[str, asyncio.Event] = {}
        self._shutdown_timeout_seconds = 5.0

    def start(self, task_id: str, work: Coroutine[object, object, None]) -> None:
        event = asyncio.Event()
        event.set()
        self._events[task_id] = event
        task = asyncio.create_task(work)
        self._tasks[task_id] = task
        task.add_done_callback(lambda _: self._cleanup(task_id))

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        task.cancel()
        return True

    def pause(self, task_id: str) -> bool:
        event = self._events.get(task_id)
        if event is None:
            return False
        event.clear()
        return True

    def resume(self, task_id: str) -> bool:
        event = self._events.get(task_id)
        if event is None:
            return False
        event.set()
        return True

    async def wait_if_paused(self, task_id: str) -> None:
        event = self._events.get(task_id)
        if event is not None:
            await event.wait()

    def _cleanup(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)
        self._events.pop(task_id, None)

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
        self._tasks.clear()
        self._events.clear()


TaskRuntime = InMemoryBackgroundTaskRunner
