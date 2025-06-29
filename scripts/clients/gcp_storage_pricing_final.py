#!/usr/bin/env python3
"""
Fixed version of GCP Storage pricing extractor that properly maps global operations to regional records.
"""

import json
import csv
import re
import os
import sys
from datetime import datetime
from google.auth import default
from googleapiclient.discovery import build
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ─── CONFIG ────────────────────────────────────────────────────────────────────

SERVICE_ID = "95FF-2EF5-5EA1"   # GCP Cloud Storage service ID

CSV_COLUMNS = [
    "provider_name", "service_name", "storage_class", "region",
    "access_tier", "capacity_price", "read_price", "write_price",
    "flat_item_price", "other_details",
]

# GCP region mapping to continents (similar to AWS approach)
GCP_REGION_TO_CONTINENT = {
    # North America
    'us-central1': 'north_america',
    'us-east1': 'north_america',
    'us-east4': 'north_america',
    'us-east5': 'north_america',
    'us-south1': 'north_america',
    'us-west1': 'north_america',
    'us-west2': 'north_america',
    'us-west3': 'north_america',
    'us-west4': 'north_america',
    'northamerica-northeast1': 'north_america',
    'northamerica-northeast2': 'north_america',
    'us': 'north_america',         # US multi-region
    'nam4': 'north_america',       # North America multi-region
    
    # South America
    'southamerica-east1': 'south_america',
    'southamerica-west1': 'south_america',
    
    # Europe
    'europe-central2': 'europe',
    'europe-north1': 'europe',
    'europe-southwest1': 'europe',
    'europe-west1': 'europe',
    'europe-west2': 'europe',
    'europe-west3': 'europe',
    'europe-west4': 'europe',
    'europe-west6': 'europe',
    'europe-west8': 'europe',
    'europe-west9': 'europe',
    'europe-west10': 'europe',
    'europe-west12': 'europe',
    'eu': 'europe',               # Europe multi-region
    'eur4': 'europe',             # Europe multi-region
    'eur5': 'europe',             # Europe multi-region
    'eur7': 'europe',             # Europe multi-region
    'eur8': 'europe',             # Europe multi-region
    'europe': 'europe',             # Europe multi-region
    
    # Asia
    'asia-east1': 'asia',
    'asia-east2': 'asia',
    'asia-northeast1': 'asia',
    'asia-northeast2': 'asia',
    'asia-northeast3': 'asia',
    'asia-south1': 'asia',
    'asia-south2': 'asia',
    'asia-southeast1': 'asia',
    'asia-southeast2': 'asia',
    'me-central1': 'asia',        # Middle East (similar to AWS mapping)
    'me-central2': 'asia',        # Middle East
    'me-west1': 'asia',          # Middle East
    
    # Africa
    'africa-south1': 'africa',
    
    # Oceania
    'australia-southeast1': 'oceania',
    'australia-southeast2': 'oceania',
    
    # Multi-region and special cases
    'asia1': 'asia',              # Asia multi-region
    'asia': 'asia',              # Asia multi-region
    'global': 'global'            # Global (special case)
}

CLASS_MAP = {
    "standard": "STANDARD",
    "nearline": "NEARLINE",
    "coldline": "COLDLINE",
    "archive": "ARCHIVE",
}
TIER_MAP = {
    "STANDARD": "FREQUENT_ACCESS",
    "NEARLINE": "OCCASIONAL_ACCESS",
    "COLDLINE": "RARE_ACCESS",
    "ARCHIVE": "ARCHIVE",
}

# Operation classification maps
WRITE_TERMS = ["class a", "write", "put", "post", "create", "insert", "upload"]
READ_TERMS = ["class b", "read", "get", "list", "retrieve", "download"]

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def to_usd(units, nanos):
    """Convert {units, nanos} -> float USD."""
    try:
        u = float(units)
    except:
        u = 0.0
    try:
        n = float(nanos) * 1e-9
    except:
        n = 0.0
    return round(u + n, 6)

def normalize_class(rg: str) -> str:
    """Map resourceGroup substring to STANDARD/NEARLINE/COLDLINE/ARCHIVE."""
    rg = (rg or "").lower()
    for key, val in CLASS_MAP.items():
        if key in rg:
            return val
    return "STANDARD"

