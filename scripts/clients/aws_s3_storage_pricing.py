#!/usr/bin/env python3
"""
AWS S3 Storage Pricing Data Extraction Script

This script fetches AWS S3 storage pricing data from the AWS Pricing API
and saves it to a single CSV file.

The script extracts the following columns:
- provider: The cloud vendor (e.g., AWS)
- service_code: The official product family name (e.g., AmazonS3)
- service_name: The product name
- storage_class: The vendor-specific tier (e.g., Standard, Glacier)
- region: Mapped continent
- access_tier: Standardized access tier (FREQUENT, OCCASIONAL, RARE, ARCHIVE)
- capacity_price: Price per GiB-month
- read_price: Price per million read operations
- write_price: Price per million write operations
- egress_price: Price per GiB for data egress
- flat_item_price: Any fixed monthly fees
- other_details: Raw JSON from the pricing API

USAGE:
    python3 scripts/aws_s3_storage_pricing.py [--max-records N]

    Options:
        --max-records N    Limit processing to N records (default: no limit)
"""

import boto3
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# AWS region mapping to continents
AWS_REGION_TO_CONTINENT = {
    # North America
    'us-east-1': 'north_america',
    'us-east-2': 'north_america',
    'us-west-1': 'north_america',
    'us-west-2': 'north_america',
    'ca-central-1': 'north_america',
    'ca-west-1': 'north_america',
    'us-gov-east-1': 'north_america',
    'us-gov-west-1': 'north_america',
    'mx-central-1': 'north_america',
    
    # South America
    'sa-east-1': 'south_america',
    
    # Europe
    'eu-central-1': 'europe',
    'eu-central-2': 'europe',
    'eu-north-1': 'europe',
    'eu-south-1': 'europe',
    'eu-south-2': 'europe',
    'eu-west-1': 'europe',
    'eu-west-2': 'europe',
    'eu-west-3': 'europe',
    
    # Asia Pacific
    'ap-east-1': 'asia_pacific',
    'ap-east-2': 'asia_pacific',
    'ap-northeast-1': 'asia_pacific',
    'ap-northeast-2': 'asia_pacific',
    'ap-northeast-3': 'asia_pacific',
    'ap-south-1': 'asia_pacific',
    'ap-south-2': 'asia_pacific',
    'ap-southeast-1': 'asia_pacific',
    'ap-southeast-2': 'asia_pacific',
    'ap-southeast-3': 'asia_pacific',
    'ap-southeast-4': 'asia_pacific',
    'ap-southeast-5': 'asia_pacific',
    'ap-southeast-7': 'asia_pacific',
    
    # Middle East
    'me-central-1': 'middle_east',
    'me-south-1': 'middle_east',
    'il-central-1': 'middle_east',
    
    # Africa
    'af-south-1': 'africa',
    'af-south-1-los-1': 'africa',
    
    # China
    'cn-north-1': 'asia_pacific',
    'cn-northwest-1': 'asia_pacific',
}

