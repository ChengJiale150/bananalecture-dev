# ruff: noqa: C901, D102, D107, EM101, F401, TRY003

from sqlalchemy.ext.asyncio import AsyncSession

from bananalecture_backend.core.errors import NotFoundError
from bananalecture_backend.core.time import utc_now
from bananalecture_backend.db.repositories import GenerationSessionRepository, TaskRepository
from bananalecture_backend.models import GenerationSessionModel
from bananalecture_backend.schemas.generation import (
    PHASES_ORDER,
    GenerationPhase,
    GenerationPhaseState,
    GenerationPhaseTaskState,
    GenerationSessionResponse,
    GenerationSessionStatus,
)
from bananalecture_backend.services.utils import new_id


class GenerationSessionService:
    """Resource operations for generation session records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sessions = GenerationSessionRepository(session)
        self.tasks = TaskRepository(session)

    async def create_session(self, project_id: str) -> GenerationSessionModel:
        timestamp = utc_now()
        session_obj = GenerationSessionModel(
            id=f"gs-{new_id()}",
            project_id=project_id,
            status=GenerationSessionStatus.RUNNING.value,
            current_phase=0,
            current_task_id=None,
            error_message=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        await self.sessions.create(session_obj)
        await self.session.commit()
        return session_obj

    async def get_session(self, session_id: str) -> GenerationSessionModel:
        session_obj = await self.sessions.get(session_id)
        if session_obj is None:
            raise NotFoundError("Generation session not found")
        return session_obj

    async def get_active_by_project(self, project_id: str) -> GenerationSessionModel | None:
        return await self.sessions.get_by_project(project_id)

    async def mark_phase(self, session_id: str, phase: int, task_id: str | None = None) -> None:
        values: dict[str, object] = {
            "current_phase": phase,
            "updated_at": utc_now(),
        }
        if task_id is not None:
            values["current_task_id"] = task_id
        await self._update(session_id, values)

    async def mark_completed(self, session_id: str) -> None:
        await self._update(
            session_id,
            {
                "status": GenerationSessionStatus.COMPLETED.value,
                "updated_at": utc_now(),
            },
        )

    async def mark_failed(self, session_id: str, error_message: str) -> None:
        await self._update(
            session_id,
            {
                "status": GenerationSessionStatus.FAILED.value,
                "error_message": error_message,
                "updated_at": utc_now(),
            },
        )

    async def mark_cancelled(self, session_id: str) -> None:
        await self._update(
            session_id,
            {
                "status": GenerationSessionStatus.CANCELLED.value,
                "error_message": "Pipeline cancelled",
                "updated_at": utc_now(),
            },
        )

    async def mark_paused(self, session_id: str) -> None:
        await self._update(
            session_id,
            {
                "status": GenerationSessionStatus.PAUSED.value,
                "updated_at": utc_now(),
            },
        )

    async def mark_running(self, session_id: str) -> None:
        await self._update(
            session_id,
            {
                "status": GenerationSessionStatus.RUNNING.value,
                "updated_at": utc_now(),
            },
        )

    async def build_response(self, session_id: str) -> GenerationSessionResponse:
        session_obj = await self.get_session(session_id)
        phases: list[GenerationPhaseState] = []
        for idx, phase_enum in enumerate(PHASES_ORDER):
            phase_state = GenerationPhaseState(
                phase=phase_enum.name,
                label=phase_enum.label,
                status="pending",
            )
            if idx < session_obj.current_phase:
                phase_state.status = "completed"
            elif idx == session_obj.current_phase:
                if session_obj.status == GenerationSessionStatus.COMPLETED.value:
                    phase_state.status = "completed"
                elif session_obj.status == GenerationSessionStatus.FAILED.value:
                    phase_state.status = "failed"
                elif session_obj.status == GenerationSessionStatus.CANCELLED.value:
                    phase_state.status = "cancelled"
                elif session_obj.status == GenerationSessionStatus.PAUSED.value:
                    phase_state.status = "paused"
                else:
                    phase_state.status = "running"

                if session_obj.current_task_id:
                    task_model = await self.tasks.get(session_obj.current_task_id)
                    if task_model:
                        phase_state.task = GenerationPhaseTaskState(
                            task_id=task_model.id,
                            status=task_model.status,
                            current_step=task_model.current_step,
                            total_steps=task_model.total_steps,
                            progress=int((task_model.current_step / max(task_model.total_steps, 1)) * 100),
                            error_message=task_model.error_message,
                        )
            elif idx > session_obj.current_phase:
                phase_state.status = "pending"
            else:
                phase_state.status = "completed"

            phases.append(phase_state)

        return GenerationSessionResponse(
            session_id=session_obj.id,
            project_id=session_obj.project_id,
            status=session_obj.status,
            current_phase=session_obj.current_phase,
            phases=phases,
            error_message=session_obj.error_message,
            created_at=session_obj.created_at,
            updated_at=session_obj.updated_at,
        )

    async def _update(self, session_id: str, values: dict[str, object]) -> None:
        session_obj = await self.sessions.get(session_id)
        if session_obj is None:
            raise NotFoundError("Generation session not found")
        await self.sessions.update(session_obj, values)
        await self.session.commit()
