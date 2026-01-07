#!/usr/bin/env python3
"""Check network names in BigQuery."""
from google.cloud import bigquery
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file('credentials/gcp_service_account.json')
client = bigquery.Client(project='gen-lang-client-0468554395', credentials=credentials)

query = """
SELECT DISTINCT network
FROM `gen-lang-client-0468554395.ad_network_analytics.network_comparison`
WHERE dt = '2026-01-01'
ORDER BY network
"""

result = client.query(query).result()
print('BigQuery network isimleri:')
print('=' * 40)
for row in result:
    print(f'  - {row.network}')
