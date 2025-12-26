"""
Test Adjust API connectivity and credentials.
"""
import requests
from datetime import datetime, timedelta

# Your credentials from config
API_TOKEN = "Ar2F9WGnsPJXC-uHq6tW"
APP_TOKEN = "a09civrihyio"

# Test different Adjust API endpoints
endpoints = [
    "https://api.adjust.com/kpis/v1",
    "https://dash.adjust.com/control-center/reports-service/report"
]

# Date range
end_date = datetime.now() - timedelta(days=1)
start_date = end_date

print("=" * 60)
print("Testing Adjust API Connectivity")
print("=" * 60)

for base_url in endpoints:
    print(f"\nTesting endpoint: {base_url}")
    
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }
    
    params = {
        "app_tokens": APP_TOKEN,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "kpis": "revenue,impressions",
        "grouping": "app"
    }
    
    try:
        response = requests.get(
            f"{base_url}/{APP_TOKEN}",
            headers=headers,
            params=params,
            timeout=10
        )
        
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("  ✅ Success!")
            break
        elif response.status_code == 401:
            print("  ❌ Authentication failed - check your API token")
        elif response.status_code == 404:
            print("  ❌ Endpoint not found")
        else:
            print(f"  ❌ Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Connection error: {str(e)}")

print("\n" + "=" * 60)
print("Alternative: Using Adjust Dashboard Export")
print("=" * 60)
print("""
If API is not accessible, you can:
1. Go to Adjust Dashboard: https://dash.adjust.com
2. Navigate to Reports
3. Export data as CSV
4. Use a custom fetcher to read from CSV file

Would you like me to create a CSV-based fetcher?
""")

