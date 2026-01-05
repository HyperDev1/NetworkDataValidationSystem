"""
InMobi API Test - Shows curl command and tests API
"""
import requests

SESSION_URL = 'https://api.inmobi.com/v1.1/generatesession/generate'
username = 'berat@hyperlab.games'
secret_key = 'ZfQIeHaOgQ_ES3QBW_LS8e_aDNgXx0r_DY_gka6-WzrMN9_jDfJP7OY9pAYc_Sk5'

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'userName': username,
    'secretKey': secret_key
}

print('=' * 60)
print('INMOBI SESSION GENERATION TEST')
print('=' * 60)
print()
print('CURL equivalent command:')
print('-' * 60)
print(f'''curl -v "https://api.inmobi.com/v1.1/generatesession/generate" \\
  -X POST \\
  -H "Content-Type: application/json" \\
  -H "Accept: application/json" \\
  -H "userName: {username}" \\
  -H "secretKey: {secret_key}"''')
print()
print('=' * 60)
print('Testing with Python requests (allow_redirects=False)...')
print('=' * 60)

try:
    response = requests.post(SESSION_URL, headers=headers, timeout=30, allow_redirects=False)
    
    print(f'Status Code: {response.status_code}')
    print(f'Response Headers:')
    for k, v in response.headers.items():
        print(f'  {k}: {v}')
    print()
    print(f'Response Body: {response.text[:2000] if response.text else "Empty"}')
    
    if response.status_code in [301, 302, 307, 308]:
        print()
        print(f'[!] REDIRECT detected to: {response.headers.get("Location", "N/A")}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()

