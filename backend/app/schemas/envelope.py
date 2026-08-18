"""Generic response envelope shared by every API route."""

from pydantic import BaseModel, computed_field


class PaginationMeta(BaseModel):
    """Pagination metadata attached to list responses."""

    total: int
    offset: int
    limit: int


class ErrorDetail(BaseModel):
    """Single structured error."""

    field: str | None = None
    code: str
    message: str


class ErrorInfo(BaseModel):
    """Top-level error info for a failed response."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ResponseEnvelope[DataT, MetaT: BaseModel](BaseModel):
    """Standard envelope for API responses."""

    data: DataT | None = None
    error: ErrorInfo | None = None
    meta: MetaT | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def success(self) -> bool:
        return self.error is None