AWS_LOCATION_TO_REGION_CODE = {
    'US East (N. Virginia)': 'us-east-1',
    'US East (Ohio)': 'us-east-2',
    'US West (N. California)': 'us-west-1',
    'US West (Oregon)': 'us-west-2',
    'Canada (Central)': 'ca-central-1',
    'Canada West (Calgary)': 'ca-west-1',
    'Europe (Ireland)': 'eu-west-1',
    'EU (Ireland)': 'eu-west-1',
    'Europe (Frankfurt)': 'eu-central-1',
    'EU (Frankfurt)': 'eu-central-1',
    'Europe (London)': 'eu-west-2',
    'EU (London)': 'eu-west-2',
    'Europe (Paris)': 'eu-west-3',
    'EU (Paris)': 'eu-west-3',
    'Europe (Stockholm)': 'eu-north-1',
    'EU (Stockholm)': 'eu-north-1',
    'Europe (Milan)': 'eu-south-1',
    'EU (Milan)': 'eu-south-1',
    'Europe (Spain)': 'eu-south-2',
    'EU (Spain)': 'eu-south-2',
    'Europe (Zurich)': 'eu-central-2',
    'EU (Zurich)': 'eu-central-2',
    'Asia Pacific (Tokyo)': 'ap-northeast-1',
    'Asia Pacific (Seoul)': 'ap-northeast-2',
    'Asia Pacific (Singapore)': 'ap-southeast-1',
    'Asia Pacific (Sydney)': 'ap-southeast-2',
    'Asia Pacific (Mumbai)': 'ap-south-1',
    'Asia Pacific (Hong Kong)': 'ap-east-1',
    'Asia Pacific (Jakarta)': 'ap-southeast-3',
    'Asia Pacific (Osaka)': 'ap-northeast-3',
    'Asia Pacific (Hyderabad)': 'ap-south-2',
    'Asia Pacific (Melbourne)': 'ap-southeast-4',
    'Asia Pacific (Malaysia)': 'ap-southeast-5',
    'Asia Pacific (Taipei)': 'ap-east-2',
    'Asia Pacific (Thailand)': 'ap-southeast-7',
    'South America (Sao Paulo)': 'sa-east-1',
    'Middle East (UAE)': 'me-central-1',
    'Middle East (Bahrain)': 'me-south-1',
    'Africa (Cape Town)': 'af-south-1',
    'Israel (Tel Aviv)': 'il-central-1',
    'Mexico (Central)': 'mx-central-1',
    'AWS GovCloud (US-West)': 'us-gov-west-1',
    'AWS GovCloud (US-East)': 'us-gov-east-1',
    'China (Beijing)': 'cn-north-1',
    'China (Ningxia)': 'cn-northwest-1',
}

