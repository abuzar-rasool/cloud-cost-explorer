#!/usr/bin/env python3
"""
AWS On-Demand VM Pricing Data Extraction Script

This script fetches all AWS EC2 on-demand compute pricing data from the AWS Pricing API
and saves it to a single CSV file. Each time the script runs, new data is appended.

The script extracts the following columns:
- vm_name: VM instance type name (string)
- provider_name: Cloud provider name - AWS (enum)
- virtual_cpu_count: Number of virtual CPUs (int)
- memory_gb: Memory in GiB (double)
- cpu_arch: CPU architecture (string)
- price_per_hour_usd: Price per hour in USD (double)
- gpu_count: Number of GPUs (int)
- gpu_name: GPU name/type (string)
- gpu_memory: GPU memory in GiB (double)
- os_type: Operating system type - WINDOWS, LINUX, OTHER (enum)
- region: AWS region mapped to continent - north_america, south_america, europe, asia, africa, oceania, antarctica (enum)
- other_details: All VM information from pricing API and EC2 API in JSON format (string)

USAGE:
    python3 scripts/aws_ondemand_vm_pricing.py [--max-records N]
    
    Options:
        --max-records N    Limit processing to N records (default: no limit)

REQUIREMENTS:
    - AWS credentials configured (via AWS CLI, environment variables, or IAM role)
    - boto3 library installed
    - Internet connection for AWS Pricing API and EC2 API access
    - IAM permissions: pricing:GetProducts, ec2:DescribeInstanceTypes

OUTPUT:
    - Timestamped CSV file: data/aws_ondemand_vm_pricing_YYYYMMDD_HHMMSS.csv
    - New file created each time the script runs with current timestamp
    - Progress summaries written every 100 pages

FILTERS APPLIED:
    - API-level filter: productFamily = "Compute Instance"
    - Post-processing filter: Only OnDemand pricing terms
    - Post-processing filter: Only items with USD pricing available
    - Post-processing filter: Only items with non-zero USD pricing (price > 0.0)
    - Post-processing filter: Only items with mapped AWS regions
    - No specific memory or CPU filtering (gets all data)
    
ASSUMPTIONS:
    - Items without USD pricing are considered invalid and filtered out
    - Items with 0.0 USD pricing are considered invalid and filtered out
    - Items with unmapped regions are considered invalid and filtered out
    - All filtered cases are treated as normal filtering, not errors
    - Unmapped regions are tracked in the extraction summary for review
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
    'mx-central-1': 'north_america',
    'us-gov-west-1': 'north_america',
    'us-gov-east-1': 'north_america',
    
    # North America - US Local Zones
    'us-west-2-lax-1': 'north_america',    # Los Angeles
    'us-east-1-dfw-1': 'north_america',    # Dallas
    'us-east-1-nyc-1': 'north_america',    # New York
    'us-east-1-chi-1': 'north_america',    # Chicago
    'us-west-2-phx-1': 'north_america',    # Phoenix
    'us-east-1-phl-1': 'north_america',    # Philadelphia
    'us-east-1-atl-1': 'north_america',    # Atlanta
    'us-east-1-mia-1': 'north_america',    # Miami
    'us-east-1-mci-1': 'north_america',    # Kansas City
    'us-west-2-den-1': 'north_america',    # Denver
    'us-east-1-iah-1': 'north_america',    # Houston
    'us-east-1-bos-1': 'north_america',    # Boston
    'us-west-2-pdx-1': 'north_america',    # Portland
    'us-east-1-msp-1': 'north_america',    # Minneapolis
    'us-west-2-hnl-1': 'north_america',    # Honolulu
    'us-east-1-qro-1': 'north_america',    # Querétaro, Mexico
    
    # North America - US Wavelength Zones
    'us-east-1-wl1-was1': 'north_america', # Washington
    'us-east-1-wl1-msp1': 'north_america', # Minneapolis
    'us-east-1-wl1-tpa1': 'north_america', # Tampa
    'us-east-1-wl1-foe1': 'north_america', # Wavelength zone
    'us-east-1-wl1-bna1': 'north_america', # Nashville
    'us-west-2-wl1-las1': 'north_america', # Las Vegas
    'us-east-1-wl1-clt1': 'north_america', # Charlotte
    
    # South America
    'sa-east-1': 'south_america',
    'us-east-1-scl-1': 'south_america',    # Santiago, Chile (Local Zone)
    'us-east-1-bue-1': 'south_america',    # Buenos Aires, Argentina (Local Zone)
    
    # Europe
    'eu-central-1': 'europe',
    'eu-central-2': 'europe',
    'eu-west-1': 'europe',
    'eu-west-2': 'europe',
    'eu-west-3': 'europe',
    'eu-south-1': 'europe',
    'eu-south-2': 'europe',
    'eu-north-1': 'europe',
    
    # Europe - Local Zones and Wavelength Zones
    'eu-central-1-waw-1': 'europe',        # Warsaw, Poland
    'eu-central-1-wl1-dtm1': 'europe',     # Dortmund, Germany (Wavelength)
    'eu-north-1-hel-1': 'europe',          # Helsinki, Finland
    'eu-west-2-wl2-man1': 'europe',        # Manchester, UK (Wavelength)
    
    # Asia
    'ap-east-1': 'asia',
    'ap-east-2': 'asia',           # Asia Pacific East 2
    'ap-south-1': 'asia',
    'ap-south-2': 'asia',
    'ap-northeast-1': 'asia',
    'ap-northeast-2': 'asia',
    'ap-northeast-3': 'asia',
    'ap-southeast-1': 'asia',
    'ap-southeast-3': 'asia',
    'ap-southeast-5': 'asia',
    'ap-southeast-7': 'asia',
    'il-central-1': 'asia',
    'me-south-1': 'asia',
    'me-central-1': 'asia',
    'cn-north-1': 'asia',        # China (Beijing)
    'cn-northwest-1': 'asia',    # China (Ningxia)
    
    # Asia - Local Zones and Wavelength Zones
    'ap-south-1-ccu-1': 'asia',            # Kolkata, India
    'ap-southeast-1-mnl-1': 'asia',        # Manila, Philippines
    'ap-northeast-2-wl1-cjj1': 'asia',     # South Korea (Wavelength)
    'ap-northeast-1-tpe-1': 'asia',        # Taipei, Taiwan
    'cn-north-1-pkx-1': 'asia',            # Beijing, China
    'me-south-1-mct-1': 'asia',            # Muscat, Oman
    
    # Oceania
    'ap-southeast-2': 'oceania',
    'ap-southeast-4': 'oceania',
    'ap-southeast-2-akl-1': 'oceania',     # Auckland, New Zealand
    
    # Africa
    'af-south-1': 'africa',
    'af-south-1-los-1': 'africa',          # Lagos, Nigeria (Local Zone)
}

class AWSComputePricingExtractor:
    def __init__(self, max_records: Optional[int] = None):
        """Initialize the AWS pricing client.
        
        Args:
            max_records: Maximum number of valid records to process. If None, process all records.
        """
        self.pricing_client = boto3.client("pricing", region_name="us-east-1")
        self.ec2_client = boto3.client("ec2", region_name="us-east-1")
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Create timestamped CSV file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_file_path = self.data_dir / f"aws_ondemand_vm_pricing_{timestamp}.csv"
        
        # Single summary file path (no timestamps)
        self.summary_file_path = self.data_dir / "extraction_summary.txt"
        
        # CSV columns
        self.csv_columns = [
            'vm_name',
            'provider_name',
            'virtual_cpu_count',
            'memory_gb', 
            'cpu_arch',
            'price_per_hour_usd',
            'gpu_count',
            'gpu_name',
            'gpu_memory',
            'os_type',
            'region',
            'other_details'
        ]
        
        # Processing limits and batch configuration
        self.max_records = max_records
        self.batch_size = 200
        self.total_records = 0
        self.pages_processed = 0
        self.items_seen = 0
        self.items_filtered_out = 0
        self.items_with_errors = 0
        self.error_count = 0  # Track errors without storing full data
        self.unmapped_regions = {}  # Track unmapped regions and their counts
        
        # Compile regex patterns once for performance
        self.memory_pattern = re.compile(r'([\d.]+)\s*GiB')
        self.gpu_pattern = re.compile(r'(\d+)\s*x?\s*(.+)')
        self.linux_os_pattern = re.compile(r'linux|rhel|sles|ubuntu|amazon', re.IGNORECASE)
        self.windows_os_pattern = re.compile(r'windows', re.IGNORECASE)
        
        # Regex patterns for AWS region zone types
        self.local_zone_pattern = re.compile(r'^([a-z0-9-]+)-[a-z]{3,4}-\d+$')  # e.g., us-west-2-sea-1, ap-southeast-2-per-1
        self.wavelength_zone_pattern = re.compile(r'^([a-z0-9-]+)-wl\d+(?:-[a-z0-9]+)?$')  # e.g., us-east-1-wl1, eu-west-3-wl1-cmn1
        
        # Cache for instance type details to avoid repeated API calls
        self.instance_type_cache = {}
        
        # Initialize new timestamped CSV file with headers
        logger.info(f"Creating new timestamped CSV file: {self.csv_file_path}")
        with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.csv_columns, quoting=csv.QUOTE_ALL)
            writer.writeheader()
        
        # Log processing limits
        if self.max_records:
            logger.info(f"Processing limit: {self.max_records} records")
        else:
            logger.info("Processing limit: No limit (all records)")
        
        logger.info("Using dynamic GPU information extraction via EC2 API")
        
    def get_continent_from_region(self, region_code: str) -> Optional[str]:
        """Map AWS region code to continent with support for Local Zones and Wavelength Zones.
        
        This function handles:
        1. Direct mapping for standard regions
        2. Local zones (e.g., us-west-2-sea-1 -> us-west-2)
        3. Wavelength zones (e.g., us-east-1-wl1 -> us-east-1, eu-west-3-wl1-cmn1 -> eu-west-3)
        
        Args:
            region_code: AWS region code
            
        Returns:
            Continent name or None if unmapped
        """
        if not region_code:
            return None
            
        # First try direct mapping for standard regions
        continent = AWS_REGION_TO_CONTINENT.get(region_code)
        if continent:
            return continent
        
        # Try to extract base region from Local Zone pattern (e.g., us-west-2-sea-1)
        local_zone_match = self.local_zone_pattern.match(region_code)
        if local_zone_match:
            base_region = local_zone_match.group(1)
            return AWS_REGION_TO_CONTINENT.get(base_region)
        
        # Try to extract base region from Wavelength Zone pattern (e.g., us-east-1-wl1, eu-west-3-wl1-cmn1)
        wavelength_zone_match = self.wavelength_zone_pattern.match(region_code)
        if wavelength_zone_match:
            base_region = wavelength_zone_match.group(1)
            return AWS_REGION_TO_CONTINENT.get(base_region)
        
        # No mapping found
        return None
        
    def map_os_type(self, os_string: str) -> str:
        """Map AWS OS string to standardized OS type."""
        if not os_string:
            return "OTHER"
        
        if self.windows_os_pattern.search(os_string):
            return "WINDOWS"
        elif self.linux_os_pattern.search(os_string):
            return "LINUX"
        else:
            return "OTHER"
    
    def extract_memory_gib(self, memory_string: str) -> float:
        """Extract memory in GiB from AWS memory string."""
        if not memory_string:
            return 0.0
        
        match = self.memory_pattern.search(memory_string)
        if match:
            return float(match.group(1))
        return 0.0
    
    def get_instance_type_details(self, instance_type: str) -> Dict[str, Any]:
        """Get instance type details from EC2 API with caching."""
        if instance_type in self.instance_type_cache:
            return self.instance_type_cache[instance_type]
        
        try:
            response = self.ec2_client.describe_instance_types(
                InstanceTypes=[instance_type]
            )
            
            if response['InstanceTypes']:
                details = response['InstanceTypes'][0]
                
                # Debug log the full response structure for GPU instances
                if 'GpuInfo' in details and len(self.instance_type_cache) <= 3:
                    logger.debug(f"Full EC2 response for {instance_type}: {json.dumps(details, indent=2, default=str)}")
                
                self.instance_type_cache[instance_type] = details
                return details
            else:
                self.instance_type_cache[instance_type] = {}
                return {}
                
        except Exception as e:
            logger.debug(f"Failed to get instance type details for {instance_type}: {e}")
            self.instance_type_cache[instance_type] = {}
            return {}
    
    def extract_gpu_info(self, attributes: Dict[str, Any]) -> tuple:
        """Extract GPU count, name, and memory from attributes using dynamic EC2 API."""
        gpu_count = 0
        gpu_name = ""
        gpu_memory = 0.0
        
        instance_type = attributes.get("instanceType", "")
        
        # First, check for GPU-related attributes in pricing data
        gpu_info = attributes.get("gpu", "")
        if gpu_info and gpu_info not in ("NA", ""):
            gpu_match = self.gpu_pattern.search(gpu_info)
            if gpu_match:
                gpu_count = int(gpu_match.group(1))
                gpu_name = gpu_match.group(2).strip()
            else:
                # If gpu field is just a number (like "1"), treat it as count, not name
                try:
                    gpu_count = int(gpu_info)
                    gpu_name = ""  # Will be filled by EC2 API lookup
                except ValueError:
                    # If it's not a number, treat as name
                    gpu_count = 1
                    gpu_name = gpu_info
        
        # Check GPU memory from pricing data
        gpu_mem = attributes.get("gpuMemory", "")
        if gpu_mem and gpu_mem not in ("NA", ""):
            # Extract numeric value from GPU memory string (e.g., "16 GiB" -> 16.0)
            gpu_mem_match = self.memory_pattern.search(gpu_mem)
            if gpu_mem_match:
                gpu_memory = float(gpu_mem_match.group(1))
            else:
                # Try to extract just numbers if no GiB pattern
                number_match = re.search(r'([\d.]+)', gpu_mem)
                if number_match:
                    gpu_memory = float(number_match.group(1))
        
        # Get EC2 API details for meta information and GPU fallback
        instance_details = {}
        if instance_type:
            instance_details = self.get_instance_type_details(instance_type)
            
            # If no GPU info found in pricing data, use EC2 API for dynamic lookup
            if not gpu_name and 'GpuInfo' in instance_details:
                gpu_info_details = instance_details['GpuInfo']
                
                if 'Gpus' in gpu_info_details and gpu_info_details['Gpus']:
                    gpu_spec = gpu_info_details['Gpus'][0]  # Take first GPU spec
                    
                    # Get GPU count
                    gpu_count = gpu_spec.get('Count', 1)
                    
                    # Get GPU name - ensure it's a string
                    raw_gpu_name = gpu_spec.get('Name', '')
                    if raw_gpu_name:
                        gpu_name = str(raw_gpu_name)
                    else:
                        # Fallback: try Manufacturer + Model if Name is not available
                        manufacturer = gpu_spec.get('Manufacturer', '')
                        if manufacturer:
                            gpu_name = str(manufacturer)
                        
                        # Check if there's any other identifying field
                        for key in ['Model', 'Type', 'Description']:
                            if key in gpu_spec and gpu_spec[key]:
                                if gpu_name:
                                    gpu_name += f" {gpu_spec[key]}"
                                else:
                                    gpu_name = str(gpu_spec[key])
                                break
                    
                    # Get GPU memory (convert from MiB to GiB)
                    gpu_memory_mib = gpu_spec.get('MemoryInfo', {}).get('SizeInMiB', 0)
                    if gpu_memory_mib:
                        gpu_memory = round(gpu_memory_mib / 1024.0, 2)  # Convert MiB to GiB
            
        return gpu_count, gpu_name, gpu_memory, instance_details
    
    def process_price_item(self, price_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single price item and extract relevant data."""
        try:
            self.items_seen += 1
            
            product = price_item.get("product", {})
            attributes = product.get("attributes", {})
            
            # Check for OnDemand pricing terms
            terms = price_item.get("terms", {})
            on_demand_terms = terms.get("OnDemand", {})
            
            if not on_demand_terms:
                self.items_filtered_out += 1
                return None
            
            # Extract basic compute specs with optimized attribute access
            vm_name = attributes.get("instanceType", "")
            provider_name = "AWS"
            vcpu = int(attributes.get("vcpu", 0))
            memory_gib = self.extract_memory_gib(attributes.get("memory", ""))
            cpu_arch = attributes.get("processorArchitecture", "")
            
            # Map region to continent - filter out unmapped regions
            region_code = attributes.get("regionCode", "")
            continent = self.get_continent_from_region(region_code)
            
            # If region is not mapped, track it and filter out the record
            if continent is None:
                self.items_filtered_out += 1
                # Track unmapped regions for summary
                if region_code in self.unmapped_regions:
                    self.unmapped_regions[region_code] += 1
                else:
                    self.unmapped_regions[region_code] = 1
                return None
            
            # Map OS type
            os_type = self.map_os_type(attributes.get("operatingSystem", ""))
            
            # Extract GPU information and get EC2 instance details
            gpu_count, gpu_name, gpu_memory, ec2_instance_details = self.extract_gpu_info(attributes)
            
            # Get pricing information from OnDemand terms
            price_per_hour = 0.0
            
            for term in on_demand_terms.values():
                price_dimensions = term.get("priceDimensions", {})
                for price_dimension in price_dimensions.values():
                    if price_dimension.get("unit") == "Hrs":
                        price_per_unit = price_dimension.get("pricePerUnit", {})
                        if "USD" not in price_per_unit:
                            self.items_filtered_out += 1
                            return None
                        
                        try:
                            price_per_hour = float(price_per_unit["USD"])
                        except (ValueError, TypeError):
                            self.items_filtered_out += 1
                            return None
                        break
                if price_per_hour > 0:
                    break
            
            # Filter out items with zero or no valid USD pricing
            if price_per_hour <= 0.0:
                self.items_filtered_out += 1
                return None            
            # Create comprehensive meta information combining pricing and EC2 API data
            meta_info = {
                'pricing_api': attributes,  # All pricing API attributes
                'ec2_api': ec2_instance_details  # All EC2 API instance details
            }
            # Stringify JSON - let CSV writer handle the escaping automatically
            meta_json_string = json.dumps(meta_info, separators=(',', ':'), default=str, ensure_ascii=True)
            
            return {
                'vm_name': vm_name,
                'provider_name': provider_name,
                'virtual_cpu_count': vcpu,
                'memory_gb': memory_gib,
                'cpu_arch': cpu_arch,
                'price_per_hour_usd': price_per_hour,
                'gpu_count': gpu_count,
                'gpu_name': gpu_name,
                'gpu_memory': gpu_memory,
                'os_type': os_type,
                'region': continent,
                'other_details': meta_json_string
            }
            
        except Exception as e:
            self.items_with_errors += 1
            self.error_count += 1
            return None
    
    def append_batch_to_csv(self, data_batch: List[Dict[str, Any]]) -> bool:
        """Append a batch of data to the timestamped CSV file.
        
        Returns:
            bool: True if processing should continue, False if max_records limit reached
        """
        if not data_batch:
            return True
        
        # Check if we need to truncate the batch to stay within limits
        records_to_write = data_batch
        if self.max_records:
            remaining_slots = self.max_records - self.total_records
            if remaining_slots <= 0:
                return False  # Already at limit
            elif len(data_batch) > remaining_slots:
                records_to_write = data_batch[:remaining_slots]
                logger.info(f"Truncating batch to {len(records_to_write)} records to stay within limit of {self.max_records}")
            
        with open(self.csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.csv_columns, quoting=csv.QUOTE_ALL)
            writer.writerows(records_to_write)
        
        self.total_records += len(records_to_write)
        
        # Check if we've reached the limit
        if self.max_records and self.total_records >= self.max_records:
            logger.info(f"Reached maximum record limit of {self.max_records}. Stopping processing.")
            return False
        
        return True
    
    def write_progress_summary(self):
        """Write a progress summary to a single file that gets updated."""
        with open(self.summary_file_path, 'w') as f:
            f.write(f"AWS Pricing Data Extraction Summary\n")
            f.write(f"=" * 40 + "\n")
            f.write(f"Last Updated: {datetime.now()}\n")
            f.write(f"Pages processed: {self.pages_processed}\n")
            f.write(f"Items seen: {self.items_seen}\n")
            f.write(f"Items filtered out: {self.items_filtered_out}\n")
            f.write(f"Items with errors: {self.items_with_errors}\n")
            f.write(f"Valid records found: {self.total_records}\n")
            f.write(f"CSV file: {self.csv_file_path}\n")
            
            # Add unmapped regions details
            if self.unmapped_regions:
                f.write(f"\nUnmapped Regions (Filtered Out):\n")
                f.write(f"=" * 35 + "\n")
                f.write(f"Total unmapped region instances: {sum(self.unmapped_regions.values())}\n")
                f.write(f"Unique unmapped regions: {len(self.unmapped_regions)}\n\n")
                
                # Sort by count (descending) for better readability
                sorted_regions = sorted(self.unmapped_regions.items(), key=lambda x: x[1], reverse=True)
                for region, count in sorted_regions:
                    f.write(f"  {region}: {count} instances\n")
    
    def fetch_all_compute_pricing(self):
        """Fetch all AWS compute pricing data and save to a timestamped CSV file."""
        logger.info("Starting AWS compute pricing data extraction...")
        
        # Filter for EC2 Compute Instance product family at API level
        filters = [
            {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Compute Instance"},
        ]
        
        service_code = "AmazonEC2"
        logger.info(f"Output file: {self.csv_file_path}")
        logger.info(f"Batch processing size: {self.batch_size} records")
        
        try:
            paginator = self.pricing_client.get_paginator("get_products")
            page_iterator = paginator.paginate(
                ServiceCode=service_code,
                Filters=filters
            )
            
            current_batch = []
            should_continue = True
            
            for page_num, page in enumerate(page_iterator, 1):
                if not should_continue:
                    break
                    
                self.pages_processed = page_num
                
                page_valid_items = 0
                
                # Process all items in the page
                for price_item_json in page["PriceList"]:
                    if not should_continue:
                        break
                        
                    # Parse JSON once and reuse
                    try:
                        price_item = json.loads(price_item_json)
                        processed_item = self.process_price_item(price_item)
                        
                        if processed_item:
                            current_batch.append(processed_item)
                            page_valid_items += 1
                            
                            # Write batch when it reaches the desired size
                            if len(current_batch) >= self.batch_size:
                                should_continue = self.append_batch_to_csv(current_batch)
                                current_batch = []
                                if not should_continue:
                                    break
                    except json.JSONDecodeError:
                        self.items_with_errors += 1
                        continue
                
                # Log progress every 25 pages
                if page_num % 25 == 0:
                    logger.info(f"Page {page_num}: {page_valid_items} valid items, {self.total_records} total records")
                
                # Write batch after every 20 pages if not empty
                if page_num % 20 == 0 and current_batch and should_continue:
                    should_continue = self.append_batch_to_csv(current_batch)
                    current_batch = []
                
                # Write progress summary every 100 pages
                if page_num % 100 == 0:
                    self.write_progress_summary()
            
            # Write remaining data if any
            if current_batch and should_continue:
                self.append_batch_to_csv(current_batch)
            
            # Final summary
            self.write_progress_summary()
            
            logger.info(f"Data extraction completed!")
            logger.info(f"Total records: {self.total_records}")
            logger.info(f"Output file: {self.csv_file_path}")
            
        except Exception as e:
            logger.error(f"Error during data extraction: {e}")
            raise

def main():
    """Main function to run the pricing data extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract AWS EC2 on-demand pricing data')
    parser.add_argument('--max-records', type=int, default=None, 
                       help='Maximum number of records to process (default: no limit)')
    
    args = parser.parse_args()
    
    try:
        logger.info("Initializing AWS Compute Pricing Extractor...")
        extractor = AWSComputePricingExtractor(max_records=args.max_records)
        
        logger.info("Starting optimized data extraction process...")
        extractor.fetch_all_compute_pricing()
        
        logger.info("Script completed successfully!")
        
    except Exception as e:
        logger.error(f"Script execution failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
