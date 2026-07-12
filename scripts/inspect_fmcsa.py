from automation.sources.fmcsa.downloader import download_company_sample

records = download_company_sample(limit=100)

status_codes = set()
carrier_operations = set()
business_orgs = set()
fleet_sizes = set()

for record in records:
    if record.get("status_code"):
        status_codes.add(record["status_code"])

    if record.get("carrier_operation"):
        carrier_operations.add(record["carrier_operation"])

    if record.get("business_org_desc"):
        business_orgs.add(record["business_org_desc"])

    if record.get("fleetsize"):
        fleet_sizes.add(record["fleetsize"])

print("\nSTATUS CODES")
print(sorted(status_codes))

print("\nCARRIER OPERATIONS")
print(sorted(carrier_operations))

print("\nBUSINESS TYPES")
print(sorted(business_orgs))

print("\nFLEET SIZES")
print(sorted(fleet_sizes))