class AWSStoragePricingExtractor:
    def __init__(self, max_records: Optional[int] = None):
        self.pricing_client = boto3.client("pricing", region_name="us-east-1")
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file_path = self.data_dir / f"aws_s3_storage_pricing_{timestamp}.csv"
        self.summary_file_path = self.data_dir / f"aws_s3_storage_pricing_summary_{timestamp}.txt"
        
        self.csv_columns = [
            'provider', 'service_code', 'service_name', 'storage_class', 'region', 
            'access_tier', 'capacity_price', 'read_price', 'write_price',
            'flat_item_price', 'other_details'
        ]
        
        self.max_records = max_records
        self.batch_size = 200
        self.total_records = 0
        self.pages_processed = 0
        self.items_seen = 0
        self.items_filtered_out = 0
        self.items_with_errors = 0
        self.unmapped_regions = {}
        
        # This map will hold the final records as they are being built.
        # Key: (continent, volumeType), Value: record_dictionary
        self.storage_records_map = {}
        
        # Detailed filtering reasons tracking
        self.filtering_reasons = {
            'no_on_demand_terms': 0,
            'unmapped_region': 0,
            'no_valid_pricing': 0
        }
        
        self.local_zone_pattern = re.compile(r'^([a-z0-9-]+)-[a-z]{3,4}-\d+$')
        self.wavelength_zone_pattern = re.compile(r'^([a-z0-9-]+)-wl\d+(?:-[a-z0-9]+)?$')
        
        logger.info(f"Creating new CSV file: {self.csv_file_path}")
        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.csv_columns, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
        if self.max_records:
            logger.info(f"Processing limit: {self.max_records} records")
        else:
            logger.info("Processing limit: No limit")

    def get_api_storage_class_map(self):
        """Returns a mapping from API group prefixes to storage classes."""
        return {
            "S3-API-Std": ["General Purpose"],
            "S3-API-SIA": ["Infrequent Access"],
            "S3-API-ZIA": ["Infrequent Access"], # One-Zone is a flavor of IA
            "S3-API-GIR": ["Archive Instant Retrieval"],
            "S3-API-GDA": ["Archive"],
            "S3-API-GLACIER": ["Archive"],
            "S3-API-INT": ["Intelligent-Tiering"]
        }

    def get_continent_from_region(self, region_code: str) -> Optional[str]:
        if not region_code:
            return None
        
        continent = AWS_REGION_TO_CONTINENT.get(region_code)
        if continent:
            return continent
        
        local_zone_match = self.local_zone_pattern.match(region_code)
        if local_zone_match:
            base_region = local_zone_match.group(1)
            return AWS_REGION_TO_CONTINENT.get(base_region)
            
        wavelength_zone_match = self.wavelength_zone_pattern.match(region_code)
        if wavelength_zone_match:
            base_region = wavelength_zone_match.group(1)
            return AWS_REGION_TO_CONTINENT.get(base_region)
            
        return None

    def map_access_tier(self, storage_class: str) -> str:
        """Map AWS S3 storage class to a standardized access tier."""
        if not storage_class:
            return "FREQUENT_ACCESS"

        storage_class_lower = storage_class.lower()

        # More specific matches first - Archive tiers
        if "archive" in storage_class_lower and "instant" in storage_class_lower:
            return "RARE_ACCESS"  # Glacier Instant Retrieval
        elif "archive" in storage_class_lower:
            return "ARCHIVE"  # Deep Archive, Glacier, etc.
        elif "glacier" in storage_class_lower:
            return "ARCHIVE"
        
        # Infrequent access tiers
        if "infrequent access" in storage_class_lower or "infrequent" in storage_class_lower:
            return "OCCASIONAL_ACCESS"
        
        # High performance tiers
        if "high performance" in storage_class_lower or "express" in storage_class_lower:
            return "FREQUENT_ACCESS"
        
        # Standard/General purpose
        if "general purpose" in storage_class_lower or "standard" in storage_class_lower:
            return "FREQUENT_ACCESS"
            
        # Intelligent tiering - starts in frequent
        if "intelligent" in storage_class_lower:
            return "FREQUENT_ACCESS"
        
        # Non-critical data (Reduced Redundancy)
        if "non-critical" in storage_class_lower:
            return "FREQUENT_ACCESS"
        
        return "FREQUENT_ACCESS"  # Default fallback

    def get_on_demand_terms(self, price_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts OnDemand terms from a price item."""
        return price_item.get("terms", {}).get("OnDemand", {})

    def extract_price(self, price_dimensions: Dict[str, Any]) -> Optional[float]:
        """
        Extracts the price from the price dimensions.
        """
        price_by_tier = {}
        for dim in price_dimensions.values():
            price_str = dim.get('pricePerUnit', {}).get('USD')
            if price_str:
                try:
                    price = float(price_str)
                    begin_range = int(dim.get('beginRange', '0'))
                    price_by_tier[begin_range] = price
                except (ValueError, TypeError):
                    continue
        
        if not price_by_tier:
            return None

        # Return the price for the lowest usage tier, rounded to 6 decimal places
        lowest_tier = min(price_by_tier.keys())
        raw_price = price_by_tier[lowest_tier]
        return round(raw_price, 6)

    def get_service_name(self, attributes: Dict[str, Any]) -> str:
        """Construct a descriptive service name from product attributes."""
        storage_class = attributes.get("storageClass", "General Purpose")
        
        # Use standardized naming
        base_name = "Amazon S3"
        
        # Clean up storage class names for better readability
        if storage_class == "General Purpose":
            return f"{base_name} - Standard"
        elif storage_class == "Archive Instant Retrieval":
            return f"{base_name} - Glacier Instant Retrieval"
        elif storage_class == "Archive":
            return f"{base_name} - Glacier Deep Archive"
        elif storage_class == "Infrequent Access":
            return f"{base_name} - Infrequent Access"
        elif storage_class == "Intelligent-Tiering":
            return f"{base_name} - Intelligent Tiering"
        elif storage_class == "Non-Critical Data":
            return f"{base_name} - Reduced Redundancy"
        elif storage_class == "High Performance":
            return f"{base_name} - Express One Zone"
        else:
            return f"{base_name} - {storage_class}"

    def process_storage_item(self, price_item: Dict[str, Any]):
        try:
            attributes = price_item.get('product', {}).get('attributes', {})
            volume_type = attributes.get('volumeType')
            location = attributes.get('location')
            storage_class = attributes.get('storageClass')

            if not all([volume_type, location, storage_class]):
                return
            
            # Filter out Tags storage class - these are metadata costs, not object storage
            if storage_class == 'Tags' or 'tag' in volume_type.lower():
                return

            region_code = AWS_LOCATION_TO_REGION_CODE.get(location)
            if not region_code:
                if location not in self.unmapped_regions:
                    self.unmapped_regions[location] = 0
                self.unmapped_regions[location] += 1
                return

            continent = self.get_continent_from_region(region_code)
            if not continent:
                return
            
            # Use a composite key of continent and storage class for broader matching
            record_key = (continent, storage_class)

            # Create a base record if it doesn't exist
            if record_key not in self.storage_records_map:
                service_name = self.get_service_name(attributes)
                
                self.storage_records_map[record_key] = {
                    'provider': 'AWS',
                    'service_code': attributes.get("servicecode"),
                    'service_name': service_name,
                    'storage_class': storage_class,
                    'region': continent,
                    'access_tier': self.map_access_tier(storage_class),
                    'capacity_price': None,
                    'read_price': None,
                    'write_price': None,
                    'flat_item_price': None,
                    'other_details': json.dumps({"pricing_api": price_item.get('product')})
                }

            # Add capacity pricing
            on_demand_terms = self.get_on_demand_terms(price_item)
            if not on_demand_terms:
                return

            for term in on_demand_terms.values():
                price = self.extract_price(term.get("priceDimensions", {}))
                
                # Check if it's a valid capacity price (GB-Mo)
                is_capacity_price = False
                for dim in term.get("priceDimensions", {}).values():
                    if 'gb-mo' in dim.get('unit', '').lower():
                        is_capacity_price = True
                        break
                
                if price is not None and is_capacity_price:
                    # Only update if not already set, to avoid overwriting with tiered pricing
                    if self.storage_records_map[record_key]['capacity_price'] is None:
                        self.storage_records_map[record_key]['capacity_price'] = price
                    break # Assume first price is the base price
        except Exception as e:
            logger.warning(f"Could not process storage item: {price_item.get('product', {}).get('sku')} - {e}")

    def process_api_request_item(self, price_item: Dict[str, Any]):
        attributes = price_item.get('product', {}).get('attributes', {})
        on_demand_terms = self.get_on_demand_terms(price_item)
        if not on_demand_terms:
            return

        price_per_million = 0
        conversion_info = None  # For debugging
        
        for term in on_demand_terms.values():
            for dim in term.get("priceDimensions", {}).values():
                price_str = dim.get('pricePerUnit', {}).get('USD')
                if price_str:
                    try:
                        base_price = float(price_str)
                        unit_desc = dim.get("description", "").lower()
                        unit = dim.get("unit", "").lower()
                        
                        # Skip zero prices - these are legitimate free operations
                        if base_price == 0.0:
                            continue
                        
                        # More robust and specific unit detection for AWS S3 pricing
                        if any(pattern in unit_desc for pattern in ["per 1,000 requests", "1,000 requests", "1000 requests"]) or \
                           any(pattern in unit for pattern in ["1000requests", "1krequest"]):
                            price_per_million = base_price * 1000  # Convert per 1K to per million
                            conversion_info = f"per_1000: {base_price} * 1000 = {price_per_million}"
                        elif any(pattern in unit_desc for pattern in ["per 10,000 requests", "10,000 requests", "10000 requests"]) or \
                             any(pattern in unit for pattern in ["10000requests", "10krequest"]):
                            price_per_million = base_price * 100   # Convert per 10K to per million
                            conversion_info = f"per_10000: {base_price} * 100 = {price_per_million}"
                        elif any(pattern in unit_desc for pattern in ["per 1,000,000 requests", "1,000,000 requests", "1000000 requests", "million requests"]) or \
                             any(pattern in unit for pattern in ["1000000requests", "millionrequests", "1mrequests"]):
                            price_per_million = base_price         # Already per million
                            conversion_info = f"per_million: {base_price} (no conversion)"
                        # Check for very specific S3 operations that might have high per-request pricing
                        elif any(term in unit_desc for term in ["glacier", "archive", "deep archive", "retrieval"]) and \
                             ("requests" in unit or "requests" in unit_desc):
                            # Glacier/Archive operations can be expensive per request, but cap the conversion
                            if base_price > 0.05:  # If more than 5 cents per request, it's likely not per-request pricing
                                logger.debug(f"Skipping high-priced archive operation: ${base_price} - {unit_desc} - SKU: {price_item.get('product', {}).get('sku')}")
                                continue
                            price_per_million = base_price * 1000000
                            conversion_info = f"archive_per_request: {base_price} * 1000000 = {price_per_million}"
                        elif "requests" in unit and "requests" in unit_desc:
                            # Standard request pricing - but validate the base price is reasonable
                            if base_price > 0.01:  # If more than 1 cent per request, it's suspicious
                                logger.warning(f"Suspicious per-request price: ${base_price} - {unit_desc} - SKU: {price_item.get('product', {}).get('sku')}")
                                continue
                            price_per_million = base_price * 1000000
                            conversion_info = f"per_request: {base_price} * 1000000 = {price_per_million}"
                        elif "requests" in unit_desc and not "requests" in unit:
                            # Unit description mentions requests but unit field doesn't - try to parse
                            if any(pattern in unit_desc for pattern in ["1,000", "1000"]):
                                price_per_million = base_price * 1000
                                conversion_info = f"desc_per_1000: {base_price} * 1000 = {price_per_million}"
                            elif any(pattern in unit_desc for pattern in ["10,000", "10000"]):
                                price_per_million = base_price * 100
                                conversion_info = f"desc_per_10000: {base_price} * 100 = {price_per_million}"
                            else:
                                # Default to per-request but validate price
                                if base_price > 0.01:
                                    logger.debug(f"Skipping suspicious request price from description: ${base_price} - {unit_desc} - SKU: {price_item.get('product', {}).get('sku')}")
                                    continue
                                price_per_million = base_price * 1000000
                                conversion_info = f"desc_per_request: {base_price} * 1000000 = {price_per_million}"
                        else:
                            # Skip non-request pricing items or unrecognized patterns
                            logger.debug(f"Skipping non-request item: unit='{unit}', desc='{unit_desc}', price=${base_price} - SKU: {price_item.get('product', {}).get('sku')}")
                            continue
                        
                        # Validate the result is reasonable for S3 operations
                        if price_per_million < 0.00001:
                            logger.debug(f"Skipping very low price: ${price_per_million:.6f} from {conversion_info}")
                            continue
                        elif price_per_million > 5000:  # Adjust threshold to $5000 per million for S3
                            logger.warning(f"High price per million: ${price_per_million:.6f} from {conversion_info} - SKU: {price_item.get('product', {}).get('sku')}")
                            # Still use it but log for investigation
                        
                        # Round to 6 decimal places to avoid scientific notation and maintain precision
                        price_per_million = round(price_per_million, 6)
                        break
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to parse price: {price_str} - {e}")
                        continue
            if price_per_million > 0:
                break
        
        if price_per_million == 0:
            return

        operation = attributes.get('operation', '').lower()
        group = attributes.get('group', '')
        location = attributes.get('location')
        usage_type = attributes.get('usagetype', '').lower()
        
        region_code = AWS_LOCATION_TO_REGION_CODE.get(location)
        if not region_code: 
            return
        continent = self.get_continent_from_region(region_code)
        if not continent: 
            return

        # Determine operation type from multiple sources with better pattern matching
        price_key = None
        
        # Check operation field first (most reliable)
        if operation:
            if any(op in operation for op in ['put', 'copy', 'post', 'upload']):
                price_key = 'write_price'
            elif any(op in operation for op in ['get', 'select', 'head', 'retrieve']):
                price_key = 'read_price'
            elif 'list' in operation:
                # LIST operations are typically considered write operations in S3 billing
                price_key = 'write_price'
        
        # Check usage type if operation didn't match
        if not price_key and usage_type:
            # More specific patterns for AWS S3 usage types
            if any(pattern in usage_type for pattern in ['put', 'copy', 'post', 'upload', 'list', 'requests-tier1', '-put-', '-copy-']):
                price_key = 'write_price'
            elif any(pattern in usage_type for pattern in ['get', 'select', 'head', 'retrieve', 'requests-tier2', '-get-', '-select-']):
                price_key = 'read_price'
        
        # Check group description as fallback
        if not price_key and group:
            group_desc = attributes.get('groupDescription', '').lower()
            if any(op in group_desc for op in ['put', 'post', 'copy', 'delete', 'list', 'upload']):
                price_key = 'write_price'
            elif any(op in group_desc for op in ['get', 'head', 'select', 'retrieve']):
                price_key = 'read_price'
        
        if not price_key:
            logger.debug(f"Could not determine operation type for SKU {price_item.get('product', {}).get('sku')} - operation: {operation}, usage_type: {usage_type}")
            return

        # Log the price assignment for debugging
        sku = price_item.get('product', {}).get('sku')
        logger.debug(f"Setting {price_key} = ${price_per_million:.6f} for {continent} - {conversion_info} - SKU: {sku}")

        # Determine which storage classes this applies to based on usage type
        target_storage_classes = []
        
        # Map based on usage type patterns with more precise matching
        if any(pattern in usage_type for pattern in ['sia', 'infrequent']):
            target_storage_classes.append('Infrequent Access')
        elif any(pattern in usage_type for pattern in ['zia', 'onezone']):
            target_storage_classes.append('Infrequent Access')  # One Zone IA
        elif any(pattern in usage_type for pattern in ['gir', 'glacier-ir', 'instantretrieval']):
            target_storage_classes.append('Archive Instant Retrieval')
        elif any(pattern in usage_type for pattern in ['gda', 'glacier-da', 'deep-archive', 'deeparchive']):
            target_storage_classes.append('Archive')
        elif 'glacier' in usage_type and 'gir' not in usage_type and 'gda' not in usage_type:
            target_storage_classes.append('Archive')
        elif any(pattern in usage_type for pattern in ['int', 'intelligent']):
            target_storage_classes.append('Intelligent-Tiering')
        elif any(pattern in usage_type for pattern in ['standard', 'std']):
            target_storage_classes.append('General Purpose')
        elif any(pattern in usage_type for pattern in ['express', 'xz']):
            target_storage_classes.append('High Performance')
        else:
            # Default: apply to all storage classes in this region
            target_storage_classes = ['General Purpose', 'Infrequent Access', 'Archive Instant Retrieval', 
                                    'Archive', 'Intelligent-Tiering', 'Non-Critical Data', 'High Performance']

        # Apply the price to matching storage records
        matches_found = 0
        for storage_class in target_storage_classes:
            key = (continent, storage_class)
            if key in self.storage_records_map:
                current_price = self.storage_records_map[key][price_key]
                if current_price is None or abs(current_price - price_per_million) > 0.000001:  # Only update if different
                    self.storage_records_map[key][price_key] = price_per_million
                    matches_found += 1
                    logger.debug(f"Updated {price_key} for {continent}-{storage_class}: ${price_per_million:.6f}")
        
        # If no specific matches, apply to General Purpose as fallback
        if matches_found == 0:
            fallback_key = (continent, 'General Purpose')
            if fallback_key in self.storage_records_map:
                current_price = self.storage_records_map[fallback_key][price_key]
                if current_price is None:
                    self.storage_records_map[fallback_key][price_key] = price_per_million
                    logger.debug(f"Applied {price_key} to fallback {continent}-General Purpose: ${price_per_million:.6f}")

    def process_data_transfer_item(self, price_item: Dict[str, Any]):
        # Data transfer pricing (egress) is no longer tracked per user requirements
        return

    def process_fee_item(self, price_item: Dict[str, Any]):
        attributes = price_item.get('product', {}).get('attributes', {})
        on_demand_terms = self.get_on_demand_terms(price_item)
        if not on_demand_terms:
            return

        fee_price = 0
        for term in on_demand_terms.values():
            price = self.extract_price(term.get("priceDimensions", {}))
            if price is not None and price > 0:
                # Round to 6 decimal places to avoid scientific notation and maintain consistency
                fee_price = round(price, 6)
                break
        
        if fee_price == 0:
            return

        location = attributes.get('location')
        region_code = AWS_LOCATION_TO_REGION_CODE.get(location)
        continent = self.get_continent_from_region(region_code)
        if not continent: return

        # This is a broad update - apply fee to ALL storage types in the continent
        for key, record in self.storage_records_map.items():
            if key[0] == continent:
                if record['flat_item_price'] is None:
                    record['flat_item_price'] = fee_price

    def append_batch_to_csv(self, data_batch: List[Dict[str, Any]]) -> bool:
        if not data_batch:
            return True
        
        records_to_write = data_batch
        if self.max_records:
            remaining_slots = self.max_records - self.total_records
            if remaining_slots <= 0: return False
            if len(data_batch) > remaining_slots:
                records_to_write = data_batch[:remaining_slots]
        
        # Format numeric fields to avoid scientific notation
        formatted_records = []
        for record in records_to_write:
            formatted_record = record.copy()
            # Format price fields to ensure no scientific notation
            for price_field in ['capacity_price', 'read_price', 'write_price', 'flat_item_price']:
                if formatted_record.get(price_field) is not None:
                    try:
                        # Convert to float and format with up to 6 decimal places, removing trailing zeros
                        price_value = float(formatted_record[price_field])
                        formatted_record[price_field] = f"{price_value:.6f}".rstrip('0').rstrip('.')
                    except (ValueError, TypeError):
                        # Keep original value if formatting fails
                        pass
            formatted_records.append(formatted_record)
            
        with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.csv_columns, quoting=csv.QUOTE_ALL)
            writer.writerows(formatted_records)
        
        self.total_records += len(records_to_write)
        
        if self.max_records and self.total_records >= self.max_records:
            logger.info(f"Reached max record limit of {self.max_records}.")
            return False
            
        return True

    def write_progress_summary(self):
        """Writes a summary of the extraction process to a text file."""
        # For debugging the counters
        logger.info(f"Final counts: Pages={self.pages_processed}, Items={self.items_seen}")
        
        summary_content = (
            f"AWS S3 Storage Pricing Extraction Summary\n"
            f"=============================================\n"
            f"Last Updated: {datetime.now()}\n"
            f"Pages processed: {self.pages_processed}\n"
            f"Items seen: {self.items_seen}\n"
            f"Items filtered: {self.items_filtered_out}\n"
            f"Items with errors: {self.items_with_errors}\n"
            f"Valid records found: {self.total_records}\n"
            f"CSV file: {self.csv_file_path}\n\n"
            f"=========================\n"
            f"No OnDemand terms: {self.filtering_reasons['no_on_demand_terms']}\n"
            f"Unmapped regions: {len(self.unmapped_regions)} ({sum(self.unmapped_regions.values())} items)\n"
            f"No valid pricing: {self.filtering_reasons['no_valid_pricing']}\n"
        )
        
        # Add detailed unmapped regions information
        if self.unmapped_regions:
            summary_content += f"\nUnmapped Regions Details:\n"
            summary_content += f"========================\n"
            for location, count in sorted(self.unmapped_regions.items(), key=lambda x: x[1], reverse=True):
                summary_content += f"{location}: {count} items\n"
        
        try:
            with open(self.summary_file_path, 'w') as f:
                f.write(summary_content)
            logger.info(f"Progress summary written to {self.summary_file_path}")
            
            # Also log the unmapped regions to console for debugging
            if self.unmapped_regions:
                logger.warning("Unmapped regions found:")
                for location, count in sorted(self.unmapped_regions.items(), key=lambda x: x[1], reverse=True):
                    logger.warning(f"  {location}: {count} items")
        except IOError as e:
            logger.error(f"Error writing summary file: {e}")

    def fetch_all_storage_pricing(self):
        logger.info("Starting AWS S3 storage pricing data extraction...")
        
        paginator = self.pricing_client.get_paginator('get_products')
        
        all_price_items = []
        product_families = ["Storage", "API Request", "Data Transfer", "Fee"]

        for family in product_families:
            logger.info(f"Fetching data for product family: {family}...")
            try:
                pages = paginator.paginate(
                    ServiceCode='AmazonS3',
                    Filters=[{'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': family}]
                )

                for page in pages:
                    self.pages_processed += 1
                    price_list = page.get('PriceList', [])
                    
                    if self.max_records and len(all_price_items) >= self.max_records:
                        break

                    for item_str in price_list:
                        self.items_seen += 1
                        try:
                            price_item = json.loads(item_str)
                            all_price_items.append(price_item)
                        except json.JSONDecodeError:
                            logger.warning("Failed to decode JSON price item.")
                            self.items_with_errors += 1
                        
                        if self.max_records and len(all_price_items) >= self.max_records:
                            break
            except Exception as e:
                logger.error(f"Failed to fetch pricing for {family}: {e}")
            
            if self.max_records and len(all_price_items) >= self.max_records:
                logger.info(f"Reached max record limit of {self.max_records}. "
                            f"Processing {len(all_price_items)} records.")
                break

        logger.info(f"Collected {len(all_price_items)} price items in total. Processing...")

        # Create a set to track which records have been modified to avoid duplicate processing
        processed_records = set()

        # First pass: process storage items to create base records
        for item in all_price_items:
            if item.get('product', {}).get('productFamily') == 'Storage':
                self.process_storage_item(item)
        
        # Second pass: enrich with API, data transfer, and fee data
        for item in all_price_items:
            family = item.get('product', {}).get('productFamily')
            sku = item.get('product', {}).get('sku')

            if sku in processed_records: continue
            
            if family == 'API Request':
                self.process_api_request_item(item)
                processed_records.add(sku)
            elif family == 'Data Transfer':
                self.process_data_transfer_item(item)
                processed_records.add(sku)
            elif family == 'Fee':
                self.process_fee_item(item)
                processed_records.add(sku)
        
        # Final step: write all the processed records to the CSV file
        if self.storage_records_map:
            logger.info(f"Writing {len(self.storage_records_map)} final records to CSV...")
            self.append_batch_to_csv(list(self.storage_records_map.values()))
        else:
            logger.warning("No storage records were generated.")
            
        self.write_progress_summary()
        logger.info("Data extraction completed!")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract AWS S3 storage pricing data.')
    parser.add_argument('--max-records', type=int, help='Max records to process.')
    args = parser.parse_args()
    
    try:
        extractor = AWSStoragePricingExtractor(max_records=args.max_records)
        extractor.fetch_all_storage_pricing()
        logger.info("Script completed successfully!")
    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        return 1
    return 0

if __name__ == "__main__":
    exit(main()) 