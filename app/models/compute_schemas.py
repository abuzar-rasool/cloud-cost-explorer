"""
Compute-specific schemas for the pricing API.
"""
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.base_schemas import ProviderError
from app.models.enums import Provider, Region


class ComputeSpecs(BaseModel):
    """Specifications for compute pricing comparison."""
    vcpu: int = Field(..., description="Number of virtual CPUs", gt=0)
    ram_gib: float = Field(..., description="RAM in GiB", gt=0)


class ComputePrice(BaseModel):
    """Compute instance price from a provider."""
    provider: Provider = Field(..., description="Provider of the price")
    sku: str = Field(..., description="SKU of the price")
    service_name: str = Field(..., description="Name of the service")
    provider_region: str = Field(..., description="Region of the price")
    vcpu: int = Field(..., description="Number of virtual CPUs")
    ram_gib: float = Field(..., description="RAM in GiB")
    hourly_usd: float = Field(..., description="Price per hour in USD")
    service_details: dict = Field(None, description="Cloud provider specific service details, would contain all the details in the pricing response for the service")

class ComputePricingRequest(BaseModel):
    """Request for compute pricing comparison."""
    region: Region
    specs: ComputeSpecs


class ComputePricingResponse(BaseModel):
    """Response for compute pricing comparison."""
    results: List[ComputePrice]
    errors: List[ProviderError] = [] 