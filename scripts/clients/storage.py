# pip install boto3 requests python-dateutil
import json, re, csv, boto3, requests
from decimal import Decimal
from urllib.parse import quote_plus
from dateutil import parser as dt
from collections import defaultdict
from enum import StrEnum

HOURS_PER_MONTH = Decimal("730")
MAX_PAGES = 10000  # Increased to get more comprehensive data

class Region(StrEnum):
    NORTH_AMERICA = "north_america"
    SOUTH_AMERICA = "south_america"
    EUROPE = "europe"
    ASIA = "asia"
    AFRICA = "africa"
    OCEANIA = "oceania"
    ANTARCTICA = "antarctica"

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
        ("attatlanta1", "AT&T Atlanta"),               # ← added
        ("attdallas1", "AT&T Dallas"),                 # ← added
        ("global", "Global"),                          # ← added (default to North America)

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
        ("swedensouth", "Sweden South"),               # ← added

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
        ("malaysiasouth", "Malaysia South"),           # ← added
        ("uaecentral", "UAE Central"),
        ("uaenorth", "UAE North"),
        ("qatarcentral", "Qatar Central"),
        ("israelcentral", "Israel Central"),
        ("israelnorthwest", "Israel Northwest"),       # ← added
    ],
    Region.OCEANIA: [
        ("australiaeast", "Australia East"),
        ("australiasoutheast", "Australia Southeast"),
        ("australiacentral", "Australia Central"),
        ("australiacentral2", "Australia Central 2"),
        ("newzealandnorth", "New Zealand North"),      # ← added
        ("perth", "Perth"),                            # ← added
    ],
    Region.AFRICA: [
        ("southafricanorth", "South Africa North"),
        ("southafricawest", "South Africa West"),
    ],
    Region.ANTARCTICA: [], # remove—no such region in Azure
}

# Access tier mapping based on your requirements
ACCESS_TIER_MAPPING = {
    "hot": "FREQUENT_ACCESS",
    "premium": "FREQUENT_ACCESS", 
    "premium block blob": "FREQUENT_ACCESS",
    "standard": "FREQUENT_ACCESS",
    "general purpose": "FREQUENT_ACCESS",
    "cool": "OCCASIONAL_ACCESS",
    "cold": "RARE_ACCESS",
    "archive": "ARCHIVE"
}

# Helper functions for parsing unit of measure
BUNDLE = {"": 1, "K": 1_000, "M": 1_000_000}
UOM_RE = re.compile(r"(?P<n>\d+(?:\.\d+)?)(?P<p>[KM])?\s*(?P<u>[^/\s]*)(?:/(?P<t>\w+))?", re.I)

def parse_uom(uom):
    """Parse unit of measure string to extract number, unit, and time period"""
    m = UOM_RE.match(uom)
    if not m:
        return None, None, None
    n = Decimal(m["n"]) * BUNDLE[m["p"] or ""]
    unit, period = (m["u"] or "").lower(), (m["t"] or "").lower() or None
    return n, unit, period

def map_azure_region_to_geo(azure_region):
    """
    Map Azure region code to our geographical region enum
    
    Args:
        azure_region: Azure region code (e.g., 'eastus', 'westeurope')
        
    Returns:
        Geographical region string or None if not found
    """
    if not azure_region:
        return None
        
    # Convert to lowercase for consistent matching
    azure_region = azure_region.lower()
    
    # Create region mapping for easier lookup
    for geo_region, region_list in AZURE_REGION_MAPPING.items():
        for region_code, region_name in region_list:
            if azure_region == region_code.lower():
                return geo_region.value
    
    # Return None if region not found in mapping
    return None