def extract_region_type(desc):
    """Extract region type from description."""
    desc = desc.lower()
    if "multi-region" in desc or "multiregion" in desc:
        return "multi-region"
    elif "dual-region" in desc or "dualregion" in desc:
        return "dual-region" 
    else:
        return "regional"  # Default to regional

def get_continent_from_region(region_code):
    """Map GCP region code to a continent name for standardized output."""
    if not region_code:
        return "global"
        
    # Check direct mapping first
    continent = GCP_REGION_TO_CONTINENT.get(region_code.lower())
    if continent:
        return continent
        
    # Try pattern matching for regions not explicitly listed
    region_lower = region_code.lower()
    
    # Extract the general region from dual/multi region pairs
    if "-" in region_lower and any(x in region_lower for x in ["dual", "pair", "multi"]):
        parts = region_lower.split("-")
        for part in parts:
            # Try each part to see if it maps to a continent
            if part in GCP_REGION_TO_CONTINENT:
                return GCP_REGION_TO_CONTINENT[part]
    
    # Regional pattern matching
    if region_lower.startswith("us-") or "northamerica-" in region_lower:
        return "north_america"
    elif region_lower.startswith("europe-") or "eu-" in region_lower:
        return "europe"
    elif region_lower.startswith("asia-"):
        return "asia"
    elif "australia" in region_lower or "oceania" in region_lower:
        return "oceania"
    elif "southamerica-" in region_lower:
        return "south_america"
    elif "africa-" in region_lower:
        return "africa"
    
    # Multi-region pattern matching
    if region_lower in ["us", "nam4"]:
        return "north_america"
    elif region_lower in ["eu", "eur4"]:
        return "europe"
    elif region_lower == "asia1":
        return "asia"
    
    # Default to global if no match
    logger.warning(f"Could not map region {region_code} to a continent, using 'global'")
    return "global"

