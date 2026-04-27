from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class TerahResponse(BaseModel):
    """Standard response envelope — used by ALL endpoints, no exceptions."""
    success: bool
    data: Any = None
    message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TerahErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class TerahErrorResponse(BaseModel):
    success: bool = False
    error: TerahErrorDetail
    timestamp: datetime = Field(default_factory=datetime.utcnow)