def classify_and_normalize_azure_charge(item):
    """
    Classify Azure storage charges and normalize to canonical units
    Returns: (charge_type, normalized_price) where charge_type is one of:
    'capacity', 'read_ops', 'write_ops', 'egress', 'flat_monthly'
    """
    uom = item["unitOfMeasure"]
    sku_name = item["skuName"].lower()
    price = Decimal(str(item["unitPrice"]))
    meter_name = item.get("meterName", "").lower()
    
    # Exclude specialized high-cost operations that skew normal pricing analysis
    excluded_operation_patterns = [
        "priority read",          # Archive priority read operations (extremely expensive)
        "archive priority read",  # Explicit archive priority reads
        "expedited retrieval",    # Expedited data retrieval from archive
        "emergency read",         # Emergency read operations
        "instant retrieval",      # Instant retrieval from archive
        "bulk retrieval",         # Bulk data retrieval operations
        "restore",                # Data restore operations
        "early delete",           # Early deletion penalties
        "index tags",             # Index tag operations (not typical storage ops)
        "encryption scope",       # Encryption scope management (not storage ops)
        "data processing",        # Data processing services
        "query acceleration",     # Query acceleration services
        "analytics",              # Analytics services
        "replication",            # Geo-replication overhead
        "lifecycle",              # Lifecycle management operations
        "inventory",              # Blob inventory operations
        "change feed",            # Change feed services
        "event grid"              # Event grid notifications
    ]
    
    # Check if this is a specialized operation to exclude
    if any(pattern in meter_name for pattern in excluded_operation_patterns) or \
       any(pattern in sku_name for pattern in excluded_operation_patterns):
        return None, None
    
    bundle, unit, period = parse_uom(uom)
    if bundle is None:
        return None, None
    
    # Capacity charges (storage space) - normalize to USD/GiB-month
    # Azure storage charges are often just "1 GB" without explicit time period but are monthly
    if any(x in uom.lower() for x in ["gb", "gib"]):
        # Handle reserved capacity pricing (e.g., "1 PB", "100 TB", etc.)
        reserved_multiplier = 1
        
        # Check for petabyte/terabyte reserved capacity in SKU name
        if "10 pb" in sku_name or "10pb" in sku_name:
            reserved_multiplier = 10_485_760  # 10 PB = 10,485,760 GB
        elif "1 pb" in sku_name or "1pb" in sku_name:
            reserved_multiplier = 1_048_576  # 1 PB = 1,048,576 GB
        elif "100 tb" in sku_name or "100tb" in sku_name:
            reserved_multiplier = 102_400    # 100 TB = 102,400 GB
        elif "10 tb" in sku_name or "10tb" in sku_name:
            reserved_multiplier = 10_240     # 10 TB = 10,240 GB
        elif "1 tb" in sku_name or "1tb" in sku_name:
            reserved_multiplier = 1_024      # 1 TB = 1,024 GB
        
        # Check if it has an explicit time period
        if any(x in uom.lower() for x in ["/month", "/hour", "/day", " month", " hour", " day"]):
            if period == "hour":
                normalized_price = (price * (HOURS_PER_MONTH / bundle)) / reserved_multiplier
            elif period == "month":
                normalized_price = (price / bundle) / reserved_multiplier
            elif period == "day":
                normalized_price = (price * (30 / bundle)) / reserved_multiplier
            else:
                normalized_price = (price / bundle) / reserved_multiplier
        else:
            # For Azure, GB charges without explicit period are typically monthly
            # Especially for storage tiers (hot, cool, archive, etc.)
            storage_tier_keywords = ["hot", "cool", "cold", "archive", "premium", "standard"]
            if any(keyword in sku_name for keyword in storage_tier_keywords):
                normalized_price = (price / bundle) / reserved_multiplier  # Assume monthly billing
                return "capacity", float(normalized_price)
        return "capacity", float(normalized_price)
    
    # Request operations - normalize to USD per million operations
    if any(x in uom.lower() for x in ["10k", "100k", "1k", "1m", "10 k", "100 k", "1 k", "1 m"]) and not any(x in uom.lower() for x in ["gb", "gib"]):
        # Normalize to price per million operations
        normalized_price = (price / bundle) * 1_000_000
        
        # Additional filtering for reasonable operation prices
        # Exclude operations that cost more than $100 per million (extremely high)
        if normalized_price > 100.0:
            return None, None
        
        # Classify as read or write based on meter name first, then SKU name
        write_patterns = ["write", "put", "post", "create", "upload", "copy", "append", "patch"]
        read_patterns = ["read", "get", "list", "head", "retrieve", "download"]
        delete_patterns = ["delete", "remove"]
        
        # Check meter name first (more accurate)
        if any(pattern in meter_name for pattern in write_patterns):
            return "write_ops", float(normalized_price)
        elif any(pattern in meter_name for pattern in read_patterns):
            return "read_ops", float(normalized_price)
        elif any(pattern in meter_name for pattern in delete_patterns):
            return "write_ops", float(normalized_price)  # Deletes are write operations
        # Then check SKU name as fallback
        elif any(pattern in sku_name for pattern in write_patterns):
            return "write_ops", float(normalized_price)
        elif any(pattern in sku_name for pattern in read_patterns):
            return "read_ops", float(normalized_price)
        else:
            # For ambiguous operations, check for common Azure operation patterns
            if any(op in meter_name for op in ["operations", "list", "container"]):
                return "read_ops", float(normalized_price)  # Default to read for general operations
            return "read_ops", float(normalized_price)
    
    # Special exclusions for data processing services that are NOT storage operations
    # These services are charged per MB/GB of data processed, not per operation
    excluded_data_services = [
        "point-in-time restore", "restore", "backup", "recovery",
        "change feed", "event grid", "index", "search", "analytics",
        "replication", "geo-replication", "sync", "migration",
        "encryption", "key vault", "managed identity", "monitor",
        "diagnostic", "log", "audit", "compliance", "governance"
    ]
    
    # Check if this is a data processing service, not a storage operation
    is_data_processing = (
        any(service in meter_name for service in excluded_data_services) or
        any(service in sku_name for service in excluded_data_services) or
        "data processed" in meter_name or
        "data scanned" in meter_name
    )
    
    # If it's a data processing service with MB/GB pricing, don't treat as operations
    if is_data_processing and any(x in uom.lower() for x in ["mb", "gb", "gib", "mib"]):
        # These are data processing charges, not storage operations - skip them
        return None, None
    
    # Data transfer/egress - normalize to USD/GiB
    transfer_keywords = ["data transfer", "egress", "outbound", "bandwidth", "geo-replication", "replication"]
    meter_transfer_keywords = ["data transfer", "egress", "outbound", "bandwidth", "geo", "replication", "inter-region", "zone redundant"]
    
    # Check both SKU name and meter name for transfer patterns
    has_transfer_pattern = (any(keyword in sku_name for keyword in transfer_keywords) or 
                           any(keyword in meter_name for keyword in meter_transfer_keywords))
    
    if has_transfer_pattern and any(x in uom.lower() for x in ["gb", "gib"]):
        normalized_price = price / bundle
        return "egress", float(normalized_price)
    
    # Flat monthly charges - normalize to USD/item-month
    if ("/month" in uom.lower() or " month" in uom.lower()) and not any(x in uom.lower() for x in ["gb", "gib"]):
        normalized_price = price / bundle
        return "flat_monthly", float(normalized_price)
    
    return None, None

