import csv
from enum import StrEnum
import os
from typing import List, Literal, Optional
from pydantic import BaseModel
import requests
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from dotenv import load_dotenv
import re
import time

load_dotenv()

class Region(StrEnum):
    NORTH_AMERICA = "north_america"
    SOUTH_AMERICA = "south_america"
    EUROPE = "europe"
    ASIA = "asia"
    AFRICA = "africa"
    OCEANIA = "oceania"
    ANTARCTICA = "antarctica"

class CloudCompute(BaseModel):
    vm_name: str
    provider_name: Literal["AZURE"]
    virtual_cpu_count: int
    memory_gb: float
    cpu_arch: str
    price_per_hour_usd: float
    gpu_count: int
    gpu_name: Optional[str]
    gpu_memory: float
    os_type: Literal["LINUX", "WINDOWS", "OTHER"]
    region: Literal[
        "north_america",
        "south_america",
        "europe",
        "asia",
        "africa",
        "oceania",
        "antarctica",
    ]
    other_details: Optional[dict] = None

class CloudStorage(BaseModel):
    storage_name: str
    provider_name: Literal["AZURE"]
    price_per_gb_month_usd: float
    region: Literal[
        "north_america",
        "south_america",
        "europe",
        "asia",
        "africa",
        "oceania",
        "antarctica",
    ]
    other_details: Optional[dict] = None

# Azure region mapping by geographical areas
AZURE_REGION_MAPPING = {
    Region.NORTH_AMERICA: [
        # United States (public)
        ("eastus", "East US"),
        ("eastus2", "East US 2"),
        ("centralus", "Central US"),
        ("northcentralus", "North Central US"),
        ("southcentralus", "South Central US"),
        ("westus", "West US"),
        ("westus2", "West US 2"),
        ("westus3", "West US 3"),
        ("westcentralus", "West Central US"),          # ← added
        ("mexicocentral", "Mexico Central"),           # ← added

        # Canada
        ("canadacentral", "Canada Central"),
        ("canadaeast", "Canada East"),

        # Government Clouds
        ("usgovvirginia", "US Gov Virginia"),
        ("usgovarizona", "US Gov Arizona"),
        ("usgovtexas", "US Gov Texas"),
        ("usdodcentral", "US DoD Central"),            # ← added
        ("usdodeast", "US DoD East"),                  # ← added
    ],
    Region.SOUTH_AMERICA: [
        ("brazilsouth", "Brazil South"),
        ("brazilsoutheast", "Brazil Southeast"),
        ("chilecentral", "Chile Central"),             # ← added
    ],
    Region.EUROPE: [
        # Western Europe
        ("westeurope", "West Europe"),
        ("northeurope", "North Europe"),
        ("uksouth", "UK South"),
        ("ukwest", "UK West"),
        ("francecentral", "France Central"),
        ("francesouth", "France South"),
        ("swedencentral", "Sweden Central"),           # ← added
        ("austriaeast", "Austria East"),               # ← added (coming soon)

        # Central Europe
        ("germanywestcentral", "Germany West Central"),
        ("germanynorth", "Germany North"),
        ("switzerlandnorth", "Switzerland North"),
        ("switzerlandwest", "Switzerland West"),

        # Northern Europe
        ("norwayeast", "Norway East"),
        ("norwaywest", "Norway West"),

        # Southern Europe
        ("italynorth", "Italy North"),
        ("spaincentral", "Spain Central"),
        ("polandcentral", "Poland Central"),
    ],
    Region.ASIA: [
        # East Asia
        ("eastasia", "East Asia"),
        ("southeastasia", "Southeast Asia"),
        ("japaneast", "Japan East"),
        ("japanwest", "Japan West"),
        ("koreacentral", "Korea Central"),
        ("koreasouth", "Korea South"),

        # South Asia
        ("centralindia", "Central India"),
        ("southindia", "South India"),
        ("westindia", "West India"),
        ("jioindiacentral", "Jio India Central"),
        ("jioindiawest", "Jio India West"),

        # Southeast & Middle East
        ("indonesiacentral", "Indonesia Central"),     # ← added
        ("malaysiawest", "Malaysia West"),             # ← added
        ("uaecentral", "UAE Central"),
        ("uaenorth", "UAE North"),
        ("qatarcentral", "Qatar Central"),
        ("israelcentral", "Israel Central"),
    ],
    Region.OCEANIA: [
        ("australiaeast", "Australia East"),
        ("australiasoutheast", "Australia Southeast"),
        ("australiacentral", "Australia Central"),
        ("australiacentral2", "Australia Central 2"),
        ("newzealandnorth", "New Zealand North"),      # ← added
    ],
    Region.AFRICA: [
        ("southafricanorth", "South Africa North"),
        ("southafricawest", "South Africa West"),
    ],
    Region.ANTARCTICA: [], # remove—no such region in Azure
}

