"""
Base schemas for the pricing API.
"""
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel

from app.models.enums import ErrorSource, Provider, Region


class ProviderError(BaseModel):
    """Error response from a provider."""
    provider: str
    message: str
    details: Optional[Dict] = None


class ErrorResponse(BaseModel):
    """API error response."""
    error: str
    source: ErrorSource
    details: Optional[Dict] = None 