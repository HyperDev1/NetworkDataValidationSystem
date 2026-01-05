"""Direct auth test for Moloco."""
import requests
import json
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

moloco_config = config.get('networks', {}).get('moloco', {})
email = moloco_config.get('email')
password = moloco_config.get('password')
platform_id = moloco_config.get('platform_id')
publisher_id = moloco_config.get('publisher_id')

url = 'https://sdkpubapi.moloco.com/api/adcloud/publisher/v1/auth/tokens'
headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
payload = {
    'email': email,
    'password': password,
    'workplace_id': platform_id  # Auth uses platform_id
}

print('=' * 60)
print('MOLOCO AUTH TEST')
print('=' * 60)
print(f'Email: {email}')
print(f'Platform ID (workplace_id): {platform_id}')
print(f'Publisher ID: {publisher_id}')
print('Request URL:', url)
print('Payload:')
# Mask password
masked_payload = payload.copy()
masked_payload['password'] = '*' * len(password)
print(json.dumps(masked_payload, indent=2))
print()

try:
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print('=' * 60)
    print('RESPONSE')
    print('=' * 60)
    print('Status Code:', response.status_code)
    print()
    
    try:
        body = response.json()
        print('Response Body:')
        # Mask token for display
        display_body = body.copy()
        if 'token' in display_body and display_body['token']:
            display_body['token'] = display_body['token'][:30] + '...'
        print(json.dumps(display_body, indent=2))
        
        # Write to file for full output
        with open('auth_response.json', 'w') as f:
            json.dump({'status': response.status_code, 'body': body}, f, indent=2)
        print('\nFull response saved to auth_response.json')
    except:
        print('Response Text:', response.text[:500])
except Exception as e:
    print('Error:', str(e))

