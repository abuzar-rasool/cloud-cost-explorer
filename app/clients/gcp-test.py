import csv
import json
import re
from googleapiclient.discovery import build
from google.auth import default
from collections import defaultdict

# === HARD-CODED GCP PROJECT ID ===
GCP_PROJECT_ID = "fastapi-461018"  # <<<< REPLACE THIS

SERVICE_ID = "6F81-5844-456A"
CSV_FILENAME = "gcp_cleaned_instances.csv"

# ------------------------------------------
# Fetch SKUs from Cloud Billing API
# ------------------------------------------
def fetch_service_skus(service_id):
    credentials, _ = default()
    service = build("cloudbilling", "v1", credentials=credentials)
    skus = []
    request = service.services().skus().list(parent=f"services/{service_id}")

    while request is not None:
        response = request.execute()
        skus.extend(response.get("skus", []))
        request = service.services().skus().list_next(previous_request=request, previous_response=response)

    return skus

# ------------------------------------------
# Fetch machine type specs from Compute Engine API
# ------------------------------------------
def fetch_machine_specs():
    credentials, _ = default()
    compute = build("compute", "v1", credentials=credentials)
    request = compute.machineTypes().aggregatedList(project=GCP_PROJECT_ID)
    machine_specs = {}

    while request is not None:
        response = request.execute()
        for _, machine_list in response.get("items", {}).items():
            for mt in machine_list.get("machineTypes", []):
                name = mt["name"]
                machine_specs[name] = {
                    "vcpus": mt.get("guestCpus", 0),
                    "memory_gb": round(mt.get("memoryMb", 0) / 1024.0, 2),
                    "arch": "x86_64"  # default assumption
                }
        request = compute.machineTypes().aggregatedList_next(previous_request=request, previous_response=response)

    return machine_specs

# ------------------------------------------
# Parse SKU to desired CSV format
# ------------------------------------------
def parse_vm_details(sku, machine_specs):
    description = sku.get("description", "")
    category = sku.get("category", {})
    resource_group = category.get("resourceGroup", "").lower()
    pricing_info = sku.get("pricingInfo", [])
    regions = sku.get("serviceRegions", [])

    # Try to match VM type based on resourceGroup prefix (e.g., 'n1', 'e2', 'c2')
    matched_vm = None
    for machine_type in machine_specs:
        if machine_type.startswith(resource_group):
            matched_vm = machine_type
            break

    if not matched_vm:
        return None

    specs = machine_specs[matched_vm]
    virtual_cpu_count = specs["vcpus"]
    memory_gb = specs["memory_gb"]
    cpu_arch = specs["arch"]

    # GPU detection
    gpu_count = 0
    gpu_name = ""
    gpu_memory = 0.0
    if "gpu" in description.lower():
        gpu_count = 1
        match = re.search(r'(nvidia[^,\s]*)', description.lower())
        gpu_name = match.group(1).title() if match else "NVIDIA GPU"
        gpu_memory = 16.0  # default assumption

    # Price
    price_per_hour_usd = 0.0
    if pricing_info:
        try:
            unit_price = pricing_info[0]["pricingExpression"]["tieredRates"][0]["unitPrice"]
            units = float(unit_price.get("units", 0) or 0)
            nanos = unit_price.get("nanos", 0) / 1e9
            price_per_hour_usd = round(units + nanos, 5)
        except:
            price_per_hour_usd = 0.0

    # OS
    os_type = "LINUX" if "linux" in description.lower() else (
        "WINDOWS" if "windows" in description.lower() else "OTHER"
    )

    # Region
    region = region_to_continent(regions[0]) if regions else "other"

    # Other metadata
    other_details = json.dumps({
        "resource_group": resource_group,
        "usage_type": category.get("usageType", ""),
        "region_list": regions
    }).replace('"', '""')

    return {
        "vm_name": matched_vm,
        "provider_name": "GCP",
        "virtual_cpu_count": virtual_cpu_count,
        "memory_gb": memory_gb,
        "cpu_arch": cpu_arch,
        "price_per_hour_usd": price_per_hour_usd,
        "gpu_count": gpu_count,
        "gpu_name": gpu_name,
        "gpu_memory": gpu_memory,
        "os_type": os_type,
        "region": region,
        "other_details": f'"{other_details}"'
    }


# ------------------------------------------
# Convert region to continent
# ------------------------------------------
def region_to_continent(region):
    region = region.lower()
    if "us" in region or "northamerica" in region:
        return "north_america"
    elif "southamerica" in region:
        return "south_america"
    elif "europe" in region:
        return "europe"
    elif "asia" in region:
        return "asia"
    elif "australia" in region or "oceania" in region:
        return "oceania"
    elif "africa" in region:
        return "africa"
    elif "antarctica" in region:
        return "antarctica"
    return "other"

# ------------------------------------------
# Save output to CSV
# ------------------------------------------
def save_cleaned_csv(cleaned_data, filename):
    fieldnames = [
        "vm_name", "provider_name", "virtual_cpu_count", "memory_gb",
        "cpu_arch", "price_per_hour_usd", "gpu_count", "gpu_name",
        "gpu_memory", "os_type", "region", "other_details"
    ]
    cleaned_data = sorted(cleaned_data, key=lambda x: (x['virtual_cpu_count'], x['memory_gb']))
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in cleaned_data:
            writer.writerow(row)
    print(f"✅ Cleaned and sorted data saved to {filename}")

# ------------------------------------------
# Main execution
# ------------------------------------------
if __name__ == "__main__":
    print(f"🔍 Fetching real-time SKU data for service ID: {SERVICE_ID}")
    skus = fetch_service_skus(SERVICE_ID)
    print(f"🎯 Total SKUs fetched: {len(skus)}")

    print("🧠 Fetching Compute Engine machine specs...")
    machine_specs = fetch_machine_specs()
    print(f"📦 Total machine types fetched: {len(machine_specs)}")

    print("🧹 Processing and cleaning data...")
    cleaned_data = []
    for sku in skus:
        parsed = parse_vm_details(sku, machine_specs)
        if parsed:
            cleaned_data.append(parsed)

    print(f"✅ Cleaned data ready with {len(cleaned_data)} entries")
    print("💾 Saving cleaned data to CSV...")
    save_cleaned_csv(cleaned_data, CSV_FILENAME)
