"""Test Moloco with specific date."""
from datetime import datetime, timedelta
import yaml
import json
import requests

# Output file
output_lines = []

def log(msg):
    print(msg)
    output_lines.append(msg)

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

moloco = config['networks']['moloco']

log("=" * 60)
log("MOLOCO API DEBUG TEST")
log("=" * 60)
log(f"Email: {moloco['email']}")
log(f"Platform ID (auth): {moloco['platform_id']}")
log(f"Publisher ID (API): {moloco['publisher_id']}")

# First get token directly
auth_url = 'https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/auth/tokens'
auth_payload = {
    'email': moloco['email'],
    'password': moloco['password'],
    'workplace_id': moloco['platform_id']
}
log(f"\n1. Auth Request...")
auth_response = requests.post(auth_url, json=auth_payload, headers={'Content-Type': 'application/json'})
log(f"   Status: {auth_response.status_code}")
auth_body = auth_response.json()
token = auth_body.get('token')
log(f"   Token Type: {auth_body.get('token_type')}")
log(f"   Token: {'Yes (' + token[:20] + '...)' if token else 'No'}")

if not token:
    log("   ERROR: No token!")
    with open('moloco_debug.txt', 'w') as f:
        f.write('\n'.join(output_lines))
    exit(1)

summary_url = 'https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/sdk/summary'
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
}

# Test 1: Minimal request
log(f"\n2. Test: Minimal request (no dimensions/metrics)")
payload1 = {
    'publisher_id': moloco['publisher_id'],
    'date_range': {'start': '2024-12-01', 'end': '2024-12-31'}
}
log(f"   Payload: {json.dumps(payload1)}")
r1 = requests.post(summary_url, headers=headers, json=payload1, timeout=30)
log(f"   Status: {r1.status_code}")
log(f"   Response: {r1.text}")

# Test 2: With dimensions only
log(f"\n3. Test: With dimensions only")
payload2 = {
    'publisher_id': moloco['publisher_id'],
    'date_range': {'start': '2024-12-01', 'end': '2024-12-31'},
    'dimensions': ['UTC_DATE']
}
r2 = requests.post(summary_url, headers=headers, json=payload2, timeout=30)
log(f"   Status: {r2.status_code}")
log(f"   Response: {r2.text}")

# Test 3: Without publisher_id
log(f"\n4. Test: Without publisher_id")
payload3 = {
    'date_range': {'start': '2024-12-01', 'end': '2024-12-31'},
    'dimensions': ['UTC_DATE'],
    'metrics': ['REVENUE', 'IMPRESSIONS']
}
r3 = requests.post(summary_url, headers=headers, json=payload3, timeout=30)
log(f"   Status: {r3.status_code}")
log(f"   Response: {r3.text}")

# Test 4: Using platform_id as publisher_id
log(f"\n5. Test: Using platform_id as publisher_id")
payload4 = {
    'publisher_id': moloco['platform_id'],
    'date_range': {'start': '2024-12-01', 'end': '2024-12-31'},
    'dimensions': ['UTC_DATE'],
    'metrics': ['REVENUE', 'IMPRESSIONS']
}
r4 = requests.post(summary_url, headers=headers, json=payload4, timeout=30)
log(f"   Status: {r4.status_code}")
log(f"   Response: {r4.text}")

# Save to file
with open('moloco_debug.txt', 'w') as f:
    f.write('\n'.join(output_lines))
log(f"\n==> Full output saved to moloco_debug.txt")


