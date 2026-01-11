#!/usr/bin/env python3
"""
Migration script to update network names in GCS Parquet files.
Downloads parquet files, updates network names, and re-uploads.

Usage:
    # Dry-run (show what would be updated)
    python scripts/migrate_gcs_network_names.py --dry-run
    
    # Execute migration
    python scripts/migrate_gcs_network_names.py --execute
"""
import argparse
import os
import sys
import tempfile
from datetime import datetime
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage
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


def get_gcs_client(config: Config):
    """Create GCS client from config."""
    gcp_config = config.get('gcp', {})
    service_account_path = gcp_config.get('service_account_path', 'credentials/gcp_service_account.json')
    project_id = gcp_config.get('project_id')
    
    if service_account_path and os.path.exists(service_account_path):
        credentials = service_account.Credentials.from_service_account_file(service_account_path)
        return storage.Client(project=project_id, credentials=credentials)
    else:
        return storage.Client(project=project_id)


def map_network_name(name: str) -> str:
    """Map old network name to new name."""
    if not name:
        return name
    
    # Try exact match first (case-insensitive)
    lower_name = name.lower().strip()
    if lower_name in NETWORK_NAME_MAPPING:
        return NETWORK_NAME_MAPPING[lower_name]
    
    return name


def process_parquet_file(blob, bucket, dry_run: bool = True) -> dict:
    """
    Process a single parquet file, updating network names.
    
    Returns:
        dict with statistics about updates
    """
    result = {
        'file': blob.name,
        'total_rows': 0,
        'updated_rows': 0,
        'network_changes': {},
        'success': False,
        'error': None
    }
    
    try:
        # Download to temp file
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            tmp_path = tmp.name
            blob.download_to_filename(tmp_path)
        
        # Read parquet using PyArrow only
        table = pq.read_table(tmp_path)
        
        result['total_rows'] = table.num_rows
        
        # Check if 'network' column exists
        if 'network' not in table.column_names:
            result['error'] = "No 'network' column found"
            os.unlink(tmp_path)
            return result
        
        # Get network column
        network_col = table.column('network')
        original_networks = network_col.to_pylist()
        
        # Map network names
        new_networks = [map_network_name(n) for n in original_networks]
        
        # Count changes
        changes = []
        for old, new in zip(original_networks, new_networks):
            if old != new:
                changes.append((old, new))
        
        result['updated_rows'] = len(changes)
        
        # Track specific changes
        for old, new in changes:
            key = f"{old} → {new}"
            result['network_changes'][key] = result['network_changes'].get(key, 0) + 1
        
        if not dry_run and result['updated_rows'] > 0:
            # Create new network column
            new_network_array = pa.array(new_networks, type=pa.string())
            
            # Replace column in table
            col_idx = table.column_names.index('network')
            new_table = table.set_column(col_idx, 'network', new_network_array)
            
            # Write back to temp file
            pq.write_table(new_table, tmp_path)
            
            # Upload back to GCS
            blob.upload_from_filename(tmp_path)
        
        result['success'] = True
        
        # Cleanup
        os.unlink(tmp_path)
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Migrate network names in GCS parquet files to new standardized format"
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
        '--prefix',
        type=str,
        default='network_data/',
        help='GCS prefix to filter files (default: network_data/)'
    )
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("Please specify --dry-run or --execute")
        print("\nExamples:")
        print("  python scripts/migrate_gcs_network_names.py --dry-run")
        print("  python scripts/migrate_gcs_network_names.py --execute")
        return 1
    
    # Load config
    config = Config()
    gcp_config = config.get('gcp', {})
    bucket_name = gcp_config.get('bucket_name')
    
    print(f"🎯 Target bucket: {bucket_name}")
    print(f"📁 Prefix: {args.prefix}")
    
    if args.dry_run:
        print("\n" + "="*60)
        print("DRY RUN - No changes will be made")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("EXECUTING MIGRATION")
        print("="*60)
        
        # Confirmation
        response = input("\n⚠️  This will modify files in GCS. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled.")
            return 0
    
    # Create GCS client
    client = get_gcs_client(config)
    bucket = client.bucket(bucket_name)
    
    # List all parquet files
    blobs = list(bucket.list_blobs(prefix=args.prefix))
    parquet_blobs = [b for b in blobs if b.name.endswith('.parquet')]
    
    print(f"\n📊 Found {len(parquet_blobs)} parquet files")
    print("-" * 60)
    
    total_files = 0
    total_rows = 0
    total_updated = 0
    all_changes = {}
    
    for blob in parquet_blobs:
        print(f"\n📄 Processing: {blob.name}")
        
        result = process_parquet_file(blob, bucket, dry_run=args.dry_run)
        
        total_files += 1
        total_rows += result['total_rows']
        total_updated += result['updated_rows']
        
        if result['error']:
            print(f"   ❌ Error: {result['error']}")
        elif result['updated_rows'] == 0:
            print(f"   ✅ No changes needed ({result['total_rows']} rows)")
        else:
            print(f"   🔄 {result['updated_rows']}/{result['total_rows']} rows updated")
            for change, count in result['network_changes'].items():
                print(f"      • {change}: {count} rows")
                all_changes[change] = all_changes.get(change, 0) + count
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Files processed: {total_files}")
    print(f"Total rows: {total_rows}")
    print(f"Rows updated: {total_updated}")
    
    if all_changes:
        print("\nAll network name changes:")
        for change, count in sorted(all_changes.items()):
            print(f"  • {change}: {count} rows")
    
    if args.dry_run and total_updated > 0:
        print(f"\n💡 Run with --execute to apply these changes")
    elif args.execute and total_updated > 0:
        print(f"\n✅ Migration completed successfully!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
