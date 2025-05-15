import logging
from typing import List
import json
import asyncio

import boto3

from app.models.compute_schemas import ComputePrice, ComputeSpecs
from app.models.storage_schemas import StoragePrice
from app.models.enums import Provider, Region, StorageTier
from app.models.storage_schemas import StorageSpecs
from app.clients.provider_interface import CloudProviderInterface

logger = logging.getLogger(__name__)

# AWS region mapping (one continent to many AWS regions)
# Each region is represented as a tuple of (region_code, display_name)
# The display_name is used for the AWS Pricing API queries
AWS_REGION_MAPPING = {
    Region.NORTH_AMERICA: [
        # US & Canada
        ("us-east-1",    "US East (N. Virginia)"),
        ("us-east-2",    "US East (Ohio)"),
        ("us-west-1",    "US West (N. California)"),
        ("us-west-2",    "US West (Oregon)"),
        ("ca-central-1", "Canada (Central)"),
        ("ca-west-1",    "Canada West (Calgary)"),
        ("mx-central-1", "Mexico (Central)"),
        # GovCloud
        ("us-gov-west-1", "AWS GovCloud (US-West)"),
        ("us-gov-east-1", "AWS GovCloud (US-East)"),
    ],
    Region.SOUTH_AMERICA: [
        ("sa-east-1", "South America (Sao Paulo)"),
    ],
    Region.EUROPE: [
        # Central Europe
        ("eu-central-1", "EU (Frankfurt)"),
        ("eu-central-2", "Europe (Zurich)"),
        # Western Europe
        ("eu-west-1",  "EU (Ireland)"),
        ("eu-west-2",  "EU (London)"),
        ("eu-west-3",  "EU (Paris)"),
        # Southern Europe
        ("eu-south-1", "EU (Milan)"),
        ("eu-south-2", "Europe (Spain)"),
        # Northern Europe
        ("eu-north-1", "EU (Stockholm)"),
    ],
    Region.ASIA: [
        ("ap-east-1",      "Asia Pacific (Hong Kong)"),
        ("ap-south-1",     "Asia Pacific (Mumbai)"),
        ("ap-south-2",     "Asia Pacific (Hyderabad)"),
        ("ap-northeast-1", "Asia Pacific (Tokyo)"),
        ("ap-northeast-2", "Asia Pacific (Seoul)"),
        ("ap-northeast-3", "Asia Pacific (Osaka)"),
        ("ap-southeast-1", "Asia Pacific (Singapore)"),
        ("ap-southeast-3", "Asia Pacific (Jakarta)"),
        ("ap-southeast-5", "Asia Pacific (Malaysia)"),
        ("ap-southeast-7", "Asia Pacific (Thailand)"),
        ("il-central-1",   "Israel (Tel Aviv)"),
        ("me-south-1",     "Middle East (Bahrain)"),
        ("me-central-1",   "Middle East (UAE)"),
        # Note: Sydney & Melbourne handled under Oceania
    ],
    Region.OCEANIA: [
        ("ap-southeast-2", "Asia Pacific (Sydney)"),
        ("ap-southeast-4", "Asia Pacific (Melbourne)"),
    ],
    Region.AFRICA: [
        ("af-south-1", "Africa (Cape Town)"),
    ],
    Region.ANTARCTICA: [],       # no AWS regions
    Region.MULTI_REGION: [],     # multi-region services
}

# Populate ALL regions
AWS_REGION_MAPPING[Region.ALL] = [
    region_tuple
    for regions in AWS_REGION_MAPPING.values()
    for region_tuple in regions
    if regions  # Skip empty region lists
]

# Create display names mapping from the region mapping
AWS_REGION_DISPLAY_NAMES = {
    code: name
    for regions in AWS_REGION_MAPPING.values()
    for code, name in regions
    if regions  # Skip empty region lists
}


