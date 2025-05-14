"""
Cloud pricing service for comparing prices across providers.
"""
import logging
import asyncio
from typing import List, Optional
from app.clients.provider_factory import ProviderFactory
from app.clients.provider_interface import ProviderError
from app.models.enums import Region
from app.models.compute_schemas import ComputePrice, ComputeSpecs, ComputePricingResponse
from app.models.storage_schemas import StoragePrice, StorageSpecs, StoragePricingResponse
from app.models.base_schemas import ProviderError as ProviderErrorSchema

logger = logging.getLogger(__name__)


class PricingService:
    """Service for comparing cloud pricing across providers."""
    
    def __init__(self, provider_factory: Optional[ProviderFactory] = None):
        """
        Initialize the pricing service.
        
        Args:
            provider_factory: Optional provider factory for dependency injection
        """
        self.provider_factory = provider_factory or ProviderFactory()
    
    async def close(self):
        """Close all provider clients."""
        await self.provider_factory.close_all()
    
    async def get_compute_pricing(
        self,
        region: Region,
        specs: ComputeSpecs
    ) -> ComputePricingResponse:
        """
        Get compute pricing across all providers.
        
        Args:
            region: The target region or NO_FILTER for all regions
            specs: The compute specifications
            
        Returns:
            Compute pricing response with results from all providers
        """
        errors = []
        results = []
        
        # Get all provider instances
        providers = self.provider_factory.get_all_providers()
        
        # Create tasks for all providers
        tasks = [
            provider.get_compute_pricing(region, specs)
            for provider in providers
        ]
        
        # Process all tasks concurrently
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in task_results:
                if isinstance(result, ProviderError):
                    errors.append(ProviderErrorSchema(
                        provider=result.provider,
                        message=result.message,
                        details=result.details
                    ))
                elif isinstance(result, Exception):
                    logger.error(f"Unexpected error: {str(result)}")
                    errors.append(ProviderErrorSchema(
                        provider="unknown",
                        message=f"Unexpected error: {str(result)}",
                        details={"error_type": type(result).__name__}
                    ))
                elif isinstance(result, list):
                    results.extend(result)
        
        return ComputePricingResponse(results=results, errors=errors)
    
    async def get_storage_pricing(
        self,
        region: Region,
        specs: StorageSpecs
    ) -> StoragePricingResponse:
        """
        Get storage pricing across all providers.
        
        Args:
            region: The target region or NO_FILTER for all regions
            specs: The storage specifications
            
        Returns:
            Storage pricing response with results from all providers
        """
        errors = []
        results = []
        
        # Get all provider instances
        providers = self.provider_factory.get_all_providers()
        
        # Create tasks for all providers
        tasks = [
            provider.get_storage_pricing(region, specs)
            for provider in providers
        ]
        
        # Process all tasks concurrently
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in task_results:
                if isinstance(result, ProviderError):
                    errors.append(ProviderErrorSchema(
                        provider=result.provider,
                        message=result.message,
                        details=result.details
                    ))
                elif isinstance(result, Exception):
                    logger.error(f"Unexpected error: {str(result)}")
                    errors.append(ProviderErrorSchema(
                        provider="unknown",
                        message=f"Unexpected error: {str(result)}",
                        details={"error_type": type(result).__name__}
                    ))
                elif isinstance(result, list):
                    results.extend(result)
        
        return StoragePricingResponse(results=results, errors=errors)
