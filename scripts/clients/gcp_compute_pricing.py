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
            "category_serviceDisplayName", "region", "pricing_unit", "price_units", "price_nanos", 
            "price_dollars_hourly", "os_type"
        ]
        writer.writerow(header)

        total_rows = 0
        filtered_skus = 0
        for sku in skus:
            # Check if this is an OnDemand SKU
            usage_type = sku.get("category", {}).get("usageType", "")
            if "OnDemand" not in usage_type:
                filtered_skus += 1
                continue
                
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
            
            # Check if we need to convert the price to hourly rate
            # GCP pricing can be in different units (h = hourly, mo = monthly, etc.)
            if pricing_unit == "mo":  # Monthly price
                # Convert monthly price to hourly (divide by average hours in month)
                price_dollars = price_dollars / (30.44 * 24)  # 30.44 average days per month * 24 hours
            elif pricing_unit == "d":  # Daily price
                # Convert daily price to hourly
                price_dollars = price_dollars / 24
            # Other units like 'GiBy.h' (GiB per hour) don't need conversion for hourly rate
            
            # Determine OS type
            resource_group = sku.get("category", {}).get("resourceGroup", "")
            os_type = determine_os_type(resource_group, description)
            
            # Get list of regions
            regions = sku.get("serviceRegions", [])
            
            # If no regions, add a row with empty region
            if not regions:
                writer.writerow([
                    sku.get("name"),
                    description,
                    machine_name,
                    resource_group,
                    sku.get("category", {}).get("usageType"),
                    sku.get("category", {}).get("serviceDisplayName"),
                    "",  # Empty region
                    pricing_unit,
                    price_units,
                    price_nanos,
                    f"{price_dollars:.9f}",  # Format with 9 decimal places for precision - hourly price in USD
                    os_type
                ])
                total_rows += 1
            else:
                # Create a separate row for each region
                for region in regions:
                    writer.writerow([
                        sku.get("name"),
                        description,
                        machine_name,
                        resource_group,
                        sku.get("category", {}).get("usageType"),
                        sku.get("category", {}).get("serviceDisplayName"),
                        region,  # Individual region
                        pricing_unit,
                        price_units,
                        price_nanos,
                        f"{price_dollars:.9f}",  # Format with 9 decimal places for precision - hourly price in USD
                        os_type
                    ])
                    total_rows += 1

    print(f"Saved raw SKUs to {filename} with {total_rows} rows (filtered out {filtered_skus} non-OnDemand SKUs from {len(skus)} total SKUs)")