def extract_storage_class_and_service(sku_name, service_name):
    """Extract storage class from Azure SKU name and determine if it's blob storage"""
    sku_lower = sku_name.lower()
    service_lower = service_name.lower()
    
    # Enhanced blob storage detection - Azure storage SKUs often don't contain "blob" explicitly
    # but are identifiable by storage tiers and redundancy patterns
    blob_indicators = [
        "blob", "block blob", "append blob", "page blob",
        "storage blob", "blob storage", "blob tier",
        "blob operations", "blob access"
    ]
    
    # Storage tier and redundancy patterns that indicate general purpose storage (mostly blob storage)
    storage_patterns = [
        "hot", "cool", "cold", "archive",  # Access tiers
        "premium",  # Performance tier
        "standard",  # Standard tier
        " lrs", " grs", " zrs", " ra-grs", " ra-zrs",  # Redundancy options (with space to avoid partial matches)
        "locally redundant", "geo-redundant", "zone-redundant"
    ]
    
    # Check for explicit blob indicators first
    is_blob_storage = any(indicator in sku_lower for indicator in blob_indicators)
    
    # If not explicitly blob, check for storage tier patterns
    if not is_blob_storage:
        is_blob_storage = any(pattern in sku_lower for pattern in storage_patterns)
    
    # Also exclude non-storage services (but keep data transfer as it's part of storage pricing)
    excluded_patterns = [
        "vpn", "express", "dns", "traffic manager",
        "load balancer", "application gateway", "firewall", "front door",
        "cdn", "backup", "site recovery", "batch", "container", "kubernetes",
        "sql", "cosmos", "redis", "search", "synapse", "data factory",
        "stream analytics", "event", "service bus", "notification", "logic app",
        "function", "app service", "virtual machine", "disk", "snapshot",
        "managed identity", "key vault", "active directory", "monitor",
        "security center", "sentinel", "automation", "devops", "artifacts"
    ]
    
    if any(pattern in sku_lower for pattern in excluded_patterns):
        is_blob_storage = False
    
    if not is_blob_storage:
        return None, None
    
    # Extract storage class from SKU name
    if "premium" in sku_lower and "block blob" in sku_lower:
        storage_class = "Premium Block Blob" 
    elif "premium" in sku_lower:
        storage_class = "Premium"
    elif "hot" in sku_lower:
        storage_class = "Hot"
    elif "cool" in sku_lower:
        storage_class = "Cool"
    elif "cold" in sku_lower:
        storage_class = "Cold"
    elif "archive" in sku_lower:
        storage_class = "Archive"
    elif "standard" in sku_lower:
        storage_class = "Standard"
    else:
        # Use a generic storage class if we can't determine the specific tier
        storage_class = "General Purpose"
    
    return "Blob Storage", storage_class

