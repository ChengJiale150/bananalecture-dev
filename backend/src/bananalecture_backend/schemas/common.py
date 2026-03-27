from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    """Base schema with ORM-style attribute support."""

    model_config = ConfigDict(from_attributes=True)


class Pagination(APIModel):
    """Pagination metadata."""

    page: int
    page_size: int
    total: int
    total_pages: int


class PageQuery(APIModel):
    """Pagination query params."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