def save_machine_specs_to_csv(machines, filename):
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        header = [
            "name", "machine_name", "description", "guestCpus", "memoryMb", "gpu_count", "gpu_name", "gpu_memory_per_gpu", "vcpu_info", "ram_info",
            "region", "zone", "deprecationStatus", "isSharedCpu", "cpu_arch"
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
            
            # Determine CPU architecture
            cpu_arch = determine_cpu_architecture(name, description)
            
            writer.writerow([
                m.get("name"),
                machine_name,  # Add the extracted machine name
                description,
                m.get("guestCpus"),
                m.get("memoryMb"),
                specs["gpu_count"],
                specs["gpu_name"],  # Add the GPU name
                specs["gpu_memory"],  # Memory per GPU in GiB
                specs["vcpu_info"] or str(m.get("guestCpus", "")),  # Use API value if not found in description
                specs["ram_info"] or str(round(m.get("memoryMb", 0) / 1024, 2)),  # Convert memoryMb to GB if not found
                region,
                zone_scope,  # Keep original zone for reference
                m.get("deprecated", {}).get("state", ""),
                m.get("isSharedCpu", False),
                cpu_arch  # Add CPU architecture
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
    """
    Convert GCP pricing units and nanos to dollars.
    
    GCP pricing data consists of two parts:
    - price_units: The whole dollar amount
    - price_nanos: The fractional amount in nano units (1 nano = 10^-9 dollars)
    
    For example, a price of $1.023 would be represented as:
    - price_units: "1"
    - price_nanos: "23000000" (0.023 dollars in nanos)
    
    Returns:
        The price in dollars as a float
    """
    try:
        dollars = float(price_units) if price_units else 0
        nanos = float(price_nanos) if price_nanos else 0
        # Convert nanos to dollars (1 nano = 10^-9 dollars)
        return dollars + (nanos * 1e-9)
    except (ValueError, TypeError):
        return 0.0

def extract_specs_from_description(description):
    """
    Extract GPU, vCPUs, and RAM details from machine description.
    
    Returns a dictionary with:
    - gpu_count: Number of GPUs
    - vcpu_info: vCPU count as a string
    - ram_info: RAM size as a string (in GB)
    - gpu_name: The name/model of the GPU
    - gpu_memory: Memory size per GPU in GiB (not total)
    """
    gpu_count = 0
    vcpu_info = ""
    ram_info = ""
    gpu_name = ""
    gpu_memory = 0.0
    
    # Extract GPU information
    gpu_match = re.search(r'(\d+)\s+GPU', description, re.IGNORECASE)
    if gpu_match:
        gpu_count = int(gpu_match.group(1))
        
        # If GPU is present, try to extract the GPU model name
        # Look for common NVIDIA GPU models used in GCP
        gpu_model_patterns = [
            (r'NVIDIA\s+Tesla\s+[A-Za-z0-9]+', lambda m: m.group(0)),  # NVIDIA Tesla X
            (r'NVIDIA\s+Tesla\s+[A-Za-z]\d+', lambda m: m.group(0)),   # NVIDIA Tesla V100, T4, etc.
            (r'NVIDIA\s+[A-Za-z]\d+', lambda m: m.group(0)),           # NVIDIA V100, T4, etc.
            (r'NVIDIA\s+H100', lambda m: "NVIDIA H100"),               # NVIDIA H100
            (r'NVIDIA\s+A100', lambda m: "NVIDIA A100"),               # NVIDIA A100
            (r'NVIDIA\s+P100', lambda m: "NVIDIA P100"),               # NVIDIA P100
            (r'NVIDIA\s+P4', lambda m: "NVIDIA P4"),                   # NVIDIA P4
            (r'NVIDIA\s+T4', lambda m: "NVIDIA T4"),                   # NVIDIA T4
            (r'NVIDIA\s+V100', lambda m: "NVIDIA V100"),               # NVIDIA V100
            (r'NVIDIA\s+K80', lambda m: "NVIDIA K80"),                 # NVIDIA K80
            (r'NVIDIA\s+L4', lambda m: "NVIDIA L4")                    # NVIDIA L4
        ]
        
        # Try to match any of the GPU model patterns
        for pattern, extract_func in gpu_model_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                gpu_name = extract_func(match)
                break
        
        # If no specific model is found but we know GPUs exist, use a generic name
        if gpu_count > 0 and not gpu_name:
            gpu_name = "NVIDIA GPU"  # Default to generic NVIDIA GPU
            
        # Try to extract GPU memory from description
        gpu_memory_match = re.search(r'(\d+)\s*GB\s+GPU', description, re.IGNORECASE)
        if gpu_memory_match:
            # If description specifies GPU memory (e.g., "4 NVIDIA V100 16GB GPU")
            gpu_memory = float(gpu_memory_match.group(1))
        else:
            # Otherwise, calculate based on GPU model
            gpu_memory = get_gpu_memory_size(gpu_name)
    
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
        "ram_info": ram_info,
        "gpu_name": gpu_name,
        "gpu_memory": gpu_memory
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

def determine_os_type(resource_group, description):
    """
    Determine the OS type (LINUX, WINDOWS, OTHER) based on the category_resourceGroup and description.
    
    Args:
        resource_group: The category_resourceGroup value from the SKU
        description: The description of the SKU
    
    Returns:
        String: "LINUX", "WINDOWS", or "OTHER"
    """
    if not resource_group and not description:
        return "OTHER"
    
    # Convert to lowercase for case-insensitive matching
    resource_lower = str(resource_group).lower() if resource_group else ""
    desc_lower = str(description).lower() if description else ""
    
    # Check for Windows indicators
    if any(win_term in resource_lower or win_term in desc_lower for win_term in 
           ["windows", "win", "windows_", "windows-"]):
        return "WINDOWS"
    
    # Check for Linux indicators
    if any(linux_term in resource_lower or linux_term in desc_lower for linux_term in 
           ["linux", "ubuntu", "debian", "centos", "rhel", "sles", "linux_", "linux-"]):
        return "LINUX"
    
    # For GCP Compute Engine, most non-Windows instances are Linux by default
    if "compute" in resource_lower and "instance" in resource_lower and "windows" not in resource_lower:
        return "LINUX"
    
    # Default to OTHER if we can't determine
    return "OTHER"

def determine_cpu_architecture(machine_name, description):
    """
    Determine the CPU architecture based on machine name and description.
    
    Args:
        machine_name: The name of the machine type (e.g., "a2-highgpu-1g")
        description: The description of the machine
    
    Returns:
        String: "ARM64" or "x86_64"
    """
    # Convert to lowercase for case-insensitive matching
    name_lower = str(machine_name).lower() if machine_name else ""
    desc_lower = str(description).lower() if description else ""
    
    # Check for ARM64 indicators
    # T2A instances are ARM-based (Ampere Altra CPUs)
    if any(arm_pattern in name_lower for arm_pattern in ["t2a-", "arm"]) or "t2a" in desc_lower or "ampere" in desc_lower or "altra" in desc_lower:
        return "ARM64"
    
    # Most other GCP instances are Intel/AMD x86_64 based
    return "x86_64"

def get_gpu_memory_size(gpu_name):
    """
    Get the memory size (in GiB) for a specific GPU model.
    
    Args:
        gpu_name: The name of the GPU model (e.g., "NVIDIA T4", "NVIDIA A100")
    
    Returns:
        Float: The memory size in GiB per GPU
    """
    # Mapping of GPU models to their memory sizes in GiB
    gpu_memory_map = {
        "NVIDIA K80": 12.0,        # K80 has 12 GiB
        "NVIDIA P4": 8.0,          # P4 has 8 GiB
        "NVIDIA P100": 16.0,       # P100 has 16 GiB
        "NVIDIA T4": 16.0,         # T4 has 16 GiB
        "NVIDIA V100": 16.0,       # Standard V100 has 16 GiB (some have 32)
        "NVIDIA A100": 40.0,       # A100 has 40 GiB (some have 80)
        "NVIDIA H100": 80.0,       # H100 has 80 GiB
        "NVIDIA L4": 24.0,         # L4 has 24 GiB
        "NVIDIA A10G": 24.0,       # A10G has 24 GiB
        "NVIDIA A4500": 20.0,      # A4500 has 20 GiB
        "NVIDIA A40": 48.0,        # A40 has 48 GiB
    }
    
    # If the GPU name contains any of the keys in the map, return the memory size
    if not gpu_name:
        return 0.0
    
    # Handle specific cases where GPU name might have variations
    gpu_name_clean = gpu_name.strip().upper()
    
    # Check for exact matches first
    for model, memory in gpu_memory_map.items():
        if model.upper() in gpu_name_clean:
            return memory
    
    # If we can't find an exact match, check for partial matches
    if "A100" in gpu_name_clean:
        return 40.0  # Default for A100 if not specified
    elif "V100" in gpu_name_clean:
        return 16.0  # Default for V100 if not specified
    elif "H100" in gpu_name_clean:
        return 80.0  # Default for H100
    elif "L4" in gpu_name_clean:
        return 24.0  # Default for L4
    elif "T4" in gpu_name_clean:
        return 16.0  # Default for T4
    elif "P4" in gpu_name_clean:
        return 8.0   # Default for P4
    elif "P100" in gpu_name_clean:
        return 16.0  # Default for P100
    elif "K80" in gpu_name_clean:
        return 12.0  # Default for K80
    elif "A40" in gpu_name_clean:
        return 48.0  # Default for A40
    
    # If still no match, default to a conservative value if we know it's an NVIDIA GPU
    if "NVIDIA" in gpu_name_clean:
        return 8.0  # Conservative default
        
    # If we can't determine the GPU model, return 0
    return 0.0

def map_region_to_continent(gcp_region):
    """
    Maps a GCP region to its corresponding geographical continent.
    
    Args:
        gcp_region: GCP region string (e.g., 'us-central1', 'europe-west1')
    
    Returns:
        String: Continent name from the enum: north_america, south_america, europe, asia, africa, oceania, antarctica
    """
    if not gcp_region:
        return ""
    
    # Convert to lowercase for consistent matching
    region_lower = gcp_region.lower()
    
    # North America regions
    if any(na_region in region_lower for na_region in [
        "us-", "northamerica-", "us-central", "us-east", "us-west", "us-south", 
        "canada-", "montreal", "toronto", "iowa", "virginia", "oregon", "mexico"
    ]):
        return "north_america"
    
    # South America regions
    if any(sa_region in region_lower for sa_region in [
        "southamerica-", "brazil-", "sao-paulo", "santiago"
    ]):
        return "south_america"
    
    # Europe regions
    if any(eu_region in region_lower for eu_region in [
        "europe-", "eu-", "london", "frankfurt", "netherlands", "belgium", "finland", 
        "warsaw", "zurich", "milan", "paris", "madrid", "stockholm"
    ]):
        return "europe"
    
    # Asia regions
    if any(asia_region in region_lower for asia_region in [
        "asia-", "tokyo", "osaka", "seoul", "hongkong", "mumbai", "delhi", "singapore", 
        "jakarta", "taiwan", "bangkok", "dubai", "qatar", "israel", "doha", "china", 
        "beijing", "shanghai", "shenzhen"
    ]):
        return "asia"
    
    # Africa regions
    if any(africa_region in region_lower for africa_region in [
        "africa-", "southafrica-", "johannesburg", "lagos", "nairobi", "cairo"
    ]):
        return "africa"
    
    # Oceania regions
    if any(oceania_region in region_lower for oceania_region in [
        "australia-", "sydney", "melbourne", "perth", "canberra", "brisbane",
        "newzealand-", "auckland", "wellington", "oceania-"
    ]):
        return "oceania"
    
    # Antarctica (unlikely to have cloud regions, but included for completeness)
    if "antarctica" in region_lower:
        return "antarctica"
    
    # If no match found, try to extract continent from region prefix
    if region_lower.startswith("us") or region_lower.startswith("ca") or region_lower.startswith("na"):
        return "north_america"
    elif region_lower.startswith("sa") or region_lower.startswith("br"):
        return "south_america"
    elif region_lower.startswith("eu"):
        return "europe"
    elif region_lower.startswith("as") or region_lower.startswith("jp") or region_lower.startswith("kr") or region_lower.startswith("sg"):
        return "asia"
    elif region_lower.startswith("af") or region_lower.startswith("za"):
        return "africa"
    elif region_lower.startswith("au") or region_lower.startswith("nz") or region_lower.startswith("oc"):
        return "oceania"
    
    # If still no match, return the original region (default fallback)
    return "other"

def join_and_format_data(machine_specs_file, skus_file, output_file):
    """
    Join raw_machine_specs.csv and raw_skus.csv based on machine_name and region,
    and format the output according to the specified field mappings.
    
    Args:
        machine_specs_file: Path to the raw_machine_specs.csv file
        skus_file: Path to the raw_skus.csv file
        output_file: Path where the joined data will be saved
    """
    # Read the machine specs CSV
    machine_specs = []
    with open(machine_specs_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            machine_specs.append(row)
    
    # Read the SKUs CSV
    skus = []
    with open(skus_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            skus.append(row)
    
    # Create a lookup dictionary for SKUs based on machine_name and region
    # This will help us quickly find matching SKUs for each machine spec
    sku_lookup = {}
    for sku in skus:
        # Create a composite key of machine_name and region
        key = (sku.get("machine_name", ""), sku.get("region", ""))
        
        # We might have multiple SKUs for the same machine_name and region (different OS types)
        if key not in sku_lookup:
            sku_lookup[key] = []
        sku_lookup[key].append(sku)
    
    # Prepare the output data
    joined_data = []
    
    # Process each machine spec
    for machine in machine_specs:
        # Extract the machine name and region to look up in SKUs
        machine_name = machine.get("machine_name", "")
        region = machine.get("region", "")
        
        # Look up matching SKUs
        matching_skus = sku_lookup.get((machine_name, region), [])
        
        # If no matching SKUs, we'll still include the machine in the output with null pricing
        if not matching_skus:
            # Create a single record without pricing info
            record = create_output_record(machine, None)
            joined_data.append(record)
        else:
            # For each matching SKU (different OS types), create a separate record
            for sku in matching_skus:
                record = create_output_record(machine, sku)
                joined_data.append(record)
    
    # Write the joined data to CSV
    with open(output_file, "w", newline='', encoding="utf-8") as f:
        # Define the output fields according to the mapping
        fields = [
            "vm_name", "provider_name", "virtual_cpu_count", "memory_gb", "cpu_arch",
            "price_per_hour_usd", "gpu_count", "gpu_name", "gpu_memory", "os_type", 
            "region", "other_details"
        ]
        
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(joined_data)
    
    print(f"Joined data saved to {output_file} with {len(joined_data)} records")

def create_output_record(machine, sku):
    """
    Create an output record according to the field mapping.
    
    Args:
        machine: A machine spec record from raw_machine_specs.csv
        sku: A SKU record from raw_skus.csv, or None if no matching SKU
    
    Returns:
        A dictionary containing the mapped fields
    """
    # Extract and convert fields from the machine spec
    try:
        vcpu_count = int(machine.get("vcpu_info", "0") or machine.get("guestCpus", "0"))
    except ValueError:
        vcpu_count = 0
    
    try:
        memory_gb = float(machine.get("ram_info", "0") or str(round(float(machine.get("memoryMb", "0")) / 1024, 2)))
    except ValueError:
        memory_gb = 0.0
    
    try:
        gpu_count = int(machine.get("gpu_count", "0"))
    except ValueError:
        gpu_count = 0
    
    try:
        gpu_memory = float(machine.get("gpu_memory_per_gpu", "0"))
    except ValueError:
        gpu_memory = 0.0
    
    # Create a record with fields from machine_specs
    # Map the GCP region to a continent
    gcp_region = machine.get("region", "")
    continent = map_region_to_continent(gcp_region)
    
    record = {
        "vm_name": machine.get("name", ""),
        "provider_name": "GCP",
        "virtual_cpu_count": vcpu_count,
        "memory_gb": memory_gb,
        "cpu_arch": machine.get("cpu_arch", "x86_64"),  # Default to x86_64 if not specified
        "gpu_count": gpu_count,
        "gpu_name": machine.get("gpu_name", ""),
        "gpu_memory": gpu_memory,
        "region": continent,  # Use the mapped continent instead of raw GCP region
        "other_details": json.dumps({
            "zone": machine.get("zone", ""),
            "gcp_region": gcp_region,  # Store the original GCP region in other_details
            "description": machine.get("description", ""),
            "deprecationStatus": machine.get("deprecationStatus", ""),
            "isSharedCpu": machine.get("isSharedCpu", "False") == "True"
        })
    }
    
    # Add fields from the SKU if available
    if sku:
        try:
            price_per_hour = float(sku.get("price_dollars_hourly", "0"))
        except ValueError:
            price_per_hour = 0.0
        
        record["price_per_hour_usd"] = price_per_hour
        record["os_type"] = sku.get("os_type", "OTHER")
    else:
        # Default values if no matching SKU
        record["price_per_hour_usd"] = 0.0
        record["os_type"] = "OTHER"
    
    return record

def process_and_save_consolidated_data(skus, machines, output_file):
    """
    Process raw SKUs and machine specs data in memory and save directly to the consolidated output file
    without creating intermediate CSV files.
    
    Args:
        skus: List of raw SKU dictionaries from the GCP Billing API
        machines: List of raw machine dictionaries from the GCP Compute API
        output_file: Path where the consolidated data will be saved
    """
    print("Processing raw data and generating consolidated file...")
    
    # Process SKUs to extract relevant information
    processed_skus = []
    filtered_skus = 0
    
    for sku in skus:
        # Check if this is an OnDemand SKU
        usage_type = sku.get("category", {}).get("usageType", "")
        if "OnDemand" not in usage_type:
            filtered_skus += 1
            continue
            
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
        
        # Check if we need to convert the price to hourly rate
        if pricing_unit == "mo":  # Monthly price
            price_dollars = price_dollars / (30.44 * 24)  # 30.44 average days per month * 24 hours
        elif pricing_unit == "d":  # Daily price
            price_dollars = price_dollars / 24
        
        # Determine OS type
        resource_group = sku.get("category", {}).get("resourceGroup", "")
        os_type = determine_os_type(resource_group, description)
        
        # Get list of regions
        regions = sku.get("serviceRegions", [])
        
        # If no regions, add with empty region
        if not regions:
            processed_skus.append({
                "name": sku.get("name"),
                "description": description,
                "machine_name": machine_name,
                "category_resourceGroup": resource_group,
                "category_usageType": sku.get("category", {}).get("usageType"),
                "category_serviceDisplayName": sku.get("category", {}).get("serviceDisplayName"),
                "region": "",
                "pricing_unit": pricing_unit,
                "price_units": price_units,
                "price_nanos": price_nanos,
                "price_dollars_hourly": price_dollars,
                "os_type": os_type
            })
        else:
            # Create a separate entry for each region
            for region in regions:
                processed_skus.append({
                    "name": sku.get("name"),
                    "description": description,
                    "machine_name": machine_name,
                    "category_resourceGroup": resource_group,
                    "category_usageType": sku.get("category", {}).get("usageType"),
                    "category_serviceDisplayName": sku.get("category", {}).get("serviceDisplayName"),
                    "region": region,
                    "pricing_unit": pricing_unit,
                    "price_units": price_units,
                    "price_nanos": price_nanos,
                    "price_dollars_hourly": price_dollars,
                    "os_type": os_type
                })
    
    print(f"Processed {len(processed_skus)} SKUs (filtered out {filtered_skus} non-OnDemand SKUs from {len(skus)} total SKUs)")
    
    # Process machine specs
    processed_machines = []
    
    for m in machines:
        description = m.get("description", "")
        zone_scope = m.get("zone_scope", "")
        name = m.get("name", "")
        
        # Extract specifications from description
        specs = extract_specs_from_description(description)
        
        # Extract machine name from the instance name format
        machine_name = extract_machine_name_from_instance(name)
        
        # If no machine name was extracted from instance name, try from description as fallback
        if not machine_name:
            machine_name = extract_machine_name(description)
        
        # Extract region from zone
        region = extract_region_from_zone(zone_scope)
        
        # Determine CPU architecture
        cpu_arch = determine_cpu_architecture(name, description)
        
        processed_machines.append({
            "name": m.get("name"),
            "machine_name": machine_name,
            "description": description,
            "guestCpus": m.get("guestCpus"),
            "memoryMb": m.get("memoryMb"),
            "gpu_count": specs["gpu_count"],
            "gpu_name": specs["gpu_name"],
            "gpu_memory_per_gpu": specs["gpu_memory"],
            "vcpu_info": specs["vcpu_info"] or str(m.get("guestCpus", "")),
            "ram_info": specs["ram_info"] or str(round(m.get("memoryMb", 0) / 1024, 2)),
            "region": region,
            "zone": zone_scope,
            "deprecationStatus": m.get("deprecated", {}).get("state", ""),
            "isSharedCpu": m.get("isSharedCpu", False),
            "cpu_arch": cpu_arch
        })
    
    print(f"Processed {len(processed_machines)} machine specs")
    
    # Create a lookup dictionary for SKUs based on machine_name and region
    sku_lookup = {}
    for sku in processed_skus:
        key = (sku.get("machine_name", ""), sku.get("region", ""))
        if key not in sku_lookup:
            sku_lookup[key] = []
        sku_lookup[key].append(sku)
    
    # Prepare the output data
    joined_data = []
    
    # Process each machine spec
    for machine in processed_machines:
        machine_name = machine.get("machine_name", "")
        region = machine.get("region", "")  # This is the original GCP region code
        
        # Look up matching SKUs
        matching_skus = sku_lookup.get((machine_name, region), [])
        
        # If no matching SKUs, include the machine with null pricing
        if not matching_skus:
            record = create_output_record(machine, None)
            joined_data.append(record)
        else:
            # For each matching SKU (different OS types), create a separate record
            for sku in matching_skus:
                record = create_output_record(machine, sku)
                joined_data.append(record)
    
    # Write the joined data to CSV
    with open(output_file, "w", newline='', encoding="utf-8") as f:
        # Define the output fields according to the mapping
        fields = [
            "vm_name", "provider_name", "virtual_cpu_count", "memory_gb", "cpu_arch",
            "price_per_hour_usd", "gpu_count", "gpu_name", "gpu_memory", "os_type", 
            "region", "other_details"
        ]
        
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(joined_data)
    
    print(f"Consolidated data saved to {output_file} with {len(joined_data)} records")

if __name__ == "__main__":
    print(f"Fetching real-time SKUs for service ID: {SERVICE_ID}")
    skus = fetch_raw_skus(SERVICE_ID)
    
    print(f"Fetching Compute Engine machine specs for project: {PROJECT_ID}")
    machines = fetch_raw_machine_specs(PROJECT_ID)
    
    # Process data and generate consolidated file directly
    process_and_save_consolidated_data(skus, machines, "gcp_compute_pricing.csv")
