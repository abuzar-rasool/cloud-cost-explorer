import json
import csv
import re
from googleapiclient.discovery import build
from google.auth import default

# Set your actual GCP project ID
PROJECT_ID = "fastapi-461018"
SERVICE_ID = "6F81-5844-456A"

def fetch_raw_skus(service_id):
    credentials, _ = default()
    billing = build("cloudbilling", "v1", credentials=credentials)
    skus = []
    request = billing.services().skus().list(parent=f"services/{service_id}")

    while request is not None:
        response = request.execute()
        skus.extend(response.get("skus", []))
        request = billing.services().skus().list_next(previous_request=request, previous_response=response)

    return skus

def fetch_raw_machine_specs(project_id):
    credentials, _ = default()
    compute = build("compute", "v1", credentials=credentials)
    request = compute.machineTypes().aggregatedList(project=project_id)

    machines = []
    while request is not None:
        response = request.execute()
        for zone, data in response.get("items", {}).items():
            for machine in data.get("machineTypes", []):
                machine["zone_scope"] = zone
                machines.append(machine)
        request = compute.machineTypes().aggregatedList_next(previous_request=request, previous_response=response)

    return machines

def save_skus_to_csv(skus, filename):
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        header = [
            "name", "description", "machine_name", "category_resourceGroup", "category_usageType",
            "category_serviceDisplayName", "region", "pricing_unit", "price_units", "price_nanos", "price_dollars"
        ]
        writer.writerow(header)

        total_rows = 0
        for sku in skus:
            pricing_info = sku.get("pricingInfo", [])
            price_units = ""
            price_nanos = ""
            pricing_unit = ""
            description = sku.get("description", "")
            
            # Extract machine name from description
            machine_name = extract_machine_name(description)

            if pricing_info:
                pricing_expr = pricing_info[0].get("pricingExpression", {})
                pricing_unit = pricing_expr.get("usageUnit", "")
                tiered_rates = pricing_expr.get("tieredRates", [])
                if tiered_rates:
                    unit_price = tiered_rates[0].get("unitPrice", {})
                    price_units = unit_price.get("units", "")
                    price_nanos = unit_price.get("nanos", "")
            
            # Convert to actual dollars
            price_dollars = convert_price_to_dollars(price_units, price_nanos)
            
            # Get list of regions
            regions = sku.get("serviceRegions", [])
            
            # If no regions, add a row with empty region
            if not regions:
                writer.writerow([
                    sku.get("name"),
                    description,
                    machine_name,
                    sku.get("category", {}).get("resourceGroup"),
                    sku.get("category", {}).get("usageType"),
                    sku.get("category", {}).get("serviceDisplayName"),
                    "",  # Empty region
                    pricing_unit,
                    price_units,
                    price_nanos,
                    f"{price_dollars:.9f}"  # Format with 9 decimal places for precision
                ])
                total_rows += 1
            else:
                # Create a separate row for each region
                for region in regions:
                    writer.writerow([
                        sku.get("name"),
                        description,
                        machine_name,
                        sku.get("category", {}).get("resourceGroup"),
                        sku.get("category", {}).get("usageType"),
                        sku.get("category", {}).get("serviceDisplayName"),
                        region,  # Individual region
                        pricing_unit,
                        price_units,
                        price_nanos,
                        f"{price_dollars:.9f}"  # Format with 9 decimal places for precision
                    ])
                    total_rows += 1

    print(f"Saved raw SKUs to {filename} with {len(skus)} SKUs expanded to {total_rows} rows")

def save_machine_specs_to_csv(machines, filename):
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        header = [
            "name", "machine_name", "description", "guestCpus", "memoryMb", "gpu_count", "vcpu_info", "ram_info",
            "region", "zone", "deprecationStatus", "isSharedCpu"
        ]
        writer.writerow(header)

        for m in machines:
            description = m.get("description", "")
            zone_scope = m.get("zone_scope", "")
            name = m.get("name", "")
            
            # Extract specifications from description
            specs = extract_specs_from_description(description)
            
            # Extract machine name from the instance name format (e.g., "a2-highgpu-1g")
            machine_name = extract_machine_name_from_instance(name)
            
            # If no machine name was extracted from instance name, try from description as fallback
            if not machine_name:
                machine_name = extract_machine_name(description)
            
            # Extract region from zone
            region = extract_region_from_zone(zone_scope)
            
            writer.writerow([
                m.get("name"),
                machine_name,  # Add the extracted machine name
                description,
                m.get("guestCpus"),
                m.get("memoryMb"),
                specs["gpu_count"],
                specs["vcpu_info"] or str(m.get("guestCpus", "")),  # Use API value if not found in description
                specs["ram_info"] or str(round(m.get("memoryMb", 0) / 1024, 2)),  # Convert memoryMb to GB if not found
                region,
                zone_scope,  # Keep original zone for reference
                m.get("deprecated", {}).get("state", ""),
                m.get("isSharedCpu", False)
            ])

    print(f"Saved raw machine specs to {filename} with {len(machines)} entries")

