"""
Main entry point for the Network Data Validation System.

Optimized with asyncio for parallel network fetching.
"""
import sys
import io
import time
import asyncio
import logging
import schedule
from datetime import datetime
from src.config import Config
from src.validation_service import ValidationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def run_validation_check(service: ValidationService, start_date=None, end_date=None):
    """
    Run a single validation check.
    
    Args:
        service: ValidationService instance
        start_date: Optional start date for backfill
        end_date: Optional end date for backfill
    """
    try:
        print("\n" + "=" * 60)
        # Run async validation using asyncio.run()
        result = asyncio.run(service.run_validation(start_date=start_date, end_date=end_date))
        print("=" * 60 + "\n")
        
        if not result['success']:
            logger.error(f"Validation check failed: {result.get('message', 'Unknown error')}")
            print(f"Validation check failed: {result.get('message', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Error during validation check: {e}", exc_info=True)
        print(f"Error during validation check: {str(e)}")


def main():
    """Main function."""
    print("Network Data Validation System")
    print("=" * 60)
    
    # Check command line arguments first
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("\nKullanım:")
        print("  python main.py              - Bir kez çalıştır ve çık (varsayılan)")
        print("  python main.py --schedule   - Zamanlamayı başlat (09:30 ve 17:30)")
        print("  python main.py --schedule-now - Önce çalıştır, sonra zamanlamayı başlat")
        print("  python main.py --test-slack - Slack bağlantısını test et")
        print("  python main.py --start-date 2026-01-01 --end-date 2026-01-10 - Belirli tarih aralığı için backfill")
        print("  python main.py --help       - Bu yardım mesajını göster")
        sys.exit(0)
    
    # Load configuration
    try:
        config = Config()
        print("✅ Configuration loaded successfully")
    except FileNotFoundError as e:
        print(f"❌ {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to load configuration: {str(e)}")
        sys.exit(1)
    
    # Initialize service
    service = ValidationService(config)
    
    # Parse date arguments
    start_date = None
    end_date = None
    
    if '--start-date' in sys.argv:
        idx = sys.argv.index('--start-date')
        if idx + 1 < len(sys.argv):
            start_date = datetime.strptime(sys.argv[idx + 1], '%Y-%m-%d')
    
    if '--end-date' in sys.argv:
        idx = sys.argv.index('--end-date')
        if idx + 1 < len(sys.argv):
            end_date = datetime.strptime(sys.argv[idx + 1], '%Y-%m-%d')
    
    # If start_date provided but not end_date, use start_date as end_date
    if start_date and not end_date:
        end_date = start_date
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test-slack':
            # Test Slack integration
            service.test_slack_integration()
            sys.exit(0)
        elif sys.argv[1] == '--schedule':
            # Run with fixed time scheduling (09:30 and 17:30)
            print("\n🕐 Zamanlama aktif!")
            print("   📅 Her gün saat 09:30 ve 17:30'da çalışacak")
            print("   ⏰ Şu anki saat:", datetime.now().strftime("%H:%M:%S"))
            print("\nDurdurmak için Ctrl+C basın\n")
            
            # Schedule at specific times
            schedule.every().day.at("09:30").do(lambda: run_validation_check(service))
            schedule.every().day.at("17:30").do(lambda: run_validation_check(service))
            
            # Show next run time
            next_run = schedule.next_run()
            if next_run:
                print(f"⏳ Sonraki çalışma zamanı: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Keep running
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                print("\n\n🛑 Kapatılıyor...")
                sys.exit(0)
        elif sys.argv[1] == '--schedule-now':
            # Run immediately then continue with schedule
            print("\n🕐 Zamanlama aktif (önce bir kez çalıştırılacak)!")
            print("   📅 Her gün saat 09:30 ve 17:30'da çalışacak")
            print("   ⏰ Şu anki saat:", datetime.now().strftime("%H:%M:%S"))
            print("\nDurdurmak için Ctrl+C basın\n")
            
            # Run immediately
            print("🚀 Şimdi çalıştırılıyor...\n")
            run_validation_check(service)
            
            # Schedule at specific times
            schedule.every().day.at("09:30").do(lambda: run_validation_check(service))
            schedule.every().day.at("17:30").do(lambda: run_validation_check(service))
            
            # Show next run time
            next_run = schedule.next_run()
            if next_run:
                print(f"\n⏳ Sonraki çalışma zamanı: {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Keep running
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(30)
            except KeyboardInterrupt:
                print("\n\n🛑 Kapatılıyor...")
                sys.exit(0)
    
    # Default: Run once and exit (with optional date range)
    if start_date:
        print(f"\n🔄 Backfill mode: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        from datetime import timedelta
        current = start_date
        while current <= end_date:
            print(f"\n{'='*60}")
            print(f"📅 Processing: {current.strftime('%Y-%m-%d')}")
            print(f"{'='*60}")
            run_validation_check(service, start_date=current, end_date=current)
            current += timedelta(days=1)
    else:
        run_validation_check(service)
    print("\nDone.")
    sys.exit(0)


if __name__ == "__main__":
    main()
