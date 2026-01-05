"""
Main entry point for the Network Data Validation System.
"""
import sys
import io
import time
import schedule
from datetime import datetime
from src.config import Config
from src.validation_service import ValidationService

# Fix console encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def run_validation_check(service: ValidationService):
    """
    Run a single validation check.
    
    Args:
        service: ValidationService instance
    """
    try:
        print("\n" + "=" * 60)
        result = service.run_validation()
        print("=" * 60 + "\n")
        
        if not result['success']:
            print(f"Validation check failed: {result.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"Error during validation check: {str(e)}")


def main():
    """Main function."""
    print("Network Data Validation System")
    print("=" * 60)
    
    # Check command line arguments first
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("\nUsage:")
        print("  python main.py              - Run validation once and exit (default)")
        print("  python main.py --schedule   - Run with scheduling (continuous)")
        print("  python main.py --test-slack - Test Slack integration")
        print("  python main.py --help       - Show this help message")
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
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test-slack':
            # Test Slack integration
            service.test_slack_integration()
            sys.exit(0)
        elif sys.argv[1] == '--schedule':
            # Run with scheduling
            scheduling_config = config.get_scheduling_config()
            interval_hours = scheduling_config.get('interval_hours', 6)
            
            print(f"\n🔄 Scheduling validation checks every {interval_hours} hour(s)")
            print("Press Ctrl+C to stop\n")
            
            # Run immediately on start
            run_validation_check(service)
            
            # Schedule periodic runs
            schedule.every(interval_hours).hours.do(lambda: run_validation_check(service))
            
            # Keep running
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                print("\n\nShutting down...")
                sys.exit(0)
    
    # Default: Run once and exit
    run_validation_check(service)
    print("\nDone.")
    sys.exit(0)


if __name__ == "__main__":
    main()