def extract_machine_name(description):
    """Extract machine name from description."""
    if not description:
        return ""
        
    # For machine types that might be part of a larger word (like M4Ultramem224)
    if re.search(r'M1(?:\b|[A-Z])', description):
        return "M1"
    if re.search(r'M2(?:\b|[A-Z])', description):
        return "M2"
    if re.search(r'M3(?:\b|[A-Z])', description):
        return "M3"
    if re.search(r'M4(?:\b|[A-Z])', description):
        return "M4"
    if re.search(r'N1(?:\b|[A-Z])', description):
        return "N1"
    if re.search(r'N2D(?:\b|[A-Z])', description): # Check N2D before N2
        return "N2D"
    if re.search(r'N2(?:\b|[A-Z])', description):
        return "N2"
    if re.search(r'N4(?:\b|[A-Z])', description):
        return "N4"
    if re.search(r'C2D(?:\b|[A-Z])', description): # Check C2D before C2
        return "C2D"
    if re.search(r'C2(?:\b|[A-Z])', description):
        return "C2"
    if re.search(r'C3D(?:\b|[A-Z])', description): # Check C3D before C3
        return "C3D"
    if re.search(r'C3(?:\b|[A-Z])', description):
        return "C3"
    if re.search(r'C4A(?:\b|[A-Z])', description): # Check C4A and C4D before C4
        return "C4A"
    if re.search(r'C4D(?:\b|[A-Z])', description):
        return "C4D"
    if re.search(r'C4(?:\b|[A-Z])', description):
        return "C4"
    if re.search(r'E2(?:\b|[A-Z])', description):
        return "E2"
    if re.search(r'Z3(?:\b|[A-Z])', description):
        return "Z3"
    if re.search(r'H3(?:\b|[A-Z])', description):
        return "H3"
    if re.search(r'X4(?:\b|[A-Z])', description):
        return "X4"
    if re.search(r'A4X(?:\b|[A-Z])', description): # Check A4X before A4
        return "A4X"
    if re.search(r'A4(?:\b|[A-Z])', description):
        return "A4"
    if re.search(r'A3(?:\b|[A-Z])', description):
        return "A3"
    if re.search(r'A2(?:\b|[A-Z])', description):
        return "A2"
    if re.search(r'G2(?:\b|[A-Z])', description):
        return "G2"
    if re.search(r'Tau\s+T2A', description):
        return "Tau T2A"
    if re.search(r'Tau\s+T2D', description):
        return "Tau T2D"
    
    # If nothing matches, return empty string (null)
    return ""

def convert_price_to_dollars(price_units, price_nanos):
    """Convert price units and nanos to dollars."""
    try:
        dollars = float(price_units)
        nanos = float(price_nanos) if price_nanos else 0
        # Convert nanos to dollars (1 nano = 10^-9 dollars)
        return dollars + (nanos * 1e-9)
    except (ValueError, TypeError):
        return 0.0

def extract_specs_from_description(description):
    """Extract GPU, vCPUs, and RAM details from machine description."""
    gpu_count = 0
    vcpu_info = ""
    ram_info = ""
    
    # Extract GPU information
    gpu_match = re.search(r'(\d+)\s+GPU', description, re.IGNORECASE)
    if gpu_match:
        gpu_count = int(gpu_match.group(1))
    
    # Extract vCPU information if not already available
    vcpu_match = re.search(r'(\d+)\s+vCPU', description, re.IGNORECASE)
    if vcpu_match:
        vcpu_info = vcpu_match.group(1)  # Just the number without "vCPUs"
    
    # Extract RAM information
    ram_match = re.search(r'([\d.]+)\s+GB', description, re.IGNORECASE)
    if ram_match:
        ram_info = ram_match.group(1)  # Just the number without "GB"
    
    return {
        "gpu_count": gpu_count,
        "vcpu_info": vcpu_info,
        "ram_info": ram_info
    }

def extract_region_from_zone(zone_scope):
    """Extract region from zone information."""
    if not zone_scope or not isinstance(zone_scope, str):
        return ""
        
    # Remove 'zones/' prefix if present
    zone = zone_scope.replace('zones/', '')
    
    # Extract region (usually first two parts of zone)
    parts = zone.split('-')
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    
    return zone

def extract_machine_name_from_instance(instance_name):
    """Extract machine name from instance name like 'a2-highgpu-1g'."""
    if not instance_name or not isinstance(instance_name, str):
        return ""
    
    # Define patterns to match machine types in instance names
    patterns = [
        (r'^n4-', "N4"),
        (r'^n2d-', "N2D"),
        (r'^n2-', "N2"),
        (r'^n1-', "N1"),
        (r'^c4a-', "C4A"),
        (r'^c4d-', "C4D"),
        (r'^c4-', "C4"),
        (r'^c3d-', "C3D"),
        (r'^c3-', "C3"),
        (r'^e2-', "E2"),
        (r'^t2a-', "Tau T2A"),
        (r'^t2d-', "Tau T2D"),
        (r'^z3-', "Z3"),
        (r'^h3-', "H3"),
        (r'^c2d-', "C2D"),
        (r'^c2-', "C2"),
        (r'^x4-', "X4"),
        (r'^m4-', "M4"),
        (r'^m3-', "M3"),
        (r'^m2-', "M2"),
        (r'^m1-', "M1"),
        (r'^a4x-', "A4X"),
        (r'^a4-', "A4"),
        (r'^a3-', "A3"),
        (r'^a2-', "A2"),
        (r'^g2-', "G2"),
    ]
    
    # Check each pattern
    for pattern, machine_type in patterns:
        if re.search(pattern, instance_name.lower()):
            return machine_type
    
    # If no pattern matches, return empty string
    return ""

if __name__ == "__main__":
    print(f"Fetching real-time SKUs for service ID: {SERVICE_ID}")
    skus = fetch_raw_skus(SERVICE_ID)
    save_skus_to_csv(skus, "raw_skus.csv")

    print(f"Fetching Compute Engine machine specs for project: {PROJECT_ID}")
    machines = fetch_raw_machine_specs(PROJECT_ID)
    save_machine_specs_to_csv(machines, "raw_machine_specs.csv")
