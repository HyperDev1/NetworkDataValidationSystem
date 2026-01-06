#!/usr/bin/env python3
"""
Migration script to update network names in BigQuery.
Updates old network names to new standardized naming convention.

Usage:
    # Dry-run (show what would be updated)
    python scripts/migrate_network_names.py --dry-run
    
    # Execute migration
    python scripts/migrate_network_names.py --execute
"""
import argparse
import os
import sys
from google.cloud import bigquery
from google.oauth2 import service_account

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config

# Network name mapping: old_name -> new_name
NETWORK_NAME_MAPPING = {
    # Case-insensitive mappings (lowercase keys)
    'unity': 'Unity Bidding',
    'unity ads': 'Unity Bidding',
    'ironsource': 'IronSource Bidding',
    'applovin': 'Applovin Bidding',
    'applovin exchange': 'Applovin Exchange',
    'applovin network': 'Applovin Bidding',
    'appLovin': 'Applovin Bidding',
    'applovin max': 'Applovin MAX',
    'bidmachine': 'BidMachine Bidding',
    'mintegral': 'Mintegral Bidding',
    'fyber': 'DT Exchange Bidding',
    'dt exchange': 'DT Exchange Bidding',
    'inmobi': 'InMobi Bidding',
    'vungle': 'Liftoff Monetize Bidding',
    'liftoff': 'Liftoff Monetize Bidding',
    'tiktok': 'Pangle Bidding',
    'pangle': 'Pangle Bidding',
    'moloco': 'Moloco Bidding',
    'facebook': 'Meta Bidding',
    'facebook network': 'Meta Bidding',
    'meta': 'Meta Bidding',
    'meta audience network': 'Meta Bidding',
    'admob': 'Google Bidding',
    'google admob': 'Google Bidding',
    'chartboost': 'Chartboost Bidding',
    'google ad manager': 'Google Ad Manager',
    'google ad manager network': 'Google Ad Manager',
}


def get_bigquery_client(config: Config) -> bigquery.Client:
    """Create BigQuery client from config."""
    gcp_config = config.get('gcp', {})
    service_account_path = gcp_config.get('service_account_path', 'credentials/gcp_service_account.json')
    project_id = gcp_config.get('project_id')
    
    if service_account_path and os.path.exists(service_account_path):
        credentials = service_account.Credentials.from_service_account_file(service_account_path)
        return bigquery.Client(project=project_id, credentials=credentials)
    else:
        return bigquery.Client(project=project_id)


def get_current_network_names(client: bigquery.Client, table_id: str) -> list:
    """Get list of distinct network names currently in the table."""
    query = f"""
    SELECT DISTINCT network, COUNT(*) as count
    FROM `{table_id}`
    GROUP BY network
    ORDER BY count DESC
    """
    
    results = client.query(query).result()
    return [(row.network, row.count) for row in results]


def generate_update_query(table_id: str) -> str:
    """Generate SQL UPDATE query for network name migration."""
    
    # Build CASE statement for network name mapping
    case_statements = []
    for old_name, new_name in NETWORK_NAME_MAPPING.items():
        # Use LOWER() for case-insensitive matching
        case_statements.append(f"WHEN LOWER(network) = '{old_name.lower()}' THEN '{new_name}'")
    
    case_sql = "\n        ".join(case_statements)
    
    query = f"""
    UPDATE `{table_id}`
    SET network = CASE
        {case_sql}
        ELSE network
    END
    WHERE LOWER(network) IN ({', '.join([f"'{k.lower()}'" for k in NETWORK_NAME_MAPPING.keys()])})
    """
    
    return query


def dry_run(client: bigquery.Client, table_id: str):
    """Show what would be updated without making changes."""
    print("\n" + "="*60)
    print("DRY RUN - No changes will be made")
    print("="*60)
    
    # Get current network names
    print("\n📊 Current network names in database:")
    print("-" * 40)
    
    current_names = get_current_network_names(client, table_id)
    
    if not current_names:
        print("No data found in table.")
        return
    
    total_rows = 0
    rows_to_update = 0
    
    for network, count in current_names:
        total_rows += count
        new_name = NETWORK_NAME_MAPPING.get(network.lower() if network else '', None)
        
        if new_name and new_name != network:
            print(f"  ❌ '{network}' ({count} rows) → '{new_name}'")
            rows_to_update += count
        elif new_name:
            print(f"  ✅ '{network}' ({count} rows) - Already correct")
        else:
            print(f"  ⚪ '{network}' ({count} rows) - No mapping defined")
    
    print("-" * 40)
    print(f"\nTotal rows: {total_rows}")
    print(f"Rows to update: {rows_to_update}")
    
    # Show the query that would be executed
    print("\n📝 SQL Query that would be executed:")
    print("-" * 40)
    print(generate_update_query(table_id))


def execute_migration(client: bigquery.Client, table_id: str):
    """Execute the network name migration."""
    print("\n" + "="*60)
    print("EXECUTING MIGRATION")
    print("="*60)
    
    # Show before state
    print("\n📊 Before migration:")
    print("-" * 40)
    before_names = get_current_network_names(client, table_id)
    for network, count in before_names:
        print(f"  '{network}': {count} rows")
    
    # Execute update
    print("\n🔄 Executing UPDATE query...")
    query = generate_update_query(table_id)
    
    job_config = bigquery.QueryJobConfig()
    job = client.query(query, job_config=job_config)
    
    # Wait for completion
    result = job.result()
    
    print(f"✅ Query completed!")
    print(f"   Rows affected: {job.num_dml_affected_rows}")
    
    # Show after state
    print("\n📊 After migration:")
    print("-" * 40)
    after_names = get_current_network_names(client, table_id)
    for network, count in after_names:
        print(f"  '{network}': {count} rows")
    
    print("\n✅ Migration completed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate network names in BigQuery to new standardized format"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the migration'
    )
    parser.add_argument(
        '--table',
        type=str,
        default=None,
        help='Override BigQuery table ID (project.dataset.table)'
    )
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("Please specify --dry-run or --execute")
        print("\nExamples:")
        print("  python scripts/migrate_network_names.py --dry-run")
        print("  python scripts/migrate_network_names.py --execute")
        return 1
    
    # Load config
    config = Config()
    
    # Get BigQuery table ID
    gcp_config = config.get('gcp', {})
    project_id = gcp_config.get('project_id', 'gen-lang-client-0468554395')
    dataset_id = gcp_config.get('dataset_id', 'ad_network_analytics')
    table_name = 'network_comparison'
    
    table_id = args.table or f"{project_id}.{dataset_id}.{table_name}"
    
    print(f"🎯 Target table: {table_id}")
    
    # Create BigQuery client
    client = get_bigquery_client(config)
    
    if args.dry_run:
        dry_run(client, table_id)
    elif args.execute:
        # Confirmation prompt
        print(f"\n⚠️  WARNING: This will modify data in {table_id}")
        response = input("Are you sure you want to continue? (yes/no): ")
        
        if response.lower() == 'yes':
            execute_migration(client, table_id)
        else:
            print("Migration cancelled.")
            return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