# Azure VM series memory ratios (memory GB per vCPU)
# These are typical ratios used by Azure for different VM series
VM_SERIES_MEMORY_RATIO = {
    "A": 2.0,    # General purpose, balanced
    "B": 4.0,    # Burstable, basic
    "D": 4.0,    # General purpose, balanced
    "DS": 4.0,   # General purpose with premium storage
    "E": 8.0,    # Memory optimized
    "ES": 8.0,   # Memory optimized with premium storage
    "F": 2.0,    # Compute optimized
    "FS": 2.0,   # Compute optimized with premium storage
    "G": 8.0,    # Memory and storage optimized
    "GS": 8.0,   # Memory and storage optimized with premium storage
    "H": 4.0,    # High performance compute
    "L": 8.0,    # Storage optimized
    "LS": 8.0,   # Storage optimized with premium storage
    "M": 24.0,   # Memory optimized, highest memory-to-CPU ratio
    "N": 4.0,    # GPU enabled
    "NC": 6.0,   # GPU compute
    "ND": 8.0,   # GPU for deep learning
    "NV": 4.0,   # GPU visualization
    "T": 4.0,    # CPU optimized, high throughput
    "HB": 4.0,   # High Performance Computing
    "HC": 4.0    # High Performance Computing
}


client_id       = os.getenv("AZURE_CLIENT_ID")
client_secret   = os.getenv("AZURE_CLIENT_SECRET")
tenant_id       = os.getenv("AZURE_TENANT_ID")
subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")

if all([tenant_id, client_id, client_secret]):
    credential = ClientSecretCredential(tenant_id, client_id, client_secret)
else:
    credential = DefaultAzureCredential()


