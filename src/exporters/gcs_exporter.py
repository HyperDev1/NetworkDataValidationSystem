"""
Google Cloud Storage Exporter for Network Data Validation System.
Exports comparison data to GCS in Parquet format for BigQuery analysis.
"""
import os
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from typing import Dict, Any, List, Optional
from google.cloud import storage
from google.oauth2 import service_account


class GCSExporter:
    """
    Exports network comparison data to Google Cloud Storage in Parquet format.
    
    Data is organized as:
    gs://{bucket}/network_data/dt={YYYY-MM-DD}/{network}_{platform}_{timestamp}.parquet
    
    This structure enables:
    - BigQuery external tables with Hive partitioning
    - Efficient date-based queries
    - Easy backfill and reprocessing
    """
    
    # Parquet schema for comparison data
    SCHEMA = pa.schema([
        ('date', pa.date32()),                    # Report date
        ('network', pa.string()),                 # Network name (unity, ironsource, etc.)
        ('platform', pa.string()),                # android / ios
        ('ad_type', pa.string()),                 # banner / interstitial / rewarded
        ('application', pa.string()),             # App name
        ('max_revenue', pa.float64()),            # AppLovin MAX reported revenue
        ('max_impressions', pa.int64()),          # AppLovin MAX reported impressions
        ('max_ecpm', pa.float64()),               # AppLovin MAX eCPM
        ('network_revenue', pa.float64()),        # Network's own reported revenue
        ('network_impressions', pa.int64()),      # Network's own reported impressions
        ('network_ecpm', pa.float64()),           # Network's own eCPM
        ('rev_delta_pct', pa.float64()),          # Revenue difference percentage
        ('imp_delta_pct', pa.float64()),          # Impressions difference percentage
        ('ecpm_delta_pct', pa.float64()),         # eCPM difference percentage
        ('hour_range', pa.string()),              # Hour range for hourly data (Meta only, e.g., '00:00-23:00 UTC (24/24)')
        ('fetched_at', pa.timestamp('us')),       # When data was fetched
    ])
    
    def __init__(
        self,
        project_id: str,
        bucket_name: str,
        service_account_path: Optional[str] = None,
        base_path: str = "network_data"
    ):
        """
        Initialize GCS Exporter.
        
        Args:
            project_id: Google Cloud project ID
            bucket_name: GCS bucket name
            service_account_path: Path to service account JSON file (optional if using default credentials)
            base_path: Base path in bucket for data files
        """
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.base_path = base_path
        self.service_account_path = service_account_path
        self._client = None
        self._bucket = None
    
    def _get_client(self) -> storage.Client:
        """Get or create GCS client."""
        if self._client is None:
            if self.service_account_path and os.path.exists(self.service_account_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_path
                )
                self._client = storage.Client(
                    project=self.project_id,
                    credentials=credentials
                )
            else:
                # Use default credentials (ADC)
                self._client = storage.Client(project=self.project_id)
        return self._client
    
    def _get_bucket(self) -> storage.Bucket:
        """Get or create bucket reference."""
        if self._bucket is None:
            client = self._get_client()
            self._bucket = client.bucket(self.bucket_name)
        return self._bucket
    
    def _parse_delta(self, delta_str: str) -> float:
        """
        Parse delta string (e.g., '+5.2%', '-3.1%', 'N/A') to float.
        
        Args:
            delta_str: Delta string from comparison data
            
        Returns:
            Float value or None if not parseable
        """
        if not delta_str or delta_str == 'N/A' or delta_str == '-':
            return None
        try:
            # Remove % and + signs, convert to float
            clean = delta_str.replace('%', '').replace('+', '').strip()
            return float(clean)
        except (ValueError, AttributeError):
            return None
    
    def _comparison_rows_to_table(
        self,
        comparison_rows: List[Dict[str, Any]],
        report_date: datetime
    ) -> pa.Table:
        """
        Convert comparison rows to PyArrow Table.
        
        Args:
            comparison_rows: List of comparison dictionaries from ValidationService
            report_date: The date the report is for
            
        Returns:
            PyArrow Table ready for Parquet export
        """
        # Prepare column arrays
        dates = []
        networks = []
        platforms = []
        ad_types = []
        applications = []
        max_revenues = []
        max_impressions = []
        max_ecpms = []
        network_revenues = []
        network_impressions_list = []
        network_ecpms = []
        rev_deltas = []
        imp_deltas = []
        ecpm_deltas = []
        hour_ranges = []
        fetched_ats = []
        
        fetched_at = datetime.utcnow()
        
        for row in comparison_rows:
            # Parse application to extract platform
            app_name = row.get('application', '')
            platform = 'android' if 'Android' in app_name else 'ios' if 'iOS' in app_name else 'unknown'
            clean_app_name = app_name.replace(' (Android)', '').replace(' (iOS)', '').strip()
            
            # Keep network name as-is (with Bidding suffix for Looker display)
            network = row.get('network', '')
            
            dates.append(report_date.date())
            networks.append(network)
            platforms.append(platform)
            ad_types.append(row.get('ad_type', '').lower())
            applications.append(clean_app_name)
            max_revenues.append(float(row.get('max_revenue', 0) or 0))
            max_impressions.append(int(row.get('max_impressions', 0) or 0))
            max_ecpms.append(float(row.get('max_ecpm', 0) or 0))
            network_revenues.append(float(row.get('network_revenue', 0) or 0))
            network_impressions_list.append(int(row.get('network_impressions', 0) or 0))
            network_ecpms.append(float(row.get('network_ecpm', 0) or 0))
            rev_deltas.append(self._parse_delta(row.get('rev_delta', '')))
            imp_deltas.append(self._parse_delta(row.get('imp_delta', '')))
            ecpm_deltas.append(self._parse_delta(row.get('cpm_delta', '')))
            hour_ranges.append(row.get('hour_range'))  # Only Meta has this field
            fetched_ats.append(fetched_at)
        
        # Create PyArrow arrays
        table = pa.table({
            'date': pa.array(dates, type=pa.date32()),
            'network': pa.array(networks, type=pa.string()),
            'platform': pa.array(platforms, type=pa.string()),
            'ad_type': pa.array(ad_types, type=pa.string()),
            'application': pa.array(applications, type=pa.string()),
            'max_revenue': pa.array(max_revenues, type=pa.float64()),
            'max_impressions': pa.array(max_impressions, type=pa.int64()),
            'max_ecpm': pa.array(max_ecpms, type=pa.float64()),
            'network_revenue': pa.array(network_revenues, type=pa.float64()),
            'network_impressions': pa.array(network_impressions_list, type=pa.int64()),
            'network_ecpm': pa.array(network_ecpms, type=pa.float64()),
            'rev_delta_pct': pa.array(rev_deltas, type=pa.float64()),
            'imp_delta_pct': pa.array(imp_deltas, type=pa.float64()),
            'ecpm_delta_pct': pa.array(ecpm_deltas, type=pa.float64()),
            'hour_range': pa.array(hour_ranges, type=pa.string()),
            'fetched_at': pa.array(fetched_ats, type=pa.timestamp('us')),
        })
        
        return table
    
    def _get_gcs_path(self, report_date: datetime, network: str, platform: str) -> str:
        """
        Generate GCS path for data file.
        
        Args:
            report_date: Report date
            network: Network name
            platform: Platform (android/ios)
            
        Returns:
            GCS blob path (without gs://bucket prefix)
        """
        date_str = report_date.strftime('%Y-%m-%d')
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        return f"{self.base_path}/dt={date_str}/{network}_{platform}_{timestamp}.parquet"
    
    def _get_local_path(self, output_dir: str, report_date: datetime, network: str, platform: str) -> str:
        """
        Generate local file path for dry-run mode.
        
        Args:
            output_dir: Local output directory
            report_date: Report date
            network: Network name
            platform: Platform (android/ios)
            
        Returns:
            Local file path
        """
        date_str = report_date.strftime('%Y-%m-%d')
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        dir_path = os.path.join(output_dir, f"dt={date_str}")
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, f"{network}_{platform}_{timestamp}.parquet")
    
    def export_to_local(
        self,
        comparison_rows: List[Dict[str, Any]],
        report_date: datetime,
        output_dir: str = "./output"
    ) -> List[str]:
        """
        Export comparison data to local Parquet files (dry-run mode).
        
        Args:
            comparison_rows: List of comparison dictionaries
            report_date: The date the report is for
            output_dir: Local directory for output files
            
        Returns:
            List of created file paths
        """
        if not comparison_rows:
            print("⚠️  No data to export")
            return []
        
        # Group data by network and platform
        grouped_data = self._group_by_network_platform(comparison_rows)
        
        created_files = []
        table = self._comparison_rows_to_table(comparison_rows, report_date)
        
        # For simplicity, write all data to a single file per date
        date_str = report_date.strftime('%Y-%m-%d')
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        dir_path = os.path.join(output_dir, f"dt={date_str}")
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f"comparison_data_{timestamp}.parquet")
        pq.write_table(table, file_path, compression='snappy')
        created_files.append(file_path)
        
        print(f"✅ Exported {len(comparison_rows)} rows to {file_path}")
        return created_files
    
    def export_to_gcs(
        self,
        comparison_rows: List[Dict[str, Any]],
        report_date: datetime
    ) -> List[str]:
        """
        Export comparison data to Google Cloud Storage.
        
        Automatically deletes any existing files for the same date to prevent
        duplicate data in BigQuery external tables.
        
        Args:
            comparison_rows: List of comparison dictionaries
            report_date: The date the report is for
            
        Returns:
            List of GCS URIs for uploaded files
        """
        if not comparison_rows:
            print("⚠️  No data to export")
            return []
        
        # Delete existing files for this date to prevent duplicates
        date_str = report_date.strftime('%Y-%m-%d')
        self._delete_existing_files_for_date(date_str)
        
        table = self._comparison_rows_to_table(comparison_rows, report_date)
        
        # Generate GCS path
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        blob_path = f"{self.base_path}/dt={date_str}/comparison_data_{timestamp}.parquet"
        
        # Write to temporary local file first
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            pq.write_table(table, tmp_path, compression='snappy')
            
            # Upload to GCS
            bucket = self._get_bucket()
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(tmp_path)
            
            gcs_uri = f"gs://{self.bucket_name}/{blob_path}"
            print(f"✅ Uploaded {len(comparison_rows)} rows to {gcs_uri}")
            return [gcs_uri]
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    def _delete_existing_files_for_date(self, date_str: str) -> int:
        """
        Delete all existing parquet files for a specific date.
        
        This prevents duplicate data when re-running exports for the same date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Number of files deleted
        """
        bucket = self._get_bucket()
        prefix = f"{self.base_path}/dt={date_str}/"
        
        blobs = list(bucket.list_blobs(prefix=prefix))
        deleted_count = 0
        
        for blob in blobs:
            print(f"   🗑️  Deleting existing file: {blob.name}")
            blob.delete()
            deleted_count += 1
        
        if deleted_count > 0:
            print(f"   ✅ Deleted {deleted_count} existing file(s) for {date_str}")
        
        return deleted_count
    
    def _group_by_network_platform(
        self,
        comparison_rows: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group comparison rows by network and platform.
        
        Args:
            comparison_rows: List of comparison dictionaries
            
        Returns:
            Dictionary with keys like 'unity_android' and values as row lists
        """
        grouped = {}
        for row in comparison_rows:
            app_name = row.get('application', '')
            platform = 'android' if 'Android' in app_name else 'ios' if 'iOS' in app_name else 'unknown'
            
            network = row.get('network', '').lower()
            network = network.replace(' bidding', '').replace(' ads', '').strip()
            
            key = f"{network}_{platform}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(row)
        
        return grouped
    
    def export(
        self,
        comparison_rows: List[Dict[str, Any]],
        report_date: datetime,
        dry_run: bool = False,
        output_dir: str = "./output"
    ) -> List[str]:
        """
        Export comparison data (unified interface).
        
        Args:
            comparison_rows: List of comparison dictionaries
            report_date: The date the report is for
            dry_run: If True, export to local files; if False, upload to GCS
            output_dir: Local directory for dry-run output
            
        Returns:
            List of file paths (local) or GCS URIs (upload)
        """
        if dry_run:
            return self.export_to_local(comparison_rows, report_date, output_dir)
        else:
            return self.export_to_gcs(comparison_rows, report_date)


def create_exporter_from_config(config: Dict[str, Any]) -> Optional[GCSExporter]:
    """
    Factory function to create GCSExporter from configuration dictionary.
    
    Args:
        config: GCP configuration dictionary with keys:
            - project_id: GCP project ID
            - bucket_name: GCS bucket name
            - service_account_path: Path to service account JSON (optional)
            - base_path: Base path in bucket (optional, default: 'network_data')
            
    Returns:
        GCSExporter instance or None if configuration is invalid
    """
    if not config or not config.get('enabled', False):
        return None
    
    project_id = config.get('project_id')
    bucket_name = config.get('bucket_name')
    
    if not project_id or not bucket_name:
        print("⚠️  GCP configuration incomplete: project_id and bucket_name required")
        return None
    
    return GCSExporter(
        project_id=project_id,
        bucket_name=bucket_name,
        service_account_path=config.get('service_account_path'),
        base_path=config.get('base_path', 'network_data')
    )
