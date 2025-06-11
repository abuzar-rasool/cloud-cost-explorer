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
        
    def _get_retail_price(self, service_family: str) -> List[CloudCompute]:
        """
        Fetches pricing information from Azure Retail Prices API without region filtering
        
        Args:
            service_family: The Azure service family (e.g., 'Compute')
        
        Returns:
            List of CloudCompute objects
        """
        base_filters = "serviceName eq 'Virtual Machines' and type eq 'Consumption' and contains(skuName, 'Spot') eq false and contains(skuName,'Low Priority') eq false"
        
        # First get all available items with pagination
        all_items = []
        next_page = self.prices_base_url
        
        print(f"Fetching Azure prices for all regions...")
        page_count = 0
        
        while next_page:
            page_count += 1
            print(f"Fetching page {page_count}...")
            
            if "skip" in next_page:  # If next_page already has query parameters
                print(f"next_page: {next_page}")
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
        
        # Map to organize Azure regions to our geographic regions
        azure_region_to_geo = {}
        for geo_region, region_list in AZURE_REGION_MAPPING.items():
            for region_code, region_name in region_list:
                azure_region_to_geo[region_code] = geo_region
        
        azure_vm_prices = []
        for item in vm_items:
            # Skip items that don't have a SKU name
            if not item.get("skuName"):
                continue

            # Get the Azure region from the item
            azure_region = item.get("armRegionName", "")
            if not azure_region:
                # Skip items without a region
                continue
                
            # Map Azure region to our geographic region
            geo_region = azure_region_to_geo.get(azure_region)
            if not geo_region:
                # If region is not in our mapping, skip or assign to a default
                # Here we're skipping it to maintain data quality
                print(f"Skipping item without a region: {item.get('skuName', '')}")
                continue
            
            # Extract all available fields from the item
            other_details = {
                "serviceName": item.get("serviceName", ""),
                "meterName": item.get("meterName", ""),
                "productName": item.get("productName", ""),
                "skuName": item.get("skuName", ""),
                "armRegionName": azure_region,
                "location": item.get("location", ""),
                "effectiveStartDate": item.get("effectiveStartDate", ""),
                "unitOfMeasure": item.get("unitOfMeasure", ""),
                "retailPrice": item.get("retailPrice", 0),
                "currencyCode": item.get("currencyCode", "USD"),
                # Add any other fields that might be useful
            }
            
            # Add any additional fields present in the item
            for key, value in item.items():
                if key not in other_details:
                    other_details[key] = value

            # Try to get a sensible VM name from the product or SKU name
            vm_name = item.get("productName", "") or item.get("skuName", "")
            
            # Default architecture to x86_64 unless we have info that says otherwise
            cpu_arch = "x86_64"
            if "ARM" in item.get("skuName", ""):
                cpu_arch = "ARM64"
                
            # Determine OS type from all available name fields
            os_type = "OTHER"
            detailed_os = "Unknown"
            
            # Check fields for OS information
            for field in [item.get("productName", ""), item.get("skuName", ""), item.get("meterName", "")]:
                field_lower = field.lower() if field else ""
                
                # Windows detection
                if "windows" in field_lower:
                    os_type = "WINDOWS"
                    detailed_os = "Windows"
                    
                    # Detect Windows version
                    if "server" in field_lower:
                        detailed_os = "Windows Server"
                        # Try to extract version
                        if "2022" in field_lower:
                            detailed_os += " 2022"
                        elif "2019" in field_lower:
                            detailed_os += " 2019"
                        elif "2016" in field_lower:
                            detailed_os += " 2016"
                        elif "2012" in field_lower:
                            if "r2" in field_lower:
                                detailed_os += " 2012 R2"
                            else:
                                detailed_os += " 2012"
                    elif "10" in field_lower:
                        detailed_os = "Windows 10"
                    elif "11" in field_lower:
                        detailed_os = "Windows 11"
                    
                    break
                
                # Linux detection
                elif any(os_name in field_lower for os_name in ["linux", "ubuntu", "centos", "rhel", "redhat", "suse", "debian"]):
                    os_type = "LINUX"
                    
                    # Detect specific Linux distribution
                    if "ubuntu" in field_lower:
                        detailed_os = "Ubuntu"
                        # Try to extract version
                        for version in ["18.04", "20.04", "22.04"]:
                            if version in field_lower:
                                detailed_os += f" {version}"
                                break
                    elif "centos" in field_lower:
                        detailed_os = "CentOS"
                        # Try to extract version
                        for version in ["7", "8"]:
                            if f"centos {version}" in field_lower or f"centos{version}" in field_lower:
                                detailed_os += f" {version}"
                                break
                    elif "redhat" in field_lower or "rhel" in field_lower:
                        detailed_os = "Red Hat Enterprise Linux"
                        # Try to extract version
                        for version in ["7", "8", "9"]:
                            if version in field_lower:
                                detailed_os += f" {version}"
                                break
                    elif "suse" in field_lower:
                        if "enterprise" in field_lower:
                            detailed_os = "SUSE Linux Enterprise"
                        else:
                            detailed_os = "SUSE Linux"
                    elif "debian" in field_lower:
                        detailed_os = "Debian"
                        # Try to extract version
                        for version in ["10", "11"]:
                            if version in field_lower:
                                detailed_os += f" {version}"
                                break
                    else:
                        detailed_os = "Linux"
                    
                    break
            
            # Store the detailed OS in other_details
            other_details["detailedOS"] = detailed_os

            # Try to extract CPU and memory info from the SKU name or product name
            virtual_cpu_count = 0
            memory_gb = 0
            
            # Example: "Standard_D2s_v3" has 2 vCPUs, or "D4as_v4" has 4 vCPUs
            product_name = item.get("productName", "")
            sku_name = item.get("skuName", "")
            
            # First try to extract from sku_name (usually most reliable)
            # Many Azure VM sizes have patterns like D2s_v3, F4s_v2, etc. where the number is the vCPU count
            for name in [sku_name, product_name]:
                if not name:
                    continue
                    
                # Try to find VM size patterns
                # Pattern for common VM series like D2s_v3, D4as_v4, etc.
                vm_size_match = re.search(r'([A-Za-z]+)(\d+)([a-z]*)(_v\d+)?', name)
                if vm_size_match:
                    # Group 2 is the number part, which usually corresponds to vCPU count
                    try:
                        virtual_cpu_count = int(vm_size_match.group(2))
                        # For some VM series, memory is often vCPU * 4 or * 8 GB
                        # This is a very rough estimate
                        if "D" in vm_size_match.group(1):
                            memory_gb = virtual_cpu_count * 4
                        elif "E" in vm_size_match.group(1):
                            memory_gb = virtual_cpu_count * 8
                        elif "F" in vm_size_match.group(1):
                            memory_gb = virtual_cpu_count * 2
                        # Break after successfully extracting values
                        break
                    except (ValueError, IndexError):
                        pass
            
            # Extract VM series information
            vm_series = None
            vm_generation = None
            
            # Look for VM series patterns in SKU name
            series_match = re.search(r'_([A-Za-z]+)(\d+)([a-z]*)(_v(\d+))?', sku_name)
            if series_match:
                vm_series = series_match.group(1)
                if series_match.group(5):  # Generation version number
                    vm_generation = f"v{series_match.group(5)}"
                
                # Store VM series info in other_details
                other_details["vmSeries"] = vm_series
                if vm_generation:
                    other_details["vmGeneration"] = vm_generation

            azure_vm_prices.append(
                CloudCompute(
                    vm_name=vm_name,
                    provider_name="AZURE",
                    virtual_cpu_count=virtual_cpu_count,  # Will be populated from specifications later
                    memory_gb=memory_gb,  # Will be populated from specifications later
                    cpu_arch=cpu_arch,
                    price_per_hour_usd=float(item.get("retailPrice", 0)),
                    gpu_count=0,  # Will be populated from specifications later
                    gpu_name=None,  # Will be populated from specifications later if available
                    gpu_memory=0.0,  # Will be populated from specifications later if available
                    os_type=os_type,  # Set based on name analysis
                    region=geo_region.value,
                    other_details=other_details
                )
            )
        
        return azure_vm_prices

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
        
        # Debugging: print a few SKUs to understand the structure
        if resource_skus:
            sample_sku = resource_skus[0]
            print(f"Sample SKU: {sample_sku.name}")
            if hasattr(sample_sku, 'family'):
                print(f"Family: {sample_sku.family}")
            if hasattr(sample_sku, 'size'):
                print(f"Size: {sample_sku.size}")
            
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
        
        # Debug: show some example keys to understand naming patterns
        if vm_specs:
            print("Sample VM specification keys:")
            for i, key in enumerate(list(vm_specs.keys())[:5]):
                print(f"  {i+1}. {key}")
            
        return vm_specs

    def get_compute_pricing(self) -> List[CloudCompute]:
        """
        Get compute pricing for all regions
        
        Returns:
            List of CloudCompute objects
        """
        # Get VM specifications for all regions
        vm_specs_by_region = {}
        
        print("Getting VM specifications for all regions...")
        
        # Get region codes from all geographic regions
        all_region_codes = []
        for geo_region, region_list in AZURE_REGION_MAPPING.items():
            for region_code, _ in region_list:
                all_region_codes.append(region_code)
        
        # Sample a few key regions to get VM specifications
        # We don't need to query all regions as VM specs are often similar
        sample_regions = ["eastus", "westeurope", "southeastasia", "australiaeast"]
        
        # Use regions from our mapping if sample regions not available
        if not any(region in all_region_codes for region in sample_regions):
            sample_regions = all_region_codes[:2]  # Just use the first couple of regions
        
        # Filter to regions we actually have
        sample_regions = [r for r in sample_regions if r in all_region_codes]
        
        if not sample_regions:
            print("No valid regions found for VM specifications!")
            return []
        
        # Get VM specifications for the sample regions
        for region in sample_regions:
            print(f"Getting VM specifications for {region}...")
            vm_specs_by_region[region] = self._get_vm_specifications(region)
            print(f"Retrieved {len(vm_specs_by_region[region])} VM specifications for {region}")
        
        # Combine all VM specifications
        combined_vm_specs = {}
        for region_specs in vm_specs_by_region.values():
            combined_vm_specs.update(region_specs)
        
        print(f"Combined VM specifications: {len(combined_vm_specs)} unique VM types")
        
        # Get pricing data for all regions
        vm_prices = self._get_retail_price("Compute")
        
        # Create a filtered list of VMs
        filtered_prices = []
        matched_count = 0
        
        for price in vm_prices:
            # Get SKU name from different fields to try matching
            product_name = price.other_details.get("productName", "") if price.other_details else ""
            meter_name = price.other_details.get("meterName", "") if price.other_details else ""
            sku_name = price.other_details.get("skuName", "") if price.other_details else ""
            
            # Try to match with VM specifications using different name fields
            spec_match = None
            
            # First try direct matches
            if sku_name in combined_vm_specs:
                spec_match = combined_vm_specs[sku_name]
            elif product_name in combined_vm_specs:
                spec_match = combined_vm_specs[product_name]
            elif meter_name in combined_vm_specs:
                spec_match = combined_vm_specs[meter_name]
            else:
                # Try partial matches - find a spec where the SKU name is contained in the product or meter name
                for spec_key, spec_value in combined_vm_specs.items():
                    if (spec_key in product_name or 
                        spec_key in meter_name or
                        spec_key in sku_name or
                        product_name in spec_key or
                        meter_name in spec_key):
                        spec_match = spec_value
                        break
            
            # Enrich with VM specifications if available
            if spec_match:
                matched_count += 1
                price.virtual_cpu_count = spec_match["vCPUs"]
                price.memory_gb = spec_match["memoryGB"]
                
                # Update GPU information if available
                if "gpuCount" in spec_match and spec_match["gpuCount"] > 0:
                    price.gpu_count = spec_match["gpuCount"]
                    
                    # Try to extract GPU name from the SKU name or product name
                    if "gpu" in sku_name.lower() or "gpu" in product_name.lower():
                        # Extract GPU info from the SKU name if possible
                        if "nvidia" in sku_name.lower() or "nvidia" in product_name.lower():
                            price.gpu_name = "NVIDIA"
                        elif "amd" in sku_name.lower() or "amd" in product_name.lower():
                            price.gpu_name = "AMD"
                
                # Add more VM specifications to other_details
                if price.other_details:
                    # Extract OS information from spec_match if available
                    if "OSType" in spec_match:
                        os_type = spec_match["OSType"]
                        price.other_details["specOSType"] = os_type
                        
                        # Update the main OS type if not already set
                        if price.os_type == "OTHER":
                            if os_type.lower() == "windows":
                                price.os_type = "WINDOWS"
                            elif os_type.lower() in ["linux", "ubuntu", "debian", "centos", "redhat", "rhel", "suse"]:
                                price.os_type = "LINUX"
                    
                    # Extract other interesting capabilities
                    if "HyperVGenerations" in spec_match:
                        price.other_details["hyperVGeneration"] = spec_match["HyperVGenerations"]
                    
                    # Check for premium storage support
                    if "PremiumIO" in spec_match:
                        price.other_details["supportsPremiumStorage"] = spec_match["PremiumIO"] == "True"
                    
                    # Check for encryption capabilities
                    if "EncryptionAtHostSupported" in spec_match:
                        price.other_details["supportsEncryptionAtHost"] = spec_match["EncryptionAtHostSupported"] == "True"
                    
                    # Add CPU information if available
                    if "CpuArchitectureType" in spec_match:
                        price.other_details["cpuArchitectureType"] = spec_match["CpuArchitectureType"]
                        # Update the main CPU architecture if spec provides it
                        if spec_match["CpuArchitectureType"].lower() == "arm64":
                            price.cpu_arch = "ARM64"
                        elif spec_match["CpuArchitectureType"].lower() in ["x64", "x86_64", "amd64"]:
                            price.cpu_arch = "x86_64"
                    
                    # Ensure all numeric fields in vm_specs are properly typed
                    typed_vm_specs = {}
                    for key, value in spec_match.items():
                        if isinstance(value, str):
                            # Try to convert string numeric values to their proper types
                            try:
                                if value.isdigit():
                                    typed_vm_specs[key] = int(value)
                                elif value.replace(".", "", 1).isdigit():
                                    typed_vm_specs[key] = float(value)
                                else:
                                    typed_vm_specs[key] = value
                            except (AttributeError, ValueError):
                                typed_vm_specs[key] = value
                        else:
                            typed_vm_specs[key] = value
                    
                    price.other_details.update(typed_vm_specs)

            # Additional OS type detection if still set to OTHER
            if price.os_type == "OTHER":
                # Check additional fields for OS information
                fields_to_check = [
                    product_name.lower(),
                    meter_name.lower(),
                    sku_name.lower()
                ]
                
                # Look for OS indicators in all fields
                for field in fields_to_check:
                    if "windows" in field:
                        price.os_type = "WINDOWS"
                        break
                    elif any(os_name in field for os_name in ["linux", "ubuntu", "centos", "rhel", "redhat", "suse", "debian"]):
                        price.os_type = "LINUX"
                        break
                
                # If still OTHER but the VM matches a pattern typically used for Linux VMs, assume Linux
                if price.os_type == "OTHER" and (
                    product_name.startswith("Standard_") or
                    "Virtual Machines" in product_name and not "Windows" in product_name
                ):
                    # Most Azure VMs default to Linux pricing unless specified as Windows
                    price.os_type = "LINUX"

            # Check if this VM meets the filter criteria (can add more filtering here)
            include_vm = True
            
            # Only add to filtered list if it passes all filters
            if include_vm:
                filtered_prices.append(price)
        
        print(f"VM spec match rate: {matched_count}/{len(filtered_prices)} ({matched_count/len(filtered_prices)*100 if filtered_prices else 0:.2f}%)")        
        self.vm_prices = filtered_prices
        
        # Count OS types for reporting
        windows_count = sum(1 for p in filtered_prices if p.os_type == "WINDOWS")
        linux_count = sum(1 for p in filtered_prices if p.os_type == "LINUX")
        other_count = sum(1 for p in filtered_prices if p.os_type == "OTHER")
        
        print(f"OS types: Windows: {windows_count}, Linux: {linux_count}, Other: {other_count}")
        
        # Count instances by region
        region_counts = {}
        for p in filtered_prices:
            region_counts[p.region] = region_counts.get(p.region, 0) + 1
            
        print("VM counts by region:")
        for region, count in sorted(region_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {region}: {count}")
            
        print(f"Total number of VMs fetched: {len(self.vm_prices)}")
        return self.vm_prices

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
        
        # Show detailed OS distributions
        print("\nDetailed OS distribution:")
        os_count = {}
        for instance in all_instances:
            detailed_os = instance.other_details.get("detailedOS", "Unknown") if instance.other_details else "Unknown"
            os_count[detailed_os] = os_count.get(detailed_os, 0) + 1
        
        # Sort by count (descending)
        for os_name, count in sorted(os_count.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {os_name}: {count} instances ({count/len(all_instances)*100:.2f}%)")
        
        # Count instances by region
        print("\nInstances by region:")
        region_count = {}
        for instance in all_instances:
            region_count[instance.region] = region_count.get(instance.region, 0) + 1
        
        # Sort by count (descending)
        for region, count in sorted(region_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {region}: {count} instances ({count/len(all_instances)*100:.2f}%)")
        
        # save to csv
        output_path = "data/azure_instances.csv"
        print(f"\nSaving data to {output_path}")
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(all_instances[0].model_dump().keys())
            for instance in all_instances:
                # Make a copy of the model data
                instance_data = instance.model_dump()
                # Convert other_details to JSON string if it exists
                if instance_data.get('other_details'):
                    import json
                    instance_data['other_details'] = json.dumps(instance_data['other_details'])
                writer.writerow(instance_data.values())
        
        print(f"Successfully saved {len(all_instances)} instances to {output_path}")
        print("Done!")
            
    except Exception as e:
        print(f"Error fetching Azure VM data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()