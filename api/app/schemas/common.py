from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    size: int = Field(default=20, ge=1, le=100, description="Page size (1-100)")

    @property
    def offset(self) -> int:
        """Calculate offset from page and size."""
        return (self.page - 1) * self.size


class SearchParams(BaseModel):
    """Search parameters."""
    q: Optional[str] = Field(default=None, description="Search query")
    sort: str = Field(default="created_at", description="Sort field")
    order: str = Field(default="desc", regex="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    success: bool = True
    message: str = "Data retrieved successfully"
    data: List[T]
    pagination: Dict[str, Any] = Field(..., description="Pagination metadata")

    @classmethod
    def create(
        cls,
        data: List[T],
        total: int,
        page: int,
        size: int,
        message: str = "Data retrieved successfully"
    ) -> "PaginatedResponse[T]":
        """Create paginated response."""
        total_pages = (total + size - 1) // size

        return cls(
            data=data,
            message=message,
            pagination={
                "total": total,
                "page": page,
                "size": size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        )


class SuccessResponse(BaseModel, Generic[T]):
    """Success response wrapper."""
    success: bool = True
    message: str = "Operation successful"
    data: T


class ErrorResponse(BaseModel):
    """Error response wrapper."""
    success: bool = False
    error: Dict[str, Any] = Field(..., description="Error details")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status")
    timestamp: float = Field(..., description="Unix timestamp")
    version: str = Field(..., description="Application version")
    services: Dict[str, str] = Field(..., description="Service statuses")


class InfoResponse(BaseModel):
    """Application info response."""
    name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment")
    debug: bool = Field(..., description="Debug mode")
    features: Dict[str, bool] = Field(..., description="Feature flags")


class MetricsResponse(BaseModel):
    """Metrics response."""
    metrics: str = Field(..., description="Prometheus metrics data")


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""
    field: str = Field(..., description="Field name")
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    error: Dict[str, Any] = Field(..., description="Error details")

    @classmethod
    def create(cls, errors: List[ValidationErrorDetail]) -> "ValidationErrorResponse":
        """Create validation error response."""
        return cls(
            error={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"fields": [error.dict() for error in errors]}
            }
        )


class BulkOperationResponse(BaseModel):
    """Bulk operation response."""
    success: bool = True
    message: str = "Bulk operation completed"
    processed: int = Field(..., description="Number of items processed")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")


class ImportExportResponse(BaseModel):
    """Import/Export response."""
    success: bool = True
    message: str = "Operation completed"
    items_count: int = Field(..., description="Number of items")
    file_url: Optional[str] = Field(default=None, description="Export file URL")
    import_id: Optional[str] = Field(default=None, description="Import operation ID")


class StatisticsResponse(BaseModel):
    """Statistics response."""
    success: bool = True
    message: str = "Statistics retrieved"
    data: Dict[str, Any] = Field(..., description="Statistics data")


class ConfigResponse(BaseModel):
    """Configuration response."""
    success: bool = True
    message: str = "Configuration retrieved"
    config: Dict[str, Any] = Field(..., description="Configuration data")


class NotificationResponse(BaseModel):
    """Notification response."""
    success: bool = True
    message: str = "Notification sent"
    notification_id: str = Field(..., description="Notification ID")


class FileUploadResponse(BaseModel):
    """File upload response."""
    success: bool = True
    message: str = "File uploaded successfully"
    file_url: str = Field(..., description="File URL")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="File content type")


class WebSocketMessage(BaseModel):
    """WebSocket message base class."""
    type: str = Field(..., description="Message type")
    timestamp: float = Field(default_factory=lambda: __import__('time').time(), description="Message timestamp")
    data: Dict[str, Any] = Field(default_factory=dict, description="Message data")


class WebSocketError(WebSocketMessage):
    """WebSocket error message."""
    type: str = "error"
    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(default=None, description="Error code")


class WebSocketResponse(WebSocketMessage):
    """WebSocket response message."""
    type: str = "response"
    request_id: Optional[str] = Field(default=None, description="Request ID")
    status: str = Field(default="success", description="Response status")


class BulkRequest(BaseModel):
    """Bulk request base class."""
    items: List[Dict[str, Any]] = Field(..., description="Items to process")
    options: Dict[str, Any] = Field(default_factory=dict, description="Processing options")


class FilterParams(BaseModel):
    """Filter parameters."""
    filters: Dict[str, Any] = Field(default_factory=dict, description="Filter criteria")
    include_inactive: bool = Field(default=False, description="Include inactive items")


class DateRangeParams(BaseModel):
    """Date range parameters."""
    start_date: Optional[str] = Field(default=None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(default=None, description="End date (ISO format)")

    def get_date_range(self) -> tuple:
        """Get parsed date range."""
        from datetime import datetime

        start = None
        end = None

        if self.start_date:
            try:
                start = datetime.fromisoformat(self.start_date.replace('Z', '+00:00'))
            except ValueError:
                pass

        if self.end_date:
            try:
                end = datetime.fromisoformat(self.end_date.replace('Z', '+00:00'))
            except ValueError:
                pass

        return start, end