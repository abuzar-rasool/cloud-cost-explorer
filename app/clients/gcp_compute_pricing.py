import csv
import json
import logging
import os
import re
import requests
import time
from typing import Dict, List, Any, Optional
from google.auth.transport.requests import Request
import google.auth
from google.cloud import compute_v1

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GCPComputePricingFetcher:
    """Client for fetching Google Cloud Platform Compute Engine pricing using real-time API data."""

    # Region to continent mapping
    REGION_TO_CONTINENT = {
        'us-': 'north_america',
        'northamerica-': 'north_america',
        'southamerica-': 'south_america',
        'europe-': 'europe',
        'asia-': 'asia',
        'australia-': 'oceania',
        'africa-': 'africa',
        'me-': 'middle_east'
    }

    def __init__(self):
        """Initialize the GCP compute pricing client."""
        self.provider = "GCP"
        try:
            self.credentials, self.project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
            self.credentials.refresh(Request())
            logger.info(f"Authenticated with Google Cloud for project: {self.project}")
            self.authenticated = True
        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            logger.info("Will use unauthenticated access for pricing API")
            self.authenticated = False
            self.project = None
            
        self.compute_service_id = "6F81-5844-456A"  # Compute Engine service ID
        self.pricing_url = f"https://cloudbilling.googleapis.com/v1/services/{self.compute_service_id}/skus"

    def _region_to_continent(self, region: str) -> str:
        """Map a GCP region to its continent."""
        for prefix, continent in self.REGION_TO_CONTINENT.items():
            if region.startswith(prefix):
                return continent
        return "other"

    def fetch_pricing_data(self) -> List[Dict[str, Any]]:
        """Fetch ALL GCP Compute Engine pricing data with minimal filtering."""
        logger.info("Starting to fetch ALL GCP pricing data with minimal filtering")
        
        # Fetch ALL SKUs from Billing API
        logger.info("Fetching ALL SKUs from Cloud Billing API")
        skus = self._fetch_all_skus()
        
        if not skus:
            logger.error("Failed to fetch SKUs from API")
            return []
            
        logger.info(f"Successfully fetched {len(skus)} SKUs from Billing API")
        logger.info(f"Processing ALL SKUs without any filtering")
        
        # Process ALL SKUs with minimal filtering - only require a valid price
        all_pricing_data = []
        
        processed_count = 0
        skipped_count = 0
        os_stats = {"windows": 0, "linux": 0, "other": 0}
        service_names = set()
        
        for sku in skus:
            try:
                # Extract basic information
                description = sku.get("description", "")
                category = sku.get("category", {})
                resource_family = category.get("resourceFamily", "")
                resource_group = category.get("resourceGroup", "")
                usage_type = category.get("usageType", "")
                service_name = sku.get("serviceName", "")
                service_names.add(service_name)
                
                # Get pricing - ONLY filter for SKUs with no price
                price = self._extract_price(sku)
                if price is None or price <= 0:
                    skipped_count += 1
                    continue
                    
                # Get regions - ONLY filter for SKUs with no regions
                service_regions = sku.get("serviceRegions", [])
                if not service_regions:
                    skipped_count += 1
                    continue
                
                # Determine OS type
                if "windows" in description.lower():
                    os_type = "WINDOWS"
                    os_stats["windows"] += 1
                elif any(os_name in description.lower() for os_name in ["rhel", "suse", "ubuntu", "centos", "debian"]):
                    os_type = "LINUX"
                    os_stats["linux"] += 1
                else:
                    os_type = "LINUX"  # Default to Linux
                    os_stats["linux"] += 1
                
                # Extract CPU count and memory if possible
                cpu_count = self._extract_cpu_count(description)
                memory_gb = self._extract_memory_gb(description)
                
                # Extract GPU info if present
                gpu_info = self._extract_gpu_info(description)
                
                # Create entries for each region
                for region in service_regions:
                    if not region:
                        continue
                        
                    continent = self._region_to_continent(region)
                    
                    # Create VM name from SKU info - no filtering
                    if "instance" in description.lower():
                        vm_name = self._extract_vm_name(description)
                    else:
                        # Create generic name using resource family and group
                        sanitized_family = resource_family.lower().replace(" ", "-")
                        sanitized_group = resource_group.lower().replace(" ", "-")
                        vm_name = f"{sanitized_family}-{sanitized_group}"
                        if not vm_name or vm_name == "-":
                            vm_name = f"compute-resource-{sku.get('skuId', '')[-8:]}"
                    
                    # Create pricing entry - include ALL SKUs with pricing
                    pricing_entry = {
                        "vm_name": vm_name,
                        "provider_name": self.provider,
                        "virtual_cpu_count": cpu_count,
                        "memory_gb": round(memory_gb, 2) if memory_gb else 0.0,
                        "cpu_arch": "x86_64",  # Default
                        "price_per_hour_usd": round(price, 6),
                        "gpu_count": gpu_info.get("gpu_count", 0),
                        "gpu_name": gpu_info.get("gpu_type", ""),
                        "gpu_memory": round(gpu_info.get("gpu_memory", 0.0), 1),
                        "os_type": os_type,
                        "region": continent,
                        "other_details": json.dumps({
                            "gcp_region": region,
                            "description": description[:200],
                            "resource_family": resource_family,
                            "resource_group": resource_group,
                            "usage_type": usage_type,
                            "service_name": service_name,
                            "sku_id": sku.get("skuId", "")
                        })
                    }
                    
                    all_pricing_data.append(pricing_entry)
                    processed_count += 1
                    
            except Exception as e:
                logger.warning(f"Error processing SKU {sku.get('skuId', 'unknown')}: {e}")
                skipped_count += 1
                continue
        
        logger.info(f"Found service names: {list(service_names)}")
        logger.info(f"Processed {processed_count} pricing entries, skipped {skipped_count} from {len(skus)} total SKUs")
        logger.info(f"OS statistics: Windows: {os_stats['windows']}, Linux: {os_stats['linux']}, Other: {os_stats['other']}")
        
        return all_pricing_data

    def _extract_vm_name(self, description: str) -> str:
        """Extract VM name from description with minimal filtering."""
        # Try to extract standard machine type
        machine_patterns = [
            r'\b([a-z]\d+[a-z]*-[a-z]+-\d+(?:-\d+)?g?)\b',  # Matches standard patterns like n1-standard-1, a2-highgpu-1g
            r'\b(custom-\d+-\d+)\b',  # Custom machine types
        ]
        
        for pattern in machine_patterns:
            match = re.search(pattern, description.lower())
            if match:
                return match.group(1)
        
        # Extract something machine-like from description
        words = re.findall(r'\b[a-z0-9-]+\b', description.lower())
        if words:
            vm_words = [word for word in words if any(term in word for term in ["instance", "core", "cpu", "vm", "machine"])]
            if vm_words:
                return vm_words[0]
            
            # Just take first 2-3 words if nothing else matches
            return "-".join(words[:min(3, len(words))])
        
        return "compute-instance"  # Default fallback

    def _extract_cpu_count(self, description: str) -> int:
        """Extract CPU count from description."""
        # Look for patterns like "2 vCPU" or "4 cores"
        patterns = [
            r'(\d+)\s*(?:vcpu|cpu|core|processor)',
            r'(\d+)-core',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description.lower())
            if match:
                return int(match.group(1))
        
        return 0  # Default if not found

    def _extract_memory_gb(self, description: str) -> float:
        """Extract memory in GB from description."""
        # Look for patterns like "16 GB" or "4 GiB"
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:gb|gib)',
            r'(\d+(?:\.\d+)?)\s*(?:mb|mib)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description.lower())
            if match:
                memory = float(match.group(1))
                if "mb" in match.group(0) or "mib" in match.group(0):
                    memory = memory / 1024  # Convert MB to GB
                return memory
        
        return 0.0  # Default if not found

    def _extract_gpu_info(self, description: str) -> Dict[str, Any]:
        """Extract GPU information from description."""
        desc_lower = description.lower()
        gpu_info = {"gpu_count": 0, "gpu_type": "", "gpu_memory": 0.0}
        
        # Check for known GPU types
        gpu_types = {
            "nvidia-tesla-t4": ["t4", "tesla t4"],
            "nvidia-tesla-v100": ["v100", "tesla v100"],
            "nvidia-tesla-p100": ["p100", "tesla p100"],
            "nvidia-tesla-p4": ["p4", "tesla p4"],
            "nvidia-tesla-k80": ["k80", "tesla k80"],
            "nvidia-a100": ["a100"],
            "nvidia-l4": ["l4"],
            "nvidia-h100": ["h100"],
        }
        
        for gpu_type, patterns in gpu_types.items():
            if any(pattern in desc_lower for pattern in patterns):
                gpu_info["gpu_type"] = gpu_type
                
                # Set GPU memory based on type
                if gpu_type == "nvidia-tesla-t4":
                    gpu_info["gpu_memory"] = 16.0
                elif gpu_type == "nvidia-tesla-v100":
                    gpu_info["gpu_memory"] = 32.0
                elif gpu_type == "nvidia-tesla-p100":
                    gpu_info["gpu_memory"] = 16.0
                elif gpu_type == "nvidia-tesla-p4":
                    gpu_info["gpu_memory"] = 8.0
                elif gpu_type == "nvidia-tesla-k80":
                    gpu_info["gpu_memory"] = 12.0
                elif gpu_type == "nvidia-a100":
                    gpu_info["gpu_memory"] = 40.0
                elif gpu_type == "nvidia-l4":
                    gpu_info["gpu_memory"] = 24.0
                elif gpu_type == "nvidia-h100":
                    gpu_info["gpu_memory"] = 80.0
                
                # Look for GPU count
                gpu_count_match = re.search(r'(\d+)\s*gpu', desc_lower)
                gpu_info["gpu_count"] = int(gpu_count_match.group(1)) if gpu_count_match else 1
                
                break
        
        # Check if description mentions GPU but no specific type was found
        if "gpu" in desc_lower and not gpu_info["gpu_type"]:
            gpu_info["gpu_type"] = "generic-gpu"
            gpu_info["gpu_count"] = 1
            gpu_info["gpu_memory"] = 8.0  # Default value
        
        return gpu_info

    def _fetch_all_skus(self) -> List[Dict[str, Any]]:
        """Fetch all SKUs from the Cloud Billing API."""
        all_skus = []
        
        try:
            # Set up headers based on authentication status
            if self.authenticated:
                headers = {
                    'Authorization': f'Bearer {self.credentials.token}',
                    'Content-Type': 'application/json'
                }
            else:
                headers = {'Content-Type': 'application/json'}
            
            # Fetch data with pagination
            params = {"pageSize": 1000}
            next_page_token = None
            page_num = 1
            
            while True:
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                response = requests.get(self.pricing_url, params=params, headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                page_skus = data.get("skus", [])
                all_skus.extend(page_skus)
                
                # Check if there are more pages
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break
                
                page_num += 1
                time.sleep(1)  # Avoid hitting rate limits
            
            return all_skus
                
        except Exception as e:
            logger.error(f"Error fetching SKUs: {e}")
            return []

    def _extract_price(self, sku: Dict[str, Any]) -> Optional[float]:
        """Extract price from SKU with minimal validation."""
        try:
            pricing_info = sku.get("pricingInfo", [])
            if not pricing_info:
                return None
            
            pricing_expression = pricing_info[0].get("pricingExpression", {})
            tiered_rates = pricing_expression.get("tieredRates", [])
            
            if not tiered_rates:
                return None
            
            unit_price = tiered_rates[0].get("unitPrice", {})
            nanos = unit_price.get("nanos", 0)
            units = unit_price.get("units", "0")
            
            # Handle both string and int units
            try:
                units_float = float(str(units))
            except (ValueError, TypeError):
                units_float = 0.0
            
            # Calculate the price
            price = units_float + (nanos / 1e9)
            
            # Basic validation
            if price < 0:
                return None
            
            # Convert based on usage unit
            usage_unit = pricing_expression.get("usageUnit", "").upper()
            if usage_unit == "S":  # Convert from per-second to per-hour
                price = price * 3600
            elif usage_unit == "MIN":  # Convert from per-minute to per-hour
                price = price * 60
            # If hour or empty, assume hourly
            
            return price
            
        except Exception as e:
            logger.debug(f"Error extracting price: {e}")
            return None

    def export_to_csv(self, filename: str) -> None:
        """Export pricing data to CSV file."""
        pricing_data = self.fetch_pricing_data()
        
        if not pricing_data:
            logger.error("No pricing data fetched, creating empty CSV file")
            
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Create an empty CSV with headers
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = [
                    'vm_name', 'provider_name', 'virtual_cpu_count', 'memory_gb',
                    'cpu_arch', 'price_per_hour_usd', 'gpu_count', 'gpu_name', 
                    'gpu_memory', 'os_type', 'region', 'other_details'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
            return
        
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        logger.info(f"Exporting {len(pricing_data)} pricing entries to {filename}")
        
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'vm_name', 'provider_name', 'virtual_cpu_count', 'memory_gb',
                'cpu_arch', 'price_per_hour_usd', 'gpu_count', 'gpu_name', 
                'gpu_memory', 'os_type', 'region', 'other_details'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in pricing_data:
                writer.writerow(item)
        
        logger.info(f"Successfully exported data to {filename}")

def main():
    """Main function to fetch pricing data and save to CSV."""
    try:
        # Set up the output file path
        output_file = "data/gcp_compute_pricing.csv"
        
        # Create the fetcher and export data
        fetcher = GCPComputePricingFetcher()
        fetcher.export_to_csv(output_file)
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()