class AwsProvider(CloudProviderInterface):
    def __init__(self):
        logger.info("Initializing AwsProvider...")
        super().__init__(provider_name="aws")
        self.pricing_client = boto3.client("pricing", region_name="us-east-1")
        logger.info("AwsProvider initialized with boto3 pricing client.")

    async def get_compute_pricing(self, region: Region, specs: ComputeSpecs) -> List[ComputePrice]:
        logger.info(
            f"Fetching compute pricing for region={region}, specs={specs}.")

        def sync_compute_pricing():
            import re
            try:
                # Query parameters
                operating_system = "Linux"
                tenancy = "Shared"
                preinstalled_software = "NA"
                license_model = "No License required"
                service_code = "AmazonEC2"
                memory_str = f"{int(specs.ram_gib)} GiB"
                vcpu_str = str(int(specs.vcpu))

                region_tuples = AWS_REGION_MAPPING.get(region, [])
                if not region_tuples:
                    logger.warning(
                        f"No region tuples found for region: {region}")
                    return []
                results = []
                for region_code, region_display in region_tuples:
                    logger.info(
                        f"Querying pricing for region_code={region_code}, region_display={region_display}")
                    filters = [
                        {"Type": "TERM_MATCH", "Field": "termType",
                            "Value": "OnDemand"},
                        {"Type": "TERM_MATCH",
                            "Field": "capacitystatus", "Value": "Used"},
                        {"Type": "TERM_MATCH", "Field": "location",
                            "Value": region_display},
                        {"Type": "TERM_MATCH", "Field": "operatingSystem",
                            "Value": operating_system},
                        {"Type": "TERM_MATCH", "Field": "tenancy", "Value": tenancy},
                        {"Type": "TERM_MATCH", "Field": "preInstalledSw",
                            "Value": preinstalled_software},
                        {"Type": "TERM_MATCH", "Field": "licenseModel",
                            "Value": license_model},
                        {"Type": "TERM_MATCH", "Field": "vcpu", "Value": vcpu_str},
                        {"Type": "TERM_MATCH", "Field": "memory", "Value": memory_str},
                    ]
                    paginator = self.pricing_client.get_paginator(
                        "get_products")
                    page_iterator = paginator.paginate(
                        ServiceCode=service_code, Filters=filters)
                    for page in page_iterator:
                        for price_str in page["PriceList"]:
                            try:
                                price_item = json.loads(price_str)
                                product = price_item.get("product", {})
                                attrs = product.get("attributes", {})
                                vcpu = int(attrs.get("vcpu", 0))
                                memory_val = attrs.get("memory", "0 GiB")
                                match = re.match(r"([\d.]+) GiB", memory_val)
                                ram_gib = float(
                                    match.group(1)) if match else 0.0
                                if vcpu != specs.vcpu or abs(ram_gib - specs.ram_gib) > 0.1:
                                    continue
                                on_demand_terms = price_item.get(
                                    "terms", {}).get("OnDemand", {})
                                for term in on_demand_terms.values():
                                    for pd in term.get("priceDimensions", {}).values():
                                        price_per_hour = float(
                                            pd["pricePerUnit"]["USD"])
                                        logger.info(
                                            f"Found matching instance: {attrs.get('instanceType', '')} in {region_code} at ${price_per_hour}/hr")
                                        results.append(ComputePrice(
                                            provider=Provider.AWS,
                                            sku=product.get("sku", ""),
                                            service_name=attrs.get(
                                                "instanceType", ""),
                                            provider_region=region_code,
                                            vcpu=vcpu,
                                            ram_gib=ram_gib,
                                            hourly_usd=price_per_hour,
                                            service_details=attrs
                                        ))
                            except Exception as e:
                                logger.error(
                                    f"Error parsing price item: {e}", exc_info=True)
                                continue
                    logger.info(
                        f"Region {region_code}: {len(results)} matching compute prices found so far.")
                logger.info(
                    f"Total matching compute prices found: {len(results)}")
                return results
            except Exception as e:
                logger.error(
                    f"Exception in sync_compute_pricing: {e}", exc_info=True)
                return []
        results = await asyncio.to_thread(sync_compute_pricing)
        logger.info(f"Returning {len(results)} compute pricing results.")
        return results

    async def get_storage_pricing(self, region: Region, specs: StorageSpecs) -> List[StoragePrice]:
        logger.info(
            f"Fetching storage pricing for region={region}, specs={specs}")

        # Map our tiers to the AWS storageClass values
        tier_to_classes = {
            StorageTier.SMART: ["Intelligent-Tiering"],
            StorageTier.FREQUENT_ACCESS:    [
                "General Purpose",
                "Non-Critical Data",
                "High Performance",
            ],
            StorageTier.OCCASIONAL_ACCESS:  ["Standard-IA", "One Zone-IA"],
            StorageTier.RARE_ACCESS:        ["Glacier Instant Retrieval", "Glacier Flexible Retrieval"],
            StorageTier.SHORT_TERM_ARCHIVE:  ["Glacier Flexible Retrieval"],
            StorageTier.LONG_TERM_ARCHIVE:   ["Deep Archive"],
        }
        target_classes = tier_to_classes.get(specs.tier, [])
        if not target_classes:
            logger.warning(f"No classes mapped for storage tier {specs.tier}")
            return []

        def sync_storage_pricing() -> List[StoragePrice]:
            results: List[StoragePrice] = []
            service_code = "AmazonS3"

            for region_code, region_name in AWS_REGION_MAPPING.get(region, []):
                for sc in target_classes:
                    logger.debug(
                        f"  → querying {sc} in {region_name} ({region_code})")
                    filters = [
                        {"Type": "TERM_MATCH", "Field": "location",
                            "Value": region_name},
                        {"Type": "TERM_MATCH", "Field": "productFamily",
                            "Value": "Storage"},
                        {"Type": "TERM_MATCH", "Field": "storageClass",   "Value": sc},
                    ]
                    paginator = self.pricing_client.get_paginator(
                        "get_products")

                    for page in paginator.paginate(ServiceCode=service_code, Filters=filters):
                        for raw in page["PriceList"]:
                            try:
                                item = json.loads(raw)
                                prod = item["product"]
                                attrs = prod["attributes"]
                                sku = prod["sku"]
                                cls = attrs.get("storageClass", sc)

                                # walk OnDemand terms → priceDimensions
                                for term in item.get("terms", {}).get("OnDemand", {}).values():
                                    for dim in term.get("priceDimensions", {}).values():
                                        unit = dim.get("unit", "")
                                        if unit not in ("GB-Mo", "GB-Month"):
                                            continue
                                        usd = float(dim["pricePerUnit"]["USD"])
                                        results.append(StoragePrice(
                                            provider=Provider.AWS,
                                            sku=sku,
                                            service_name='Amazon S3 ' + cls,
                                            provider_region=region_code,
                                            tier=specs.tier,
                                            gb_month_usd=usd,
                                            service_details=attrs
                                        ))
                            except Exception as e:
                                logger.error(
                                    f"Error parsing S3 price entry: {e}", exc_info=True)
                                continue
            logger.info(
                f"Found {len(results)} storage prices for {specs.tier} in {region}")
            return results

        return await asyncio.to_thread(sync_storage_pricing)