class AzureProvider:
    def __init__(self):
        self.provider_name = "AZURE"
        self.compute_client = ComputeManagementClient(credential, subscription_id)
        self.storage_client = StorageManagementClient(credential, subscription_id)
        self.prices_base_url = "https://prices.azure.com/api/retail/prices"
        self.vm_prices: List[CloudCompute] = []
        
    def _get_retail_price(self) -> List[dict]:
        """
        Fetches pricing information from Azure Retail Prices API without region filtering
        
        Returns:
            List of retail price items as dictionaries
        """
        base_filters = "serviceName eq 'Virtual Machines' and type eq 'Consumption' and contains(skuName, 'Spot') eq false and contains(skuName,'Low Priority') eq false"
        
        # First get all available items with pagination
        all_items = []
        next_page = self.prices_base_url
        
        print(f"Fetching Azure prices for all regions without filtering...")
        page_count = 0
        
        while next_page:
            page_count += 1
            print(f"Fetching page {page_count}...")
            
            if "skip" in next_page:  # If next_page already has query parameters
                response = requests.get(next_page)
            else:
                params = {"$filter": base_filters, "currencyCode": "USD"}
                response = requests.get(next_page, params=params)
                
            response.raise_for_status()
            data = response.json()
            items = data.get("Items", [])
            all_items.extend(items)
            
            print(f"Retrieved {len(items)} items (total: {len(all_items)})")
            
            # Check if there's another page
            next_page = data.get("NextPageLink")
            
            print(f"Sleeping for 5 seconds...")
            time.sleep(5)
        
        print(f"Total items fetched from API: {len(all_items)}")
        
        # Filter to include only on-demand VM items
        vm_items = [
            item for item in all_items 
            if item.get("serviceName") == "Virtual Machines" 
            and not item.get("reservationTerm")  # Exclude reserved instances
            and "spot" not in item.get("skuName", "").lower()  # Exclude spot instances
            and "low priority" not in item.get("skuName", "").lower()  # Exclude low priority instances
            and item.get("type") == "Consumption"  # Include only consumption (pay-as-you-go) pricing
        ]
        
        print(f"VM items after filtering: {len(vm_items)}")
        return vm_items

    def _get_vm_specifications(self, region: str) -> dict:
        """
        Fetches VM specifications from Azure Resource SKUs API
        
        Args:
            region: Azure region code
            
        Returns:
            Dictionary mapping SKU names to their specifications
        """
        vm_specs = {}
        
        print(f"Fetching VM specifications for region: {region}")
        
        # List resource SKUs filtered by VMs in the specified region
        resource_skus = list(self.compute_client.resource_skus.list(
            filter=f"location eq '{region}' and resourceType eq 'virtualMachines'"
        ))
        
        print(f"Retrieved {len(resource_skus)} VM SKUs from Azure")
            
        for sku in resource_skus:
            # Skip SKUs without capabilities
            if not hasattr(sku, 'capabilities') or sku.capabilities is None:
                continue
                
            # Extract capabilities
            capabilities = {cap.name: cap.value for cap in sku.capabilities 
                          if hasattr(cap, 'name') and hasattr(cap, 'value')}
            
            # Only include VMs with vCPUs and Memory
            if "vCPUs" not in capabilities or "MemoryGB" not in capabilities:
                continue
                
            # Create a sanitized capabilities dict with proper type conversion
            sanitized_capabilities = {}
            for key, value in capabilities.items():
                # Try to convert numeric strings to proper types
                try:
                    if value.isdigit():  # Integer check
                        sanitized_capabilities[key] = int(value)
                    elif value.replace(".", "", 1).isdigit():  # Float check
                        sanitized_capabilities[key] = float(value)
                    else:
                        sanitized_capabilities[key] = value
                except (AttributeError, ValueError):
                    sanitized_capabilities[key] = value

            vm_specs[sku.name] = {
                "vCPUs": int(capabilities.get("vCPUs", 0)),
                "memoryGB": float(capabilities.get("MemoryGB", 0)),
                "maxDataDisks": int(capabilities.get("MaxDataDiskCount", 0)) if "MaxDataDiskCount" in capabilities else 0,
                "maxNetworkInterfaces": int(capabilities.get("MaxNetworkInterfaces", 0)) if "MaxNetworkInterfaces" in capabilities else 0,
                "gpuCount": int(capabilities.get("GPUs", 0)) if "GPUs" in capabilities else 0,
                "premiumIO": capabilities.get("PremiumIO", "False") == "True",
                "acceleratedNetworking": capabilities.get("AcceleratedNetworkingEnabled", "False") == "True",
                **sanitized_capabilities
            }
            
            # Also add simplified versions of the name as keys for better matching
            # Example: If SKU name is "Standard_D2s_v3", also add "D2s_v3" and "D2s" as keys
            name_parts = sku.name.split('_')
            if len(name_parts) > 1:
                # Add the name without the "Standard_" prefix
                simplified_name = '_'.join(name_parts[1:])
                vm_specs[simplified_name] = vm_specs[sku.name]
                
                # Also add just the size part (like 'D2s_v3' or 'D2s')
                size_name = name_parts[1]
                if len(name_parts) > 2:
                    size_with_version = f"{name_parts[1]}_{name_parts[2]}"
                    vm_specs[size_with_version] = vm_specs[sku.name]
                vm_specs[size_name] = vm_specs[sku.name]
                
        print(f"Processed {len(vm_specs)} VM specifications with capabilities")
        return vm_specs
    
    def _estimate_memory_from_vm_size(self, vm_size: str, vcpu_count: int) -> float:
        """
        Estimates memory in GB based on VM size name and vCPU count
        
        Args:
            vm_size: VM size name (e.g., "Standard_D2s_v3" or "D2s_v3")
            vcpu_count: Number of vCPUs for the VM
            
        Returns:
            Estimated memory in GB
        """
        if not vm_size or vcpu_count <= 0:
            return 0.0
            
        # Extract series letter (like D, E, F, etc.)
        # Try different patterns to extract the series
        series_match = re.search(r'([A-Za-z]+)(\d+)', vm_size)
        if not series_match:
            # Try alternative pattern for names like "Standard_D2s_v3"
            parts = vm_size.split('_')
            if len(parts) > 1:
                series_match = re.search(r'([A-Za-z]+)(\d+)', parts[-1])
                
        if series_match:
            series = series_match.group(1).upper()
            
            # Check for common Azure VM series patterns
            for key in VM_SERIES_MEMORY_RATIO:
                if series.startswith(key):
                    return vcpu_count * VM_SERIES_MEMORY_RATIO[key]
            
            # For unknown series, use a default ratio of 4 GB per vCPU (common in Azure)
            return vcpu_count * 4.0
            
        return 0.0
    
    def _match_vm_with_spec(self, vm_item: dict, combined_vm_specs: dict) -> dict:
        """
        Advanced matching logic to find the best VM specification match
        
        Args:
            vm_item: VM item from retail API
            combined_vm_specs: Dictionary of VM specifications
            
        Returns:
            Best matching VM specification or None
        """
        # Extract key fields for matching
        sku_name = vm_item.get("skuName", "")
        product_name = vm_item.get("productName", "")
        meter_name = vm_item.get("meterName", "")
        
        # Try direct matching first
        for name in [sku_name, product_name, meter_name]:
            if name in combined_vm_specs:
                return combined_vm_specs[name]
                
        # Try matching with Standard_ prefix removed
        if sku_name.startswith("Standard_"):
            name_without_prefix = sku_name[9:]  # Remove "Standard_"
            if name_without_prefix in combined_vm_specs:
                return combined_vm_specs[name_without_prefix]
                
        # Try matching just the VM size part (e.g., "D2s_v3" from "Standard_D2s_v3")
        parts = sku_name.split('_')
        if len(parts) > 1:
            # For "Standard_D2s_v3", try "D2s_v3"
            suffix = '_'.join(parts[1:])
            if suffix in combined_vm_specs:
                return combined_vm_specs[suffix]
                
            # Try just the size part (like "D2s")
            if parts[1] in combined_vm_specs:
                return combined_vm_specs[parts[1]]
                
        # Try partial matching - look for any key that's part of our SKU name
        # This is more aggressive matching that might be less accurate
        for spec_key in combined_vm_specs.keys():
            # Only consider keys that are at least 3 characters for better accuracy
            if len(spec_key) >= 3:
                if spec_key in sku_name or spec_key in product_name:
                    return combined_vm_specs[spec_key]
        
        # No match found
        return None

    def get_compute_pricing(self) -> List[CloudCompute]:
        """
        Get compute pricing for all regions
        
        Returns:
            List of CloudCompute objects
        """
        # 1. Call retail API without region filter to get all VMs
        vm_items = self._get_retail_price()
        
        # 2. Create region mapping for easier lookup
        azure_region_to_geo = {}
        for geo_region, region_list in AZURE_REGION_MAPPING.items():
            for region_code, region_name in region_list:
                azure_region_to_geo[region_code] = geo_region.value
        
        # Get VM specifications for sample regions
        # We don't need to query all regions as VM specs are often similar across regions
        sample_regions = ["eastus", "westeurope", "southeastasia", "australiaeast"]
        
        # Get VM specifications for the sample regions
        combined_vm_specs = {}
        for region in sample_regions:
            region_specs = self._get_vm_specifications(region)
            combined_vm_specs.update(region_specs)
            print(f"Retrieved {len(region_specs)} VM specifications for {region}")
        
        print(f"Combined VM specifications: {len(combined_vm_specs)} unique VM types")
        
        # 3. Process each VM item and create CloudCompute objects
        cloud_compute_list = []
        matched_count = 0
        memory_from_specs_count = 0
        memory_estimated_count = 0
        
        for item in vm_items:
            # Extract the Azure region from the item
            azure_region = item.get("armRegionName", "")
            if not azure_region:
                continue
                
            # Map Azure region to our geographic region
            geo_region = azure_region_to_geo.get(azure_region)
            if not geo_region:
                continue
            
            # Create other_details dictionary with all item properties
            other_details = dict(item)
            
            # Try to get a sensible VM name
            vm_name = item.get("productName", "") or item.get("skuName", "")
            
            # Initialize CloudCompute fields with default values
            virtual_cpu_count = 0
            memory_gb = 0.0
            cpu_arch = "x86_64"
            price_per_hour_usd = float(item.get("retailPrice", 0))
            gpu_count = 0
            gpu_name = None
            gpu_memory = 0.0
            os_type = "OTHER"
            
            # Determine OS type from available fields
            product_name = item.get("productName", "").lower()
            sku_name = item.get("skuName", "").lower()
            meter_name = item.get("meterName", "").lower()
            
            # OS type detection
            if "windows" in product_name or "windows" in sku_name or "windows" in meter_name:
                os_type = "WINDOWS"
                other_details["detailedOS"] = "Windows"
                
                # Extract Windows version if available
                if "server" in product_name or "server" in sku_name:
                    if "2022" in product_name or "2022" in sku_name:
                        other_details["detailedOS"] = "Windows Server 2022"
                    elif "2019" in product_name or "2019" in sku_name:
                        other_details["detailedOS"] = "Windows Server 2019"
                    elif "2016" in product_name or "2016" in sku_name:
                        other_details["detailedOS"] = "Windows Server 2016"
                    else:
                        other_details["detailedOS"] = "Windows Server"
            elif any(os_name in product_name or os_name in sku_name or os_name in meter_name 
                    for os_name in ["linux", "ubuntu", "centos", "rhel", "redhat", "suse", "debian"]):
                os_type = "LINUX"
                
                # Determine Linux distribution if possible
                if "ubuntu" in product_name or "ubuntu" in sku_name:
                    other_details["detailedOS"] = "Ubuntu"
                elif "centos" in product_name or "centos" in sku_name:
                    other_details["detailedOS"] = "CentOS"
                elif "redhat" in product_name or "rhel" in product_name or "redhat" in sku_name or "rhel" in sku_name:
                    other_details["detailedOS"] = "Red Hat Enterprise Linux"
                elif "suse" in product_name or "suse" in sku_name:
                    other_details["detailedOS"] = "SUSE Linux"
                elif "debian" in product_name or "debian" in sku_name:
                    other_details["detailedOS"] = "Debian"
                else:
                    other_details["detailedOS"] = "Linux"
            else:
                # If no specific OS detected, default to Linux for standard VMs
                if product_name.startswith("standard_") or "virtual machines" in product_name and "windows" not in product_name:
                    os_type = "LINUX"
                    other_details["detailedOS"] = "Linux"
            
            # Try to extract VM size information from SKU name
            # Example: Standard_D2s_v3 has 2 vCPUs
            vm_size_match = re.search(r'([A-Za-z]+)(\d+)([a-z]*)(_v\d+)?', sku_name)
            if vm_size_match:
                try:
                    cpu_count = int(vm_size_match.group(2))
                    if cpu_count > 0:
                        virtual_cpu_count = cpu_count
                except (ValueError, IndexError):
                    pass
                    
                # Store VM series info
                vm_series = vm_size_match.group(1) if vm_size_match.group(1) else ""
                vm_version = vm_size_match.group(4) if vm_size_match.group(4) else ""
                
                if vm_series:
                    other_details["vmSeries"] = vm_series
                if vm_version:
                    other_details["vmGeneration"] = vm_version
            
            # Check if the VM is in our specifications database using the enhanced matching
            spec_match = self._match_vm_with_spec(item, combined_vm_specs)
                     
            # If we found a match, use the specification data
            if spec_match:
                matched_count += 1
                virtual_cpu_count = spec_match.get("vCPUs", virtual_cpu_count)
                memory_gb = spec_match.get("memoryGB", memory_gb)
                if memory_gb > 0:
                    memory_from_specs_count += 1
                gpu_count = spec_match.get("gpuCount", gpu_count)
                
                # Check for ARM architecture
                if spec_match.get("CpuArchitectureType", "").lower() == "arm64":
                    cpu_arch = "ARM64"
                    
                # Add additional specifications to other_details
                other_details.update(spec_match)
            
            # If we still don't have memory information, estimate it from the VM size and CPU count
            if memory_gb <= 0 and virtual_cpu_count > 0:
                memory_gb = self._estimate_memory_from_vm_size(item.get("skuName", ""), virtual_cpu_count)
                if memory_gb > 0:
                    memory_estimated_count += 1
                    other_details["memorySource"] = "estimated"
            
            # GPU detection
            if gpu_count > 0 or "gpu" in sku_name or "gpu" in product_name:
                # If gpu_count not set but "gpu" is in the name, assume at least 1
                if gpu_count == 0:
                    gpu_count = 1
                    
                # Try to determine GPU manufacturer/model
                if "nvidia" in sku_name or "nvidia" in product_name:
                    gpu_name = "NVIDIA"
                elif "amd" in sku_name or "amd" in product_name:
                    gpu_name = "AMD"
                    
                # Try to extract GPU memory if available
                # This is a rough estimation as detailed GPU specs are often not available in the API
                if "v100" in sku_name or "v100" in product_name:
                    gpu_name = "NVIDIA Tesla V100"
                    gpu_memory = 16.0  # Most V100s have 16GB
                elif "k80" in sku_name or "k80" in product_name:
                    gpu_name = "NVIDIA Tesla K80"
                    gpu_memory = 12.0
                elif "p100" in sku_name or "p100" in product_name:
                    gpu_name = "NVIDIA Tesla P100"
                    gpu_memory = 16.0
                elif "a100" in sku_name or "a100" in product_name:
                    gpu_name = "NVIDIA A100"
                    gpu_memory = 40.0
            
            # Create CloudCompute object
            compute = CloudCompute(
                vm_name=vm_name,
                provider_name="AZURE",
                virtual_cpu_count=virtual_cpu_count,
                memory_gb=memory_gb,
                cpu_arch=cpu_arch,
                price_per_hour_usd=price_per_hour_usd,
                gpu_count=gpu_count,
                gpu_name=gpu_name,
                gpu_memory=gpu_memory,
                os_type=os_type,
                region=geo_region,
                other_details=other_details
            )
            
            cloud_compute_list.append(compute)
        
        self.vm_prices = cloud_compute_list
        print(f"Created {len(cloud_compute_list)} CloudCompute objects")
        print(f"VMs matched with specifications: {matched_count} ({matched_count/len(cloud_compute_list)*100 if cloud_compute_list else 0:.2f}%)")
        print(f"VMs with memory from specs: {memory_from_specs_count} ({memory_from_specs_count/len(cloud_compute_list)*100 if cloud_compute_list else 0:.2f}%)")
        print(f"VMs with estimated memory: {memory_estimated_count} ({memory_estimated_count/len(cloud_compute_list)*100 if cloud_compute_list else 0:.2f}%)")
        print(f"VMs with memory data (total): {memory_from_specs_count + memory_estimated_count} ({(memory_from_specs_count + memory_estimated_count)/len(cloud_compute_list)*100 if cloud_compute_list else 0:.2f}%)")
        
        return cloud_compute_list

    def get_storage_pricing(self) -> List[CloudStorage]:
        """
        Get storage pricing for all regions
        
        Returns:
            List of CloudStorage objects
        """
        # Not implemented yet
        return []
    

