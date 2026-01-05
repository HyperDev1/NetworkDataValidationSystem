"""Simple Moloco API test."""
import yaml
import json
import requests

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

moloco = config['networks']['moloco']

print("=" * 60)
print("MOLOCO API TEST")
print("=" * 60)

# Get token
auth_url = 'https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/auth/tokens'
auth_response = requests.post(auth_url, json={
    'email': moloco['email'],
    'password': moloco['password'],
    'workplace_id': moloco['platform_id']
}, headers={'Content-Type': 'application/json'})

token = auth_response.json().get('token')
print(f"Token: {'OK' if token else 'FAILED'}")

if not token:
    exit(1)

summary_url = 'https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/sdk/summary'
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
}

# Test 1: Date ranges with UTC_DATE dimension
print("\n" + "=" * 60)
print("TEST 1: Different date ranges with UTC_DATE")
print("=" * 60)

date_ranges = [
    ('2026-01-01', '2026-01-04'),
    ('2025-12-01', '2025-12-31'),
    ('2025-11-01', '2025-11-30'),
]

for start, end in date_ranges:
    payload = {
        'publisher_id': moloco['publisher_id'],
        'date_range': {'start': start, 'end': end},
        'dimensions': ['UTC_DATE'],
        'metrics': ['REVENUE', 'IMPRESSIONS']
    }
    
    response = requests.post(summary_url, headers=headers, json=payload, timeout=30)
    body = response.json()
    rows = body.get('rows', [])
    
    print(f"{start} to {end}: Status={response.status_code}, Rows={len(rows)}")
    if rows:
        print(f"  First row: {rows[0]}")

# Test 2: Different dimensions with fixed date range
print("\n" + "=" * 60)
print("TEST 2: Different dimensions (2025-12-01 to 2025-12-31)")
print("=" * 60)

dimensions_list = [
    ['UTC_DATE'],
    ['AD_UNIT_ID'],
    ['PUBLISHER_APP_ID'],
    ['PUBLISHER_APP_STORE_ID'],
    ['GEO_COUNTRY'],
    ['DEVICE_OS'],  # device.os için olası isim    
    ['AD_TYPE'],    # ad_unit.inventory_type için olası isim
    [],  # No dimensions
]

for dims in dimensions_list:
    payload = {
        'publisher_id': moloco['publisher_id'],
        'date_range': {'start': '2025-12-01', 'end': '2025-12-31'},
        'dimensions': dims,
        'metrics': ['REVENUE', 'IMPRESSIONS']
    }
    
    response = requests.post(summary_url, headers=headers, json=payload, timeout=30)
    body = response.json()
    rows = body.get('rows', [])
    
    dim_str = str(dims) if dims else '(none)'
    print(f"Dimensions {dim_str}: Status={response.status_code}, Rows={len(rows)}")
    if rows:
        print(f"  First row: {rows[0]}")
    if body.get('code'):
        print(f"  Error: {body.get('message', body)}")

# Test 3: Different metrics
print("\n" + "=" * 60)
print("TEST 3: Different metrics (2025-11-01 to 2025-11-31)")
print("=" * 60)

metrics_list = [
    ['REVENUE'],
    ['IMPRESSIONS'],
    ['REQUESTS'],
    ['CLICKS'],
    ['ECPM'],
    ['FILL_RATE'],
    ['REVENUE', 'IMPRESSIONS', 'REQUESTS', 'CLICKS', 'ECPM', 'FILL_RATE'],
]

for mets in metrics_list:
    payload = {
        'publisher_id': moloco['publisher_id'],
        'date_range': {'start': '2025-11-01', 'end': '2025-11-31'},
        'dimensions': ['UTC_DATE'],
        'metrics': mets
    }
    
    response = requests.post(summary_url, headers=headers, json=payload, timeout=30)
    body = response.json()
    rows = body.get('rows', [])
    
    print(f"Metrics {mets}: Status={response.status_code}, Rows={len(rows)}")
    if rows:
        print(f"  First row: {rows[0]}")
    if body.get('code'):
        print(f"  Error: {body.get('message', body)}")


