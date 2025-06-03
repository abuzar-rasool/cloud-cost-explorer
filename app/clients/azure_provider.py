import logging
import asyncio
from typing import List, Optional

import httpx

from app.clients.provider_interface import CloudProviderInterface, ProviderError
from app.models.enums import Provider, Region
from app.models.compute_schemas import ComputePrice, ComputeSpecs
from app.models.storage_schemas import StoragePrice, StorageSpecs, StorageTier

logger = logging.getLogger(__name__)

AZURE_PRICES_API = "https://prices.azure.com/api/retail/prices"

AZURE_REGION_MAPPING = {
    Region.NORTH_AMERICA: ["eastus", "centralus", "westus2"],
    Region.EUROPE:        [
        "westeurope", "northeurope", "uksouth", "ukwest", "francecentral", "francesouth",
        "germanywestcentral", "germanynorth", "swedencentral", "switzerlandnorth",
        "switzerlandwest", "norwayeast", "norwaywest"
    ],
    Region.ASIA:          ["southeastasia", "eastasia", "japaneast", "japanwest", "koreacentral", "koreasouth"],
    
}

SKU_SPECS = {
    "Standard_D2s_v3": {"vcpu": 2, "ram_gib": 8},
    "Standard_F4s":    {"vcpu": 4, "ram_gib": 8},
    "Standard_B1s":    {"vcpu": 1, "ram_gib": 1},
    "Standard_B2ms":   {"vcpu": 2, "ram_gib": 8},
    "Standard_D4s_v3": {"vcpu": 4, "ram_gib": 16},
    "Standard_E2s_v3": {"vcpu": 2, "ram_gib": 16},
    "Standard_E4s_v3": {"vcpu": 4, "ram_gib": 32},
    "Standard_E8s_v3": {"vcpu": 8, "ram_gib": 64},      
}


class AzureProvider(CloudProviderInterface):
    def __init__(self):
        super().__init__(provider_name="azure")
        self._client = httpx.AsyncClient()
        logger.info("AzureProvider initialized.")

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def _fetch_items(self, filter_str: str) -> List[dict]:
        items: List[dict] = []
        try:
            resp = await self._client.get(AZURE_PRICES_API, params={"$filter": filter_str})
            if resp.status_code != 200:
                text = await resp.text()
                logger.error(f"Azure API returned status {resp.status_code}: {text}")
                raise ProviderError(self.provider_name, f"Azure API returned {resp.status_code}")
            data = await resp.json()
            items.extend(data.get("Items", []))
            next_link: Optional[str] = data.get("NextPageLink")
            while next_link:
                resp = await self._client.get(next_link)
                if resp.status_code != 200:
                    text = await resp.text()
                    logger.error(f"Azure API returned status {resp.status_code}: {text}")
                    raise ProviderError(self.provider_name, f"Azure API returned {resp.status_code}")
                data = await resp.json()
                items.extend(data.get("Items", []))
                next_link = data.get("NextPageLink")
        except Exception as e:
            logger.error(f"Error fetching items from Azure API: {e}")
            raise
        return items

    async def get_compute_pricing(self, region: Region, specs: ComputeSpecs) -> List[ComputePrice]:
        codes = AZURE_REGION_MAPPING.get(region, [])
        if not codes:
            logger.warning(f"No Azure regions mapped for {region}")
            return []

        results: List[ComputePrice] = []

        async def fetch_region(rc: str) -> List[ComputePrice]:
            filter_str = (
                "serviceFamily eq 'Compute' "
                "and serviceName eq 'Virtual Machines' "
                f"and armRegionName eq '{rc}'"
            )
            raw = await self._fetch_items(filter_str)
            matched: List[ComputePrice] = []
            for item in raw:
                sku = item.get("armSkuName") or item.get("skuName", "")
                info = SKU_SPECS.get(sku)
                if info and info["vcpu"] == specs.vcpu and abs(info["ram_gib"] - specs.ram_gib) < 0.1:
                    matched.append(ComputePrice(
                        provider=Provider.AZURE,
                        sku=sku,
                        service_name=item.get("productName", ""),
                        provider_region=rc,
                        vcpu=info["vcpu"],
                        ram_gib=info["ram_gib"],
                        hourly_usd=item.get("unitPrice", 0.0),
                        service_details=item
                    ))
            return matched

        tasks = [fetch_region(rc) for rc in codes]
        for coro in asyncio.as_completed(tasks):
            try:
                results.extend(await coro)
            except Exception as e:
                logger.error(f"Error fetching Azure compute pricing for region: {e}")

        return results

    async def get_storage_pricing(self, region: Region, specs: StorageSpecs) -> List[StoragePrice]:
        codes = AZURE_REGION_MAPPING.get(region, [])
        if not codes:
            logger.warning(f"No Azure regions for storage {region}")
            return []

        tier_map = {
            StorageTier.FREQUENT_ACCESS:  "Hot",
            StorageTier.OCCASIONAL_ACCESS: "Cool",
            StorageTier.RARE_ACCESS:      "Archive",
        }
        sku_tier = tier_map.get(specs.tier)
        if not sku_tier:
            logger.warning(f"No mapping for storage tier {specs.tier}")
            return []

        results: List[StoragePrice] = []

        for rc in codes:
            filter_str = (
                "serviceFamily eq 'Storage' "
                f"and armRegionName eq '{rc}' "
                f"and skuName eq 'Blob Storage {sku_tier}'"
            )
            raw = await self._fetch_items(filter_str)
            for item in raw:
                results.append(StoragePrice(
                    provider=Provider.AZURE,
                    sku=item.get("skuName", ""),
                    service_name=item.get("productName", ""),
                    provider_region=rc,
                    tier=specs.tier,
                    gb_month_usd=item.get("unitPrice", 0.0),
                    service_details=item
                ))

        return results
