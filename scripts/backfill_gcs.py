#!/usr/bin/env python3
"""
Backfill script for loading historical data to GCS.
Fetches data from all enabled networks for a date range and uploads to GCS.

Features:
- Async support for all network fetchers
- Uses ValidationService for consistency with main.py
- Rate limiting: Configurable delay between requests
- Error handling: Continues on failure, logs errors

Usage:
    # Backfill specific date range
    python scripts/backfill_gcs.py --start-date 2026-01-01 --end-date 2026-01-10
    
    # Backfill single date
    python scripts/backfill_gcs.py --start-date 2026-01-05 --end-date 2026-01-05
    
    # With custom delay between dates
    python scripts/backfill_gcs.py --start-date 2026-01-01 --end-date 2026-01-10 --delay 5
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.validation_service import ValidationService


async def backfill_date(service: ValidationService, target_date: datetime) -> Dict[str, Any]:
    """
    Run backfill for a specific date.
    
    Args:
        service: Initialized ValidationService
        target_date: Date to backfill
        
    Returns:
        Dict with success status and row count
    """
    print(f"\n{'='*60}")
    print(f"📅 Backfilling: {target_date.strftime('%Y-%m-%d')}")
    print(f"{'='*60}")
    
    # Use target date for all networks (including Meta - no T-3 delay in backfill)
    start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end_date = start_date
    
    # In backfill mode, Meta uses the same date as other networks
    meta_start_date = start_date
    meta_end_date = end_date
    
    if not service.applovin_fetcher:
        print("❌ AppLovin fetcher not configured")
        return {'success': False, 'rows': 0}
    
    # Step 1: Fetch MAX data from AppLovin
    print(f"\n📊 Fetching AppLovin MAX data...")
    try:
        max_data = await service.applovin_fetcher.fetch_data(start_date, end_date)
        max_rows = max_data.get('comparison_rows', [])
        print(f"   ✅ Retrieved {len(max_rows)} rows from MAX")
    except Exception as e:
        print(f"   ❌ Error fetching MAX: {e}")
        return {'success': False, 'rows': 0}
    
    if not max_rows:
        print(f"   ⏭️  No MAX data for {target_date.strftime('%Y-%m-%d')}")
        return {'success': True, 'rows': 0}
    
    # Step 2: Fetch all network data in parallel
    print(f"\n📊 Fetching data from {len(service.network_fetchers)} networks...")
    
    async def fetch_network(name: str, fetcher) -> tuple:
        """Fetch data from a single network."""
        try:
            result = await fetcher.fetch_data(start_date, end_date)
            revenue = result.get('total_revenue', 0)
            imps = result.get('total_impressions', 0)
            print(f"   ✅ {name}: ${revenue:.2f} revenue, {imps:,} imps")
            return name, result
        except Exception as e:
            print(f"   ❌ {name}: {e}")
            return name, None
    
    tasks = [fetch_network(name, fetcher) for name, fetcher in service.network_fetchers.items()]
    results = await asyncio.gather(*tasks)
    
    network_data = {}
    for name, result in results:
        if result:
            network_data[name] = result
    
    print(f"\n   ✅ Fetched {len(network_data)}/{len(service.network_fetchers)} networks")
    
    # Step 3: Compare and generate rows
    print(f"\n📊 Generating comparison rows...")
    comparison_rows = service._compare_data(
        max_rows, network_data, 
        start_date, end_date, 
        meta_start_date, meta_end_date, 
        max_rows  # Use same max_rows for Meta comparison in backfill
    )
    print(f"   ✅ Generated {len(comparison_rows)} rows")
    
    # Step 4: Export to GCS
    if service.gcs_exporter and comparison_rows:
        print(f"\n📤 Exporting to GCS...")
        try:
            service.gcs_exporter.export_comparison_data(comparison_rows, target_date)
            print(f"   ✅ Exported to GCS for {target_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            print(f"   ❌ GCS export error: {e}")
            return {'success': False, 'rows': len(comparison_rows)}
    
    return {'success': True, 'rows': len(comparison_rows)}


async def run_backfill(
    start_date: datetime, 
    end_date: datetime, 
    delay_seconds: int = 3
) -> Dict[str, Any]:
    """
    Run backfill for a date range.
    
    Args:
        start_date: First date to backfill
        end_date: Last date to backfill
        delay_seconds: Delay between dates for rate limiting
        
    Returns:
        Summary dict with results
    """
    print("=" * 60)
    print(f"🔄 BACKFILL: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    # Initialize service
    config = Config()
    service = ValidationService(config)
    
    print(f"✅ Initialized with {len(service.network_fetchers)} network fetchers")
    print(f"   Networks: {', '.join(service.network_fetchers.keys())}")
    
    # Process each date
    current = start_date
    results = []
    total_days = (end_date - start_date).days + 1
    day_count = 0
    
    while current <= end_date:
        day_count += 1
        print(f"\n[{day_count}/{total_days}]", end="")
        
        try:
            result = await backfill_date(service, current)
            results.append((current, result.get('success', False), result.get('rows', 0)))
        except Exception as e:
            print(f"❌ Error on {current.strftime('%Y-%m-%d')}: {e}")
            import traceback
            traceback.print_exc()
            results.append((current, False, 0))
        
        current += timedelta(days=1)
        
        # Rate limiting delay (except for last day)
        if current <= end_date and delay_seconds > 0:
            print(f"\n⏳ Waiting {delay_seconds} seconds...")
            await asyncio.sleep(delay_seconds)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 BACKFILL SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for _, success, _ in results if success)
    total_rows = sum(rows for _, _, rows in results)
    
    for date, success, rows in results:
        status = "✅" if success else "❌"
        print(f"   {status} {date.strftime('%Y-%m-%d')}: {rows} rows")
    
    print(f"\n   Total: {success_count}/{len(results)} days successful")
    print(f"   Total rows: {total_rows}")
    print("=" * 60)
    
    return {
        'total_days': len(results),
        'successful': success_count,
        'failed': len(results) - success_count,
        'total_rows': total_rows
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Backfill historical data to GCS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Backfill January 1-10, 2026
    python scripts/backfill_gcs.py --start-date 2026-01-01 --end-date 2026-01-10
    
    # Backfill single date
    python scripts/backfill_gcs.py --start-date 2026-01-05 --end-date 2026-01-05
    
    # With custom delay
    python scripts/backfill_gcs.py --start-date 2026-01-01 --end-date 2026-01-10 --delay 5
        """
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        required=True,
        help='Start date (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        required=True,
        help='End date (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=3,
        help='Delay in seconds between dates (default: 3)'
    )
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ Invalid start date format: {args.start_date}")
        sys.exit(1)
    
    try:
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ Invalid end date format: {args.end_date}")
        sys.exit(1)
    
    if end_date < start_date:
        print(f"❌ End date cannot be before start date")
        sys.exit(1)
    
    # Run backfill
    results = asyncio.run(run_backfill(
        start_date=start_date,
        end_date=end_date,
        delay_seconds=args.delay
    ))
    
    # Exit with error code if failures
    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
