#!/usr/bin/env python3
"""
Test script for GCS Export functionality.
Tests data fetching from AppLovin, Unity, and IronSource, then exports to GCS or local files.

Usage:
    # Dry-run mode - exports to local ./output folder
    python test_gcs_export.py --dry-run
    
    # Upload mode - exports to Google Cloud Storage
    python test_gcs_export.py --upload
    
    # Specify date (default: yesterday)
    python test_gcs_export.py --dry-run --date 2026-01-05
    
    # Verbose output
    python test_gcs_export.py --dry-run --verbose
"""
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from src.fetchers import ApplovinFetcher, UnityAdsFetcher, IronSourceFetcher
from src.exporters import GCSExporter


class TestGCSExport:
    """Test harness for GCS export functionality."""
    
    # Supported networks for this test
    SUPPORTED_NETWORKS = ['unity', 'ironsource']
    
    # Network name mapping for comparison
    NETWORK_NAME_MAP = {
        'UNITY_BIDDING': 'unity',
        'UNITY': 'unity',
        'Unity Bidding': 'unity',
        'Unity': 'unity',
        'IRONSOURCE_BIDDING': 'ironsource',
        'IRONSOURCE': 'ironsource',
        'ironSource Bidding': 'ironsource',
        'ironSource': 'ironsource',
        'IronSource Bidding': 'ironsource',
        'IronSource': 'ironsource',
    }
    
    def __init__(self, config: Config, verbose: bool = False):
        """Initialize test harness."""
        self.config = config
        self.verbose = verbose
        self.applovin_fetcher = None
        self.network_fetchers = {}
        
        self._initialize_fetchers()
    
    def _initialize_fetchers(self):
        """Initialize AppLovin and network fetchers."""
        print("\n🔧 Initializing fetchers...")
        
        # Initialize AppLovin MAX fetcher
        applovin_config = self.config.get_applovin_config()
        if applovin_config and applovin_config.get('api_key'):
            self.applovin_fetcher = ApplovinFetcher(
                api_key=applovin_config['api_key'],
                applications=applovin_config.get('applications', [])
            )
            print("   ✅ AppLovin MAX fetcher initialized")
        else:
            print("   ❌ AppLovin MAX configuration missing")
            return
        
        # Initialize Unity fetcher
        unity_config = self.config.get_unity_config()
        if unity_config.get('enabled') and unity_config.get('api_key'):
            self.network_fetchers['unity'] = UnityAdsFetcher(
                api_key=unity_config['api_key'],
                organization_id=unity_config['organization_id'],
                game_ids=unity_config.get('game_ids')
            )
            print("   ✅ Unity Ads fetcher initialized")
        
        # Initialize IronSource fetcher
        ironsource_config = self.config.get_ironsource_config()
        if ironsource_config.get('enabled') and ironsource_config.get('secret_key'):
            self.network_fetchers['ironsource'] = IronSourceFetcher(
                username=ironsource_config['username'],
                secret_key=ironsource_config['secret_key']
            )
            print("   ✅ IronSource fetcher initialized")
        
        print(f"\n   📊 Initialized {len(self.network_fetchers)} network fetchers: {list(self.network_fetchers.keys())}")
    
    def _normalize_network_name(self, name: str) -> str:
        """Normalize network name from AppLovin format."""
        return self.NETWORK_NAME_MAP.get(name, name.lower())
    
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch data from AppLovin MAX and individual networks.
        
        Returns:
            Dictionary with 'applovin' and 'networks' data
        """
        print(f"\n📥 Fetching data for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
        
        result = {
            'applovin': None,
            'networks': {}
        }
        
        # Fetch AppLovin MAX data
        print("\n   🔄 Fetching AppLovin MAX data...")
        try:
            result['applovin'] = self.applovin_fetcher.fetch_data(start_date, end_date)
            if self.verbose:
                print(f"      Raw response keys: {result['applovin'].keys() if result['applovin'] else 'None'}")
            print("   ✅ AppLovin MAX data fetched")
        except Exception as e:
            print(f"   ❌ AppLovin MAX fetch failed: {e}")
            return result
        
        # Fetch network data
        for network_name, fetcher in self.network_fetchers.items():
            print(f"\n   🔄 Fetching {network_name} data...")
            try:
                result['networks'][network_name] = fetcher.fetch_data(start_date, end_date)
                print(f"   ✅ {network_name} data fetched")
                if self.verbose:
                    data = result['networks'][network_name]
                    print(f"      Revenue: ${data.get('revenue', 0):.2f}")
                    print(f"      Impressions: {data.get('impressions', 0):,}")
            except Exception as e:
                print(f"   ❌ {network_name} fetch failed: {e}")
        
        return result
    
    def merge_data(self, data: Dict[str, Any], report_date: datetime) -> List[Dict[str, Any]]:
        """
        Get comparison rows from AppLovin MAX data.
        AppLovin fetcher already returns comparison_rows with MAX vs Network data.
        
        Returns:
            List of comparison rows
        """
        print("\n🔀 Processing comparison data...")
        
        applovin_data = data.get('applovin', {})
        
        if not applovin_data:
            print("   ⚠️  No AppLovin data")
            return []
        
        # AppLovin fetcher already returns comparison_rows
        comparison_rows = applovin_data.get('comparison_rows', [])
        
        if self.verbose:
            print(f"   AppLovin returned {len(comparison_rows)} comparison rows")
            if comparison_rows:
                networks = set(row.get('network', '') for row in comparison_rows)
                print(f"   Networks in data: {networks}")
        
        # Filter to only supported networks if needed
        filtered_rows = []
        for row in comparison_rows:
            network = row.get('network', '').lower()
            # Normalize network name
            normalized = self._normalize_network_name(row.get('network', ''))
            if normalized in self.SUPPORTED_NETWORKS or not self.SUPPORTED_NETWORKS:
                filtered_rows.append(row)
        
        print(f"   ✅ {len(filtered_rows)} comparison rows (filtered for: {self.SUPPORTED_NETWORKS})")
        
        return filtered_rows
    
    def _calc_delta(self, max_val: float, net_val: float) -> str:
        """Calculate percentage delta between MAX and network values."""
        if max_val == 0:
            return 'N/A'
        delta = ((net_val - max_val) / max_val) * 100
        sign = '+' if delta >= 0 else ''
        return f"{sign}{delta:.1f}%"
    
    def run(
        self,
        report_date: datetime,
        dry_run: bool = True,
        output_dir: str = "./output"
    ) -> bool:
        """
        Run the full test: fetch data, merge, and export.
        
        Args:
            report_date: Date to report on
            dry_run: If True, export to local files; if False, upload to GCS
            output_dir: Local output directory for dry-run mode
            
        Returns:
            True if successful, False otherwise
        """
        print("\n" + "="*60)
        print("🚀 GCS Export Test")
        print("="*60)
        print(f"   Report Date: {report_date.strftime('%Y-%m-%d')}")
        print(f"   Mode: {'DRY-RUN (local files)' if dry_run else 'UPLOAD (GCS)'}")
        print("="*60)
        
        # Fetch data
        end_date = report_date
        start_date = report_date
        
        data = self.fetch_data(start_date, end_date)
        
        if not data.get('applovin'):
            print("\n❌ Test failed: No AppLovin data")
            return False
        
        # Merge data
        comparison_rows = self.merge_data(data, report_date)
        
        if not comparison_rows:
            print("\n⚠️  No comparison rows generated (this may be normal if no matching data)")
            # Create some sample data for testing the export functionality
            print("\n📝 Creating sample data for export test...")
            comparison_rows = self._create_sample_data(report_date)
        
        # Display sample of data
        print("\n📋 Sample data (first 3 rows):")
        for row in comparison_rows[:3]:
            print(f"   {row['application']} | {row['network']} | {row['ad_type']}")
            print(f"      MAX: ${row['max_revenue']:.2f} / {row['max_impressions']:,} imp")
            print(f"      NET: ${row['network_revenue']:.2f} / {row['network_impressions']:,} imp")
        
        # Export data
        print("\n📤 Exporting data...")
        
        gcp_config = self.config.get_gcp_config()
        
        if dry_run:
            # Local export
            exporter = GCSExporter(
                project_id=gcp_config.get('project_id', 'test-project'),
                bucket_name=gcp_config.get('bucket_name', 'test-bucket'),
                service_account_path=gcp_config.get('service_account_path')
            )
            files = exporter.export_to_local(comparison_rows, report_date, output_dir)
        else:
            # GCS upload
            if not gcp_config.get('enabled'):
                print("❌ GCP not enabled in config.yaml")
                return False
            
            exporter = GCSExporter(
                project_id=gcp_config['project_id'],
                bucket_name=gcp_config['bucket_name'],
                service_account_path=gcp_config.get('service_account_path')
            )
            files = exporter.export_to_gcs(comparison_rows, report_date)
        
        if files:
            print("\n✅ Export successful!")
            print("   Created files:")
            for f in files:
                print(f"   📁 {f}")
            
            # Show how to verify the parquet file
            if dry_run and files:
                print("\n💡 To verify the Parquet file:")
                print(f"   python -c \"import pyarrow.parquet as pq; t = pq.read_table('{files[0]}'); print(t.to_pandas())\"")
            
            return True
        else:
            print("\n❌ Export failed: No files created")
            return False
    
    def _create_sample_data(self, report_date: datetime) -> List[Dict[str, Any]]:
        """Create sample comparison data for testing export functionality."""
        sample_rows = []
        
        for platform in ['Android', 'iOS']:
            for network in ['Unity Bidding', 'ironSource Bidding']:
                for ad_type in ['Banner', 'Interstitial', 'Rewarded']:
                    sample_rows.append({
                        'application': f'Clear And Shoot ({platform})',
                        'network': network,
                        'ad_type': ad_type,
                        'max_impressions': 10000,
                        'network_impressions': 9800,
                        'imp_delta': '-2.0%',
                        'max_revenue': 50.0,
                        'network_revenue': 48.5,
                        'rev_delta': '-3.0%',
                        'max_ecpm': 5.0,
                        'network_ecpm': 4.95,
                        'cpm_delta': '-1.0%',
                    })
        
        return sample_rows


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Test GCS export functionality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry-run mode (local files)
    python test_gcs_export.py --dry-run
    
    # Upload to GCS
    python test_gcs_export.py --upload
    
    # Specify date
    python test_gcs_export.py --dry-run --date 2026-01-05
    
    # With verbose output
    python test_gcs_export.py --dry-run --verbose
        """
    )
    
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Export to local ./output folder (for testing)'
    )
    mode_group.add_argument(
        '--upload',
        action='store_true',
        help='Upload to Google Cloud Storage'
    )
    
    parser.add_argument(
        '--date',
        type=str,
        help='Report date (YYYY-MM-DD format, default: yesterday)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./output',
        help='Local output directory for dry-run mode (default: ./output)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Parse date
    if args.date:
        try:
            report_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Invalid date format: {args.date}")
            print("   Use YYYY-MM-DD format (e.g., 2026-01-05)")
            sys.exit(1)
    else:
        report_date = datetime.now() - timedelta(days=1)
    
    # Load configuration
    try:
        config = Config()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Run test
    tester = TestGCSExport(config, verbose=args.verbose)
    
    success = tester.run(
        report_date=report_date,
        dry_run=args.dry_run,
        output_dir=args.output_dir
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
