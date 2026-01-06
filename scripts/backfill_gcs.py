#!/usr/bin/env python3
"""
Backfill script for loading historical data to GCS.
Fetches data from all enabled networks for a date range and uploads to GCS.

Features:
- Checkpoint support: Resumes from last successful date if interrupted
- Rate limiting: Configurable delay between requests
- Error handling: Continues on failure, logs errors
- Dry-run mode: Test locally before uploading

Usage:
    # Backfill from Jan 1, 2026 to today (dry-run)
    python scripts/backfill_gcs.py --start-date 2026-01-01 --dry-run
    
    # Backfill with GCS upload
    python scripts/backfill_gcs.py --start-date 2026-01-01 --upload
    
    # Backfill specific date range
    python scripts/backfill_gcs.py --start-date 2026-01-01 --end-date 2026-01-05 --upload
    
    # With delay between dates (for rate limiting)
    python scripts/backfill_gcs.py --start-date 2026-01-01 --upload --delay 30
    
    # Resume from checkpoint
    python scripts/backfill_gcs.py --start-date 2026-01-01 --upload --resume
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.fetchers import (
    ApplovinFetcher, UnityAdsFetcher, IronSourceFetcher,
    MintegralFetcher, AdmobFetcher, MetaFetcher, MolocoFetcher,
    InMobiFetcher, BidMachineFetcher, LiftoffFetcher, DTExchangeFetcher, PangleFetcher
)
from src.exporters import GCSExporter


CHECKPOINT_FILE = "backfill_checkpoint.json"

# Network configuration
NETWORK_FETCHER_MAP = {
    'unity': {
        'class': UnityAdsFetcher,
        'config_method': 'get_unity_config',
        'init_params': lambda cfg: {
            'api_key': cfg['api_key'],
            'organization_id': cfg['organization_id'],
            'game_ids': cfg.get('game_ids')
        }
    },
    'ironsource': {
        'class': IronSourceFetcher,
        'config_method': 'get_ironsource_config',
        'init_params': lambda cfg: {
            'username': cfg['username'],
            'secret_key': cfg['secret_key']
        }
    },
    'mintegral': {
        'class': MintegralFetcher,
        'config_method': 'get_mintegral_config',
        'init_params': lambda cfg: {
            'skey': cfg['skey'],
            'secret': cfg['secret'],
            'app_id': cfg.get('app_ids')
        }
    },
    'admob': {
        'class': AdmobFetcher,
        'config_method': 'get_admob_config',
        'init_params': lambda cfg: {
            'publisher_id': cfg['publisher_id'],
            'app_ids': cfg.get('app_ids'),
            'oauth_credentials_path': cfg.get('oauth_credentials_path'),
            'token_path': cfg.get('token_path')
        }
    },
    'meta': {
        'class': MetaFetcher,
        'config_method': 'get_meta_config',
        'init_params': lambda cfg: {
            'access_token': cfg['access_token'],
            'property_ids': cfg.get('property_ids')
        }
    },
    'moloco': {
        'class': MolocoFetcher,
        'config_method': 'get_moloco_config',
        'init_params': lambda cfg: {
            'email': cfg['email'],
            'password': cfg['password'],
            'app_bundle_ids': cfg.get('app_bundle_ids')
        }
    },
    'inmobi': {
        'class': InMobiFetcher,
        'config_method': 'get_inmobi_config',
        'init_params': lambda cfg: {
            'account_id': cfg['account_id'],
            'username': cfg['username'],
            'secret_key': cfg['secret_key']
        }
    },
    'bidmachine': {
        'class': BidMachineFetcher,
        'config_method': 'get_bidmachine_config',
        'init_params': lambda cfg: {
            'seller_id': cfg['seller_id'],
            'api_key': cfg['api_key']
        }
    },
    'liftoff': {
        'class': LiftoffFetcher,
        'config_method': 'get_liftoff_config',
        'init_params': lambda cfg: {
            'api_key': cfg['api_key'],
            'application_ids': cfg.get('application_ids')
        }
    },
    'dt_exchange': {
        'class': DTExchangeFetcher,
        'config_method': 'get_dt_exchange_config',
        'init_params': lambda cfg: {
            'client_id': cfg['client_id'],
            'client_secret': cfg['client_secret'],
            'publisher_id': cfg.get('publisher_id')
        }
    },
    'pangle': {
        'class': PangleFetcher,
        'config_method': 'get_pangle_config',
        'init_params': lambda cfg: {
            'user_id': cfg['user_id'],
            'role_id': cfg['role_id'],
            'secure_key': cfg['secure_key']
        }
    }
}

# Network name mapping for AppLovin data to fetcher keys
NETWORK_NAME_MAP = {
    # Unity
    'UNITY_BIDDING': 'unity', 'UNITY': 'unity', 
    'Unity Bidding': 'unity', 'Unity': 'unity', 'Unity Ads': 'unity',
    # IronSource
    'IRONSOURCE_BIDDING': 'ironsource', 'IRONSOURCE': 'ironsource', 
    'ironSource Bidding': 'ironsource', 'ironSource': 'ironsource',
    'IronSource Bidding': 'ironsource', 'IronSource': 'ironsource',
    # Mintegral
    'MINTEGRAL_BIDDING': 'mintegral', 'MINTEGRAL': 'mintegral',
    'Mintegral Bidding': 'mintegral', 'Mintegral': 'mintegral',
    # Google/AdMob
    'ADMOB_BIDDING': 'admob', 'ADMOB': 'admob', 
    'GOOGLE_BIDDING': 'admob', 'GOOGLE': 'admob',
    'Google Bidding': 'admob', 'AdMob': 'admob',
    # Meta/Facebook
    'FACEBOOK_BIDDING': 'meta', 'FACEBOOK': 'meta', 
    'META_BIDDING': 'meta', 'META': 'meta',
    'Facebook Network': 'meta', 'Meta Bidding': 'meta',
    # Moloco
    'MOLOCO_BIDDING': 'moloco', 'MOLOCO': 'moloco',
    'Moloco Bidding': 'moloco', 'Moloco': 'moloco',
    # InMobi
    'INMOBI_BIDDING': 'inmobi', 'INMOBI': 'inmobi',
    'InMobi Bidding': 'inmobi', 'InMobi': 'inmobi',
    # BidMachine
    'BIDMACHINE_BIDDING': 'bidmachine', 'BIDMACHINE': 'bidmachine',
    'BidMachine Bidding': 'bidmachine', 'BidMachine': 'bidmachine',
    # Liftoff/Vungle
    'LIFTOFF_BIDDING': 'liftoff', 'LIFTOFF': 'liftoff', 
    'VUNGLE_BIDDING': 'liftoff', 'VUNGLE': 'liftoff',
    'Liftoff Monetize Bidding': 'liftoff', 'Liftoff': 'liftoff', 
    'Vungle': 'liftoff', 'Vungle Bidding': 'liftoff',
    # DT Exchange/Fyber
    'DT_EXCHANGE_BIDDING': 'dt_exchange', 'DT_EXCHANGE': 'dt_exchange', 
    'FYBER_BIDDING': 'dt_exchange', 'FYBER': 'dt_exchange',
    'DT Exchange Bidding': 'dt_exchange', 'Fyber': 'dt_exchange',
    # Pangle/TikTok
    'PANGLE_BIDDING': 'pangle', 'PANGLE': 'pangle', 
    'TIKTOK_BIDDING': 'pangle', 'TIKTOK': 'pangle',
    'Pangle Bidding': 'pangle', 'TikTok': 'pangle',
}


class BackfillManager:
    """Manages backfill operations for historical data."""
    
    def __init__(
        self,
        config: Config,
        networks: Optional[List[str]] = None,
        verbose: bool = False
    ):
        """
        Initialize backfill manager.
        
        Args:
            config: Configuration object
            networks: List of networks to backfill (default: unity, ironsource)
            verbose: Enable verbose output
        """
        self.config = config
        self.networks = networks or ['unity', 'ironsource']
        self.verbose = verbose
        self.applovin_fetcher = None
        self.network_fetchers = {}
        
        self._initialize_fetchers()
    
    def _initialize_fetchers(self):
        """Initialize all required fetchers."""
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
            raise ValueError("AppLovin MAX configuration required for backfill")
        
        # Initialize network fetchers
        for network in self.networks:
            if network not in NETWORK_FETCHER_MAP:
                print(f"   ⚠️  Unknown network: {network}")
                continue
            
            network_info = NETWORK_FETCHER_MAP[network]
            config_method = getattr(self.config, network_info['config_method'])
            network_config = config_method()
            
            if not network_config.get('enabled'):
                print(f"   ⏭️  {network} is disabled in config")
                continue
            
            try:
                init_params = network_info['init_params'](network_config)
                self.network_fetchers[network] = network_info['class'](**init_params)
                print(f"   ✅ {network} fetcher initialized")
            except (KeyError, TypeError) as e:
                print(f"   ❌ {network} initialization failed: {e}")
        
        print(f"\n   📊 Initialized {len(self.network_fetchers)} network fetchers")
    
    def load_checkpoint(self) -> Optional[str]:
        """Load last successful date from checkpoint file."""
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('last_successful_date')
            except (json.JSONDecodeError, IOError):
                pass
        return None
    
    def save_checkpoint(self, date: datetime):
        """Save checkpoint with last successful date."""
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump({
                'last_successful_date': date.strftime('%Y-%m-%d'),
                'updated_at': datetime.utcnow().isoformat()
            }, f)
    
    def clear_checkpoint(self):
        """Remove checkpoint file."""
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
    
    def fetch_day_data(self, report_date: datetime) -> Dict[str, Any]:
        """Fetch data for a single day."""
        result = {'applovin': None, 'networks': {}}
        
        # Fetch AppLovin data
        try:
            result['applovin'] = self.applovin_fetcher.fetch_data(report_date, report_date)
        except Exception as e:
            print(f"      ❌ AppLovin fetch failed: {e}")
            return result
        
        # Fetch network data
        for network_name, fetcher in self.network_fetchers.items():
            try:
                result['networks'][network_name] = fetcher.fetch_data(report_date, report_date)
            except Exception as e:
                if self.verbose:
                    print(f"      ⚠️  {network_name} fetch failed: {e}")
        
        return result
    
    def merge_data(self, data: Dict[str, Any], report_date: datetime) -> List[Dict[str, Any]]:
        """
        Merge AppLovin MAX data with actual network data for true comparison.
        
        This combines MAX reported metrics with network's own reported metrics
        to enable delta calculations. All MAX rows are included - if no network
        data is available, network_revenue will be 0.
        """
        applovin_data = data.get('applovin', {})
        network_data = data.get('networks', {})
        
        if not applovin_data:
            return []
        
        # Get MAX comparison rows
        max_rows = applovin_data.get('comparison_rows', [])
        
        if not max_rows:
            return []
        
        # Build merged comparison rows - include ALL MAX rows
        comparison_rows = []
        
        for row in max_rows:
            network_name = row.get('network', '')
            # Map AppLovin network name to our fetcher key
            network_key = NETWORK_NAME_MAP.get(network_name, 
                NETWORK_NAME_MAP.get(network_name.upper().replace(' ', '_'), None))
            
            if not network_key:
                network_key = network_name.lower().replace(' bidding', '').replace(' ads', '').strip()
            
            # Extract platform from application name
            app_name = row.get('application', '')
            platform = 'ios' if 'iOS' in app_name else 'android'
            ad_type = row.get('ad_type', '').lower()
            
            # Default network values (no comparison data available)
            net_revenue = 0
            net_impressions = 0
            net_ecpm = 0
            has_network_data = False
            
            # Try to get network's platform and ad_type specific data if available
            if network_key in network_data:
                net_data = network_data[network_key]
                platform_data = net_data.get('platform_data', {}).get(platform, {})
                ad_data = platform_data.get('ad_data', {}).get(ad_type, {})
                
                if ad_data.get('impressions', 0) > 0:
                    net_revenue = ad_data.get('revenue', 0)
                    net_impressions = ad_data.get('impressions', 0)
                    net_ecpm = ad_data.get('ecpm', 0)
                    has_network_data = True
            
            # Calculate deltas (only if we have network data)
            if has_network_data:
                imp_delta = self._calc_delta(row.get('max_impressions', 0), net_impressions)
                rev_delta = self._calc_delta(row.get('max_revenue', 0), net_revenue)
                cpm_delta = self._calc_delta(row.get('max_ecpm', 0), net_ecpm)
            else:
                imp_delta = 'N/A'
                rev_delta = 'N/A'
                cpm_delta = 'N/A'
            
            comparison_rows.append({
                'application': app_name,
                'network': network_name,
                'ad_type': row.get('ad_type', ''),
                'max_impressions': row.get('max_impressions', 0),
                'network_impressions': net_impressions,
                'imp_delta': imp_delta,
                'max_revenue': row.get('max_revenue', 0),
                'network_revenue': net_revenue,
                'rev_delta': rev_delta,
                'max_ecpm': row.get('max_ecpm', 0),
                'network_ecpm': net_ecpm,
                'cpm_delta': cpm_delta,
            })
        
        return comparison_rows
    
    def _calc_delta(self, max_val: float, net_val: float) -> str:
        """Calculate percentage delta."""
        if max_val == 0:
            return 'N/A'
        delta = ((net_val - max_val) / max_val) * 100
        sign = '+' if delta >= 0 else ''
        return f"{sign}{delta:.1f}%"
    
    def run_backfill(
        self,
        start_date: datetime,
        end_date: datetime,
        dry_run: bool = True,
        delay_seconds: int = 5,
        resume: bool = False,
        output_dir: str = "./output"
    ) -> Dict[str, Any]:
        """
        Run backfill for date range.
        
        Args:
            start_date: Start date for backfill
            end_date: End date for backfill
            dry_run: If True, save locally; if False, upload to GCS
            delay_seconds: Delay between API calls (rate limiting)
            resume: If True, resume from checkpoint
            output_dir: Local output directory for dry-run
            
        Returns:
            Summary dictionary with success/failure counts
        """
        print("\n" + "="*60)
        print("🔄 BACKFILL OPERATION")
        print("="*60)
        print(f"   Start Date: {start_date.strftime('%Y-%m-%d')}")
        print(f"   End Date: {end_date.strftime('%Y-%m-%d')}")
        print(f"   Mode: {'DRY-RUN' if dry_run else 'GCS UPLOAD'}")
        print(f"   Networks: {', '.join(self.networks)}")
        print(f"   Delay: {delay_seconds}s between dates")
        print("="*60)
        
        # Handle resume
        if resume:
            checkpoint = self.load_checkpoint()
            if checkpoint:
                checkpoint_date = datetime.strptime(checkpoint, '%Y-%m-%d')
                if checkpoint_date >= start_date:
                    start_date = checkpoint_date + timedelta(days=1)
                    print(f"\n📍 Resuming from checkpoint: {checkpoint}")
                    print(f"   Starting from: {start_date.strftime('%Y-%m-%d')}")
        
        # Initialize exporter
        gcp_config = self.config.get_gcp_config()
        exporter = GCSExporter(
            project_id=gcp_config.get('project_id', 'test-project'),
            bucket_name=gcp_config.get('bucket_name', 'test-bucket'),
            service_account_path=gcp_config.get('service_account_path')
        )
        
        # Calculate total days
        total_days = (end_date - start_date).days + 1
        results = {
            'total_days': total_days,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        current_date = start_date
        day_count = 0
        
        while current_date <= end_date:
            day_count += 1
            date_str = current_date.strftime('%Y-%m-%d')
            
            print(f"\n📅 [{day_count}/{total_days}] Processing {date_str}...")
            
            try:
                # Fetch data
                data = self.fetch_day_data(current_date)
                
                if not data.get('applovin'):
                    print(f"      ⏭️  No AppLovin data for {date_str}")
                    results['skipped'] += 1
                    current_date += timedelta(days=1)
                    continue
                
                # Merge data
                comparison_rows = self.merge_data(data, current_date)
                
                if not comparison_rows:
                    print(f"      ⏭️  No comparison data for {date_str}")
                    results['skipped'] += 1
                else:
                    # Export
                    if dry_run:
                        files = exporter.export_to_local(comparison_rows, current_date, output_dir)
                    else:
                        files = exporter.export_to_gcs(comparison_rows, current_date)
                    
                    if files:
                        results['successful'] += 1
                        self.save_checkpoint(current_date)
                        print(f"      ✅ Exported {len(comparison_rows)} rows")
                    else:
                        results['failed'] += 1
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
                results['failed'] += 1
                results['errors'].append({
                    'date': date_str,
                    'error': str(e)
                })
            
            # Rate limiting delay (except for last day)
            if current_date < end_date and delay_seconds > 0:
                print(f"      ⏳ Waiting {delay_seconds}s...")
                time.sleep(delay_seconds)
            
            current_date += timedelta(days=1)
        
        # Print summary
        print("\n" + "="*60)
        print("📊 BACKFILL SUMMARY")
        print("="*60)
        print(f"   Total days: {results['total_days']}")
        print(f"   Successful: {results['successful']} ✅")
        print(f"   Failed: {results['failed']} ❌")
        print(f"   Skipped: {results['skipped']} ⏭️")
        
        if results['errors']:
            print("\n   Errors:")
            for err in results['errors'][:5]:
                print(f"      - {err['date']}: {err['error'][:50]}...")
        
        print("="*60)
        
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Backfill historical data to GCS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry-run from Jan 1, 2026 to today
    python scripts/backfill_gcs.py --start-date 2026-01-01 --dry-run
    
    # Upload to GCS
    python scripts/backfill_gcs.py --start-date 2026-01-01 --upload
    
    # Resume interrupted backfill
    python scripts/backfill_gcs.py --start-date 2026-01-01 --upload --resume
    
    # Custom date range with delay
    python scripts/backfill_gcs.py --start-date 2026-01-01 --end-date 2026-01-05 --delay 30 --upload
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
        help='End date (YYYY-MM-DD format, default: yesterday)'
    )
    
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Export to local ./output folder'
    )
    mode_group.add_argument(
        '--upload',
        action='store_true',
        help='Upload to Google Cloud Storage'
    )
    
    parser.add_argument(
        '--networks',
        type=str,
        default='unity,ironsource',
        help='Comma-separated list of networks (default: unity,ironsource)'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=5,
        help='Delay in seconds between dates (default: 5)'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./output',
        help='Local output directory for dry-run (default: ./output)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Parse dates
    try:
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ Invalid start date format: {args.start_date}")
        sys.exit(1)
    
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        except ValueError:
            print(f"❌ Invalid end date format: {args.end_date}")
            sys.exit(1)
    else:
        end_date = datetime.now() - timedelta(days=1)
    
    # Parse networks
    networks = [n.strip() for n in args.networks.split(',')]
    
    # Load config
    try:
        config = Config()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Run backfill
    manager = BackfillManager(config, networks=networks, verbose=args.verbose)
    
    results = manager.run_backfill(
        start_date=start_date,
        end_date=end_date,
        dry_run=args.dry_run,
        delay_seconds=args.delay,
        resume=args.resume,
        output_dir=args.output_dir
    )
    
    # Exit with error code if failures
    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
