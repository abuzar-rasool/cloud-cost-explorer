"""
Interface for cloud provider implementations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.models.compute_schemas import ComputePrice
from app.models.storage_schemas import StoragePrice
from app.models.enums import Provider, Region
from app.models.compute_schemas import ComputeSpecs
from app.models.storage_schemas import StorageSpecs


@dataclass
class ProviderError(Exception):
    """Exception raised when there's an error from a cloud provider."""
    provider: str
    message: str
    details: Optional[Dict] = None


class CloudProviderInterface(ABC):
    """Interface that all cloud provider implementations must follow."""
    
    def __init__(self, provider_name: str):
        """
        Initialize the cloud provider.
        
        Args:
            provider_name: Name of the provider
        """
        self.provider_name = provider_name
    
    @abstractmethod
    async def get_compute_pricing(self, region: Region, specs: ComputeSpecs) -> List[ComputePrice]:
        """
        Get compute instance pricing for a region and specs
        
        Args:
            region: Region enum value
            specs: ComputeSpecs
            
        Returns:
            List of compute instance prices
            
        Raises:
            ProviderError: If there's an error getting prices
        """
        pass
    
    @abstractmethod
    async def get_storage_pricing(self, region: Region, specs: StorageSpecs) -> List[StoragePrice]:
        """
        Get storage pricing for a region and specs
        
        Args:
            region: Region enum value
            specs: StorageSpecs
            
        Returns:
            List of storage prices
            
        Raises:
            ProviderError: If there's an error getting prices
        """
        pass
    
    @abstractmethod
    async def close(self):
        """Close any open connections."""
        pass 