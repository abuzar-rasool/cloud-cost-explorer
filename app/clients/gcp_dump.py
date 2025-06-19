import json
import csv
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
            "name", "description", "category_resourceGroup", "category_usageType",
            "category_serviceDisplayName", "region", "pricing_unit", "price_units", "price_nanos"
        ]
        writer.writerow(header)

        for sku in skus:
            pricing_info = sku.get("pricingInfo", [])
            price_units = ""
            price_nanos = ""
            pricing_unit = ""

            if pricing_info:
                pricing_expr = pricing_info[0].get("pricingExpression", {})
                pricing_unit = pricing_expr.get("usageUnit", "")
                tiered_rates = pricing_expr.get("tieredRates", [])
                if tiered_rates:
                    unit_price = tiered_rates[0].get("unitPrice", {})
                    price_units = unit_price.get("units", "")
                    price_nanos = unit_price.get("nanos", "")

            writer.writerow([
                sku.get("name"),
                sku.get("description"),
                sku.get("category", {}).get("resourceGroup"),
                sku.get("category", {}).get("usageType"),
                sku.get("category", {}).get("serviceDisplayName"),
                ", ".join(sku.get("serviceRegions", [])),
                pricing_unit,
                price_units,
                price_nanos
            ])

    print(f"✅ Saved raw SKUs to {filename} with {len(skus)} entries")

def save_machine_specs_to_csv(machines, filename):
    with open(filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        header = [
            "name", "description", "guestCpus", "memoryMb", "zone", "deprecationStatus", "isSharedCpu"
        ]
        writer.writerow(header)

        for m in machines:
            writer.writerow([
                m.get("name"),
                m.get("description"),
                m.get("guestCpus"),
                m.get("memoryMb"),
                m.get("zone_scope"),
                m.get("deprecated", {}).get("state", ""),
                m.get("isSharedCpu", False)
            ])

    print(f"✅ Saved raw machine specs to {filename} with {len(machines)} entries")

if __name__ == "__main__":
    print(f"🔍 Fetching real-time SKUs for service ID: {SERVICE_ID}")
    skus = fetch_raw_skus(SERVICE_ID)
    save_skus_to_csv(skus, "raw_skus.csv")

    print(f"🧠 Fetching Compute Engine machine specs for project: {PROJECT_ID}")
    machines = fetch_raw_machine_specs(PROJECT_ID)
    save_machine_specs_to_csv(machines, "raw_machine_specs.csv")
