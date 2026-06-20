"""Schemas for admin dashboard and management endpoints."""

from datetime import datetime

from bananalecture_backend.schemas.common import APIModel, Pagination


class TaskStats(APIModel):
    """Task status distribution."""

    total: int = 0
    pending: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


class DashboardStats(APIModel):
    """Aggregate dashboard statistics."""

    total_users: int
    total_projects: int
    total_slides: int
    total_dialogues: int
    tasks: TaskStats


class AdminUserItem(APIModel):
    """A single user entry in the admin user list."""

    user_id: str
    project_count: int
    last_active_at: datetime


class AdminUserList(APIModel):
    """Paginated admin user list."""

    items: list[AdminUserItem]
    pagination: Pagination