def check_directory_permissions(dir_path):
    """Check if we have write permissions to the specified directory."""
    try:
        # Create a temporary file to check write permissions
        test_file = os.path.join(dir_path, ".permission_test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        return True
    except Exception as e:
        logger.error(f"No write permission to directory {dir_path}: {e}")
        return False

def fetch_all_skus():
    """Yields every SKU under our GCS service."""
    try:
        logger.info(f"Authenticating with Google Cloud...")
        creds, project = default()
        logger.info(f"Using credentials for project: {project}")
        
        logger.info(f"Building Cloud Billing client...")
        svc = build("cloudbilling", "v1", credentials=creds, cache_discovery=False)
        
        logger.info(f"Fetching all SKUs for service {SERVICE_ID}...")
        req = svc.services().skus().list(parent=f"services/{SERVICE_ID}", pageSize=500)
        count = 0
        
        while req:
            resp = req.execute()
            batch = resp.get("skus", [])
            count += len(batch)
            logger.info(f"Fetched {len(batch)} SKUs, {count} total so far")
            
            for sku in batch:
                yield sku
                
            req = svc.services().skus().list_next(req, resp)
            
        logger.info(f"Completed fetching {count} SKUs")
            
    except Exception as e:
        logger.error(f"Error fetching SKUs: {e}")
        raise

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def process_capacity_skus(skus):
    """Process capacity pricing SKUs and return base records."""
    records = {}  # key = (region, storage_class)
    capacity_count = 0
    
    logger.info("Processing capacity SKUs...")
    
    for sku in skus:
        cat = sku.get("category", {})
        if cat.get("resourceFamily") != "Storage" or cat.get("usageType") != "OnDemand":
            continue

        pe = sku["pricingInfo"][0]["pricingExpression"]
        unit = pe.get("usageUnit", "").lower()
        
        if "giby.mo" not in unit:  # only per-GiB-month
            continue

        capacity_count += 1
        
        price_per_gib = to_usd(
            pe["tieredRates"][0]["unitPrice"].get("units", 0),
            pe["tieredRates"][0]["unitPrice"].get("nanos", 0),
        )
        
        desc = sku.get("description", "").lower()
        sc = normalize_class(cat.get("resourceGroup", ""))
        svc = f"Google Cloud Storage - {sc.title()}"
        tier = TIER_MAP[sc]

        # Store SKU ID for debugging
        sku_id = sku.get("skuId")
        
        for region in sku.get("serviceRegions", []):
            # Map the GCP region code to a continent name (like AWS format)
            continent = get_continent_from_region(region)
            
            # Store both the original region and the continent in other_details
            details = {
                "sku_id": sku_id, 
                "description": desc,
                "original_region": region
            }
            
            records[(region, sc)] = {
                "provider_name": "GCP",
                "service_name": svc,
                "storage_class": sc,
                "region": continent,  # Use continent instead of region code
                "access_tier": tier,
                "capacity_price": price_per_gib,
                "read_price": "",
                "write_price": "",
                "flat_item_price": "",
                "other_details": json.dumps(details, separators=(",", ":"), ensure_ascii=True),
            }
    
    logger.info(f"Found {capacity_count} capacity SKUs, created {len(records)} base records")
    
    # Group regions by type to help with operation matching, but preserve original region codes
    region_types = {}
    
    # Create a mapping from GCP region codes to continent names to help with lookups
    region_to_continent = {}
    
    for region_key, storage_class in records.keys():
        # Get region type from the original region code (not the continent name)
        region_type = "regional"  # Default
        
        # Store mapping between original region code and continent for later reference
        region_to_continent[region_key] = records[(region_key, storage_class)]["region"]
        
        # Determine region type based on original region code
        if "asia" in region_key.lower() or "europe" in region_key.lower() or any(x in region_key.lower() for x in ["us-", "northamerica-", "southamerica-", "australia-"]):
            region_type = "regional"
        elif "nam" in region_key.lower() or "eur" in region_key.lower() or region_key.lower() in ["us", "eu", "asia1"]:
            region_type = "multi-region"
        
        if region_type not in region_types:
            region_types[region_type] = {}
        
        if storage_class not in region_types[region_type]:
            region_types[region_type][storage_class] = []
            
        region_types[region_type][storage_class].append(region_key)
    
    logger.info(f"Region types: {region_types.keys()}")
    
    return records, region_types

def process_operations_skus(skus, records, region_types):
    """Process operations SKUs to add read/write pricing."""
    operations_found = 0
    class_a_found = 0
    class_b_found = 0
    unclassified_found = 0
    
    # Create maps for tracking applied operations
    applied_write = {}  # (region, storage_class) -> count
    applied_read = {}   # (region, storage_class) -> count
    
    logger.info("Processing operations SKUs...")
    
    for sku in skus:
        cat = sku.get("category", {})
        if cat.get("resourceFamily") != "Storage" or cat.get("usageType") != "OnDemand":
            continue

        desc = sku.get("description", "").lower()
        
        # Skip SKUs that aren't operations
        if not any(term in desc for term in ["operation", "api", "request"]):
            continue
            
        operations_found += 1
        
        # Skip SKUs for Data Transfer or other special operations
        if any(term in desc for term in ["data transfer", "network egress"]):
            continue

        pe = sku["pricingInfo"][0]["pricingExpression"]
        up = pe["tieredRates"][0]["unitPrice"]
        base = to_usd(up.get("units", 0), up.get("nanos", 0))

        # Get the quantity per operation (e.g., per 1000 operations)
        dq = pe.get("displayQuantity")
        if dq is not None:
            qty = int(str(dq).replace(",", ""))
        else:
            # fallback to usageUnitDescription e.g. "1,000 operations"
            udesc = pe.get("usageUnitDescription", "")
            m = re.search(r"([\d,]+)", udesc)
            qty = int(m.group(1).replace(",", "")) if m else 1

        # Convert to price per million operations
        multiplier = 1_000_000 / qty
        ppu = round(base * multiplier, 6)

        # Classify as read or write operation
        if any(term in desc for term in WRITE_TERMS):
            field = "write_price"
            class_a_found += 1
            logger.info(f"Write op: {desc} - {ppu}")
        elif any(term in desc for term in READ_TERMS):
            field = "read_price"
            class_b_found += 1
            logger.info(f"Read op: {desc} - {ppu}")
        else:
            unclassified_found += 1
            logger.info(f"Unclassified op: {desc}")
            continue

        # Extract storage class from description
        storage_class = None
        for class_key in CLASS_MAP:
            if class_key in desc:
                storage_class = CLASS_MAP[class_key]
                break
        
        if storage_class is None:
            # Fall back to category
            storage_class = normalize_class(cat.get("resourceGroup", ""))
        
        # Fix for 'durable reduced availability' -> map to STANDARD
        if "durable reduced availability" in desc:
            storage_class = "STANDARD"
        
        # Determine region type from description
        region_type = extract_region_type(desc)
        logger.info(f"Operation: {desc}, Class: {storage_class}, Region Type: {region_type}")
        
        # Apply operation price to all matching regions of this type and storage class
        applied_count = 0
        
        # Get all regions of this type for this storage class
        matching_regions = region_types.get(region_type, {}).get(storage_class, [])
        
        if not matching_regions:
            logger.info(f"No matching regions found for {region_type} {storage_class}")
            # Try a more flexible approach for regional
            if region_type == "regional":
                for rt in region_types:
                    if rt != "multi-region" and rt != "dual-region":  # Any non-multi/dual region
                        matching_regions.extend(region_types.get(rt, {}).get(storage_class, []))
            
        for region in matching_regions:
            key = (region, storage_class)
            rec = records.get(key)
            if rec:
                rec[field] = ppu
                applied_count += 1
                
                # Track that we've applied this price
                if field == "write_price":
                    applied_write[key] = applied_write.get(key, 0) + 1
                else:
                    applied_read[key] = applied_read.get(key, 0) + 1
        
        logger.info(f"Applied {field} to {applied_count} records for {storage_class} {region_type}")
    
    logger.info(f"Operations: {operations_found} total, {class_a_found} write, {class_b_found} read, {unclassified_found} unclassified")
    logger.info(f"Applied write prices to {sum(applied_write.values())} records")
    logger.info(f"Applied read prices to {sum(applied_read.values())} records")
    
    return records

def process_early_delete_skus(skus, records):
    """Process early delete SKUs to add flat fees."""
    early_delete_count = 0
    applied_count = 0
    
    logger.info("Processing early delete SKUs...")
    
    for sku in skus:
        cat = sku.get("category", {})
        if cat.get("resourceFamily") != "Storage" or cat.get("usageType") != "OnDemand":
            continue

        desc = sku.get("description", "").lower()
        pe = sku["pricingInfo"][0]["pricingExpression"]
        unit = pe.get("usageUnit", "").lower()

        if "giby.d" not in unit and "early delete" not in desc:
            continue

        early_delete_count += 1

        fee = to_usd(
            pe["tieredRates"][0]["unitPrice"].get("units", 0),
            pe["tieredRates"][0]["unitPrice"].get("nanos", 0),
        )
        
        # Extract storage class from description
        storage_class = None
        for class_key in CLASS_MAP:
            if class_key in desc:
                storage_class = CLASS_MAP[class_key]
                break
        
        if storage_class is None:
            # Fall back to category
            storage_class = normalize_class(cat.get("resourceGroup", ""))
        
        # Fix for 'durable reduced availability' -> map to STANDARD
        if "durable reduced availability" in desc:
            storage_class = "STANDARD"

        for region in sku.get("serviceRegions", []):
            key = (region, storage_class)
            rec = records.get(key)
            if rec and rec["flat_item_price"] == "":
                rec["flat_item_price"] = fee
                applied_count += 1
    
    logger.info(f"Found {early_delete_count} early delete SKUs, applied to {applied_count} records")
    return records

def main():
    try:
        # Fetch all SKUs once and store in memory
        logger.info(f"Starting GCP Storage pricing extraction...")
        skus = list(fetch_all_skus())
        logger.info(f"Fetched {len(skus)} total SKUs")
        
        # Process in three passes
        records, region_types = process_capacity_skus(skus)
        records = process_operations_skus(skus, records, region_types)
        records = process_early_delete_skus(skus, records)
        
        # Print summary statistics
        with_write = sum(1 for r in records.values() if r["write_price"] != "")
        with_read = sum(1 for r in records.values() if r["read_price"] != "")
        with_early_delete = sum(1 for r in records.values() if r["flat_item_price"] != "")
        
        logger.info(f"Records with write price: {with_write}/{len(records)}")
        logger.info(f"Records with read price: {with_read}/{len(records)}")
        logger.info(f"Records with early delete price: {with_early_delete}/{len(records)}")
        
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # Check directory permissions
        if not check_directory_permissions(data_dir):
            logger.error(f"Insufficient permissions to write to data directory: {data_dir}")
            sys.exit(1)
        
        # Write CSV output to data folder
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        outfn = f"gcp_storage_on_demand_{timestamp}.csv"
        outpath = os.path.join(data_dir, outfn)
        
        with open(outpath, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_NONNUMERIC)
            w.writeheader()
            w.writerows(records.values())
        
        logger.info(f"✅ Saved {len(records)} records to {outpath}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
