"""
Storage-specific schemas for the pricing API.
"""
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.base_schemas import ProviderError
from app.models.enums import Provider, Region, StorageTier


class StorageSpecs(BaseModel):
    """Specifications for storage pricing comparison."""
    tier: StorageTier = Field(..., description="Storage tier")


class StoragePrice(BaseModel):
    """Storage price from a provider."""
    provider: Provider = Field(..., description="Provider of the price")
    sku: str = Field(..., description="SKU of the price")
    service_name: str = Field(..., description="Name of the service")
    provider_region: str = Field(..., description="Region of the price")
    tier: StorageTier = Field(..., description="Storage tier in which the service is available")
    gb_month_usd: float = Field(..., description="Price per GB per month in USD")
    service_details: dict = Field(None, description="Cloud provider specific service details, would contain all the details in the pricing response for the service")

class StoragePricingRequest(BaseModel):
    """Request for storage pricing comparison."""
    region: Region
    specs: StorageSpecs


class StoragePricingResponse(BaseModel):
    """Response for storage pricing comparison."""
    results: List[StoragePrice]
    errors: List[ProviderError] = [] 