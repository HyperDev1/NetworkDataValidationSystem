"""Test Moloco inventory type dimension."""
import yaml
import json
import requests

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

moloco = config['networks']['moloco']

# Get token
auth_url = 'https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/auth/tokens'
auth_response = requests.post(auth_url, json={
    'email': moloco['email'],
    'password': moloco['password'],
    'workplace_id': moloco['platform_id']
}, headers={'Content-Type': 'application/json'})

token = auth_response.json().get('token')
print(f"Token: {'OK' if token else 'FAILED'}")

summary_url = 'https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/sdk/summary'
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
}

# Test different dimensions to get ad type info
dimensions_to_test = [
    ['DEVICE_OS', 'INVENTORY_TYPE'],
]

print("\n" + "=" * 60)
print("Testing DEVICE_OS + INVENTORY_TYPE for ad type breakdown")
print("=" * 60)

for dims in dimensions_to_test:
    payload = {
        'publisher_id': moloco['publisher_id'],
        'date_range': {'start': '2026-01-04', 'end': '2026-01-04'},
        'dimensions': dims,
        'metrics': ['REVENUE', 'IMPRESSIONS']
    }
    
    response = requests.post(summary_url, headers=headers, json=payload, timeout=30)
    body = response.json()
    rows = body.get('rows', [])
    
    print(f"\nDimensions {dims}: Status={response.status_code}, Rows={len(rows)}")
    if rows:
        print(f"  First row: {json.dumps(rows[0], indent=2)}")
    if body.get('code'):
        print(f"  Error: {body.get('message', body)}")