def get_access_tier(storage_class):
    """Map storage class to standardized access tier"""
    return ACCESS_TIER_MAPPING.get(storage_class.lower(), "FREQUENT_ACCESS")

def main():
    print("🔍 Fetching Azure Blob Storage pricing data...")
    
    # Filter for storage services - broader than just blob storage to catch all related charges
    flt = quote_plus("serviceName eq 'Storage'")
    url = f"https://prices.azure.com/api/retail/prices?$filter={flt}"
    
    # Group data by (region, service_code, storage_class)
    storage_data = defaultdict(lambda: {
        "capacity_price": None,
        "read_price": None, 
        "write_price": None,
        "egress_price": None,
        "flat_item_price": None,
        "service_name": None,
        "other_details": {},
        "currency": "USD",
        "last_updated": None
    })
    
    page_count = 0
    total_items = 0
    processed_items = 0
    
    # Add debugging counters
    debug_stats = {
        "total_storage_items": 0,
        "blob_related_items": 0,
        "capacity_items_found": 0,
        "operation_items_found": 0,
        "skipped_no_region": 0,
        "skipped_no_blob": 0,
        "skipped_unmapped_region": 0
    }
    
    # Track unmapped regions for debugging
    unmapped_regions = set()
    
    while url and page_count < MAX_PAGES:
        try:
            print(f"📄 Fetching page {page_count + 1}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
            
            items = payload.get("Items", [])
            print(f"📦 Got {len(items)} items from Azure API")
            total_items += len(items)
            
            for item in items:
                debug_stats["total_storage_items"] += 1
                
                # Debug: Print first few interesting items
                if debug_stats["total_storage_items"] <= 10:
                    print(f"🔍 Sample item: {item['skuName']} | {item['unitOfMeasure']} | ${item['unitPrice']}")
                
                service_code, storage_class = extract_storage_class_and_service(
                    item["skuName"], item["serviceName"]
                )
                
                # Skip if not blob storage
                if not service_code:
                    debug_stats["skipped_no_blob"] += 1
                    continue
                    
                debug_stats["blob_related_items"] += 1
                
                azure_region = item.get("armRegionName") or item.get("location", "")
                
                # Skip if no valid region
                if not azure_region:
                    debug_stats["skipped_no_region"] += 1
                    continue
                
                # Map Azure region to our geographical region
                region = map_azure_region_to_geo(azure_region)
                if not region:
                    debug_stats["skipped_unmapped_region"] += 1
                    unmapped_regions.add(azure_region)
                    continue
                
                charge_type, normalized_price = classify_and_normalize_azure_charge(item)
                
                if charge_type == "capacity":
                    debug_stats["capacity_items_found"] += 1
                    print(f"🎯 Found capacity item: {item['skuName']} | {item['unitOfMeasure']} | ${normalized_price}")
                elif charge_type in ["read_ops", "write_ops"]:
                    debug_stats["operation_items_found"] += 1
                
                if charge_type and normalized_price is not None:
                    # Use azure_region instead of geographical region for more granular data
                    key = (azure_region, region, service_code, storage_class)
                    processed_items += 1
                    
                    # Store the price in the appropriate field
                    if charge_type == "capacity":
                        storage_data[key]["capacity_price"] = normalized_price
                    elif charge_type == "read_ops":
                        storage_data[key]["read_price"] = normalized_price
                    elif charge_type == "write_ops":
                        storage_data[key]["write_price"] = normalized_price
                    elif charge_type == "egress":
                        storage_data[key]["egress_price"] = normalized_price
                    elif charge_type == "flat_monthly":
                        storage_data[key]["flat_item_price"] = normalized_price
                    
                    # Store service_name (sku_name) - use the first one we encounter for this key
                    if storage_data[key]["service_name"] is None:
                        storage_data[key]["service_name"] = item["skuName"]
                    
                    # Store metadata
                    storage_data[key]["currency"] = item["currencyCode"]
                    storage_data[key]["last_updated"] = item["effectiveStartDate"]
                    
                    # Store additional details in other_details
                    storage_data[key]["other_details"][f"{charge_type}_details"] = {
                        "sku_name": item["skuName"],
                        "raw_uom": item["unitOfMeasure"],
                        "raw_price": float(item["unitPrice"]),
                        "meter_name": item.get("meterName", ""),
                        "product_name": item.get("productName", ""),
                        "effective_date": item["effectiveStartDate"],
                        "azure_region": azure_region  # Store original Azure region for reference
                    }
            
            page_count += 1
            url = payload.get("NextPageLink")
            
        except Exception as e:
            print(f"❌ Azure API error: {e}")
            break
    
    # Print debug statistics
    print(f"\n🔍 Debug Statistics:")
    print(f"  Total storage items examined: {debug_stats['total_storage_items']}")
    print(f"  Blob-related items found: {debug_stats['blob_related_items']}")
    print(f"  Capacity pricing items found: {debug_stats['capacity_items_found']}")
    print(f"  Operation pricing items found: {debug_stats['operation_items_found']}")
    print(f"  Skipped (no blob relation): {debug_stats['skipped_no_blob']}")
    print(f"  Skipped (no region): {debug_stats['skipped_no_region']}")
    print(f"  Skipped (unmapped region): {debug_stats['skipped_unmapped_region']}")
    
    if unmapped_regions:
        print(f"\n⚠️  Unmapped Azure regions found: {sorted(unmapped_regions)}")
    
    print(f"\n📊 Processed {total_items} total items")
    print(f"🎯 Found {processed_items} relevant pricing items")
    print(f"📦 Grouped into {len(storage_data)} unique (region, service, storage_class) combinations")
    
    # Convert to final format matching StoragePricing schema
    final_records = []
    for (azure_region, geo_region, service_code, storage_class), data in storage_data.items():
        # Include all combinations, even if some pricing components are missing
        # This gives a more complete view of available services
        
        # Concatenate service_code with service_name (as per previous conversation)
        service_name = f"{service_code} - {data['service_name']}" if data['service_name'] else service_code
        
        record = {
            "provider_name": "AZURE",  # Use enum value from schema
            "service_name": service_name,
            "storage_class": storage_class,
            "region": geo_region,
            "access_tier": get_access_tier(storage_class),
            "capacity_price": data["capacity_price"],
            "read_price": data["read_price"],
            "write_price": data["write_price"], 
            "flat_item_price": data["flat_item_price"],
            "other_details": json.dumps(data["other_details"])
        }
        final_records.append(record)
    
    print(f"💾 Writing {len(final_records)} records to CSV...")
    
    # Write to CSV matching StoragePricing schema column order
    if final_records:
        fieldnames = [
            "provider_name", "service_name", "storage_class", "region", "access_tier",
            "capacity_price", "read_price", "write_price", "flat_item_price", "other_details"
        ]
        
        with open("azure_storage_pricing_service_per_row.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(final_records)
        
        print("✅ azure_storage_pricing_service_per_row.csv created successfully!")
        
        # Print summary statistics
        print("\n📈 Summary:")
        print(f"Total records: {len(final_records)}")
        print(f"Unique regions: {len(set(r['region'] for r in final_records))}")
        print(f"Unique storage classes: {len(set(r['storage_class'] for r in final_records))}")
        
        # Access tier breakdown
        tier_counts = {}
        for record in final_records:
            tier = record['access_tier']
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        print("\n🎯 Access tier distribution:")
        for tier, count in tier_counts.items():
            print(f"  {tier}: {count} records")
        
        # Pricing completeness analysis
        print("\n💰 Pricing completeness:")
        capacity_count = sum(1 for r in final_records if r['capacity_price'] is not None)
        read_count = sum(1 for r in final_records if r['read_price'] is not None)
        write_count = sum(1 for r in final_records if r['write_price'] is not None)
        flat_count = sum(1 for r in final_records if r['flat_item_price'] is not None)
        
        print(f"  Records with capacity pricing: {capacity_count}")
        print(f"  Records with read pricing: {read_count}")  
        print(f"  Records with write pricing: {write_count}")
        print(f"  Records with flat monthly pricing: {flat_count}")
            
    else:
        print("❌ No records to write")

if __name__ == "__main__":
    main()