def main():
    # Create the provider
    azure_provider = AzureProvider()
    
    print(f"\n{'='*80}")
    print(f"Fetching Azure VM data for all regions...")
    print(f"{'='*80}\n")
    
    try:
        # Fetch instance data for all regions
        all_instances = azure_provider.get_compute_pricing()
        
        if not all_instances:
            print("No VM instances found. Please check your Azure credentials.")
            return
            
        # Print overall summary
        print(f"\n\n{'='*80}")
        print(f"OVERALL SUMMARY")
        print(f"{'='*80}")
        print(f"Total instances across all regions: {len(all_instances)}")
        
        # Count instances with CPU and memory data
        instances_with_cpu = [i for i in all_instances if i.virtual_cpu_count > 0]
        instances_with_memory = [i for i in all_instances if i.memory_gb > 0]
        
        print(f"Instances with CPU data: {len(instances_with_cpu)} ({len(instances_with_cpu)/len(all_instances)*100 if all_instances else 0:.2f}%)")
        print(f"Instances with memory data: {len(instances_with_memory)} ({len(instances_with_memory)/len(all_instances)*100 if all_instances else 0:.2f}%)")
        
        # Count instances by OS type
        linux_instances = [i for i in all_instances if i.os_type == "LINUX"]
        windows_instances = [i for i in all_instances if i.os_type == "WINDOWS"]
        other_instances = [i for i in all_instances if i.os_type == "OTHER"]
        
        # Count by OS type
        print(f"\nOS types distribution:")
        print(f"  Linux: {len(linux_instances)} ({len(linux_instances)/len(all_instances)*100 if all_instances else 0:.2f}%)")
        print(f"  Windows: {len(windows_instances)} ({len(windows_instances)/len(all_instances)*100 if all_instances else 0:.2f}%)")
        print(f"  Other: {len(other_instances)} ({len(other_instances)/len(all_instances)*100 if all_instances else 0:.2f}%)")
        
        # Print some sample instances with data
        if instances_with_cpu:
            print("\nSample instances with CPU/memory data:")
            for i, instance in enumerate(instances_with_cpu[:5]):
                detailed_os = instance.other_details.get("detailedOS", "Unknown") if instance.other_details else "Unknown"
                vm_series = instance.other_details.get("vmSeries", "") if instance.other_details else ""
                vm_gen = instance.other_details.get("vmGeneration", "") if instance.other_details else ""
                vm_series_info = f", Series: {vm_series} {vm_gen}" if vm_series else ""
                
                print(f"{i+1}. {instance.vm_name}: {instance.virtual_cpu_count} vCPUs, {instance.memory_gb} GB memory, " +
                      f"OS: {instance.os_type} ({detailed_os}){vm_series_info}, ${instance.price_per_hour_usd:.4f}/hour")
        
        # Count instances by region
        print("\nInstances by region:")
        region_count = {}
        for instance in all_instances:
            region_count[instance.region] = region_count.get(instance.region, 0) + 1
        
        # Sort by count (descending)
        for region, count in sorted(region_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {region}: {count} instances ({count/len(all_instances)*100:.2f}%)")
        
        # 4. Save the data to CSV
        output_path = "data/azure_instances.csv"
        print(f"\nSaving data to {output_path}")
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            # Write headers
            writer.writerow(all_instances[0].model_dump().keys())
            # Write data
            for instance in all_instances:
                # Make a copy of the model data
                instance_data = instance.model_dump()
                # Convert other_details to JSON string if it exists
                if instance_data.get('other_details'):
                    import json
                    instance_data['other_details'] = json.dumps(instance_data['other_details'])
                writer.writerow(instance_data.values())
        
        print(f"Successfully saved {len(all_instances[:100])} instances to {output_path}")
        print("Done!")
            
    except Exception as e:
        print(f"Error fetching Azure VM data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()