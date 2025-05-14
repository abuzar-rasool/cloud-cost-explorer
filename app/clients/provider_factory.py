"""
Factory for creating cloud provider instances.
"""
import logging
from typing import List

from app.clients.aws_provider import AwsProvider
from app.clients.provider_interface import CloudProviderInterface, ProviderError

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating and managing cloud provider instances."""
    
    def __init__(self):
        """Initialize the provider factory."""
        self._providers = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all supported cloud providers."""
        # Initialize AWS provider
        try:
            aws_provider = AwsProvider()
            self._providers.append(aws_provider)
        except Exception as e:
            logger.error(f"Failed to initialize AWS provider: {str(e)}")
    
    def get_all_providers(self) -> List[CloudProviderInterface]:
        """
        Get all initialized cloud providers.
        
        Returns:
            List of cloud provider instances
        """
        return self._providers
    
    async def close_all(self):
        """Close all provider clients."""
        for provider in self._providers:
            try:
                await provider.close()
            except Exception as e:
                logger.error(f"Error closing {provider.provider_name} provider: {str(e)}") 