"""
Network Data Validation System - Flask HTTP Server

This is the container entry point for Cloud Run deployment.
Exposes HTTP endpoints for health checking and validation triggering.

Separate from the CLI entry point (main.py) — both coexist.
"""
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from flask import Flask, jsonify

from main import run_validation
from src.config import Config

# Configure logging (same format as main.py)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Read PORT from environment (Cloud Run convention), default to 8080
port = int(os.environ.get('PORT', 8080))


@app.route('/health', methods=['GET'])
def health_check() -> tuple:
    """
    Health check endpoint.

    Returns HTTP 200 with {"status": "healthy"}.
    No side effects, no config loading — always fast and always succeeds.
    Used by Cloud Run to determine container readiness.
    """
    return jsonify({"status": "healthy"}), 200


@app.route('/validate', methods=['POST'])
def validate() -> tuple:
    """
    Validation trigger endpoint.

    Loads config, calculates date range, runs the validation pipeline,
    and returns a JSON summary of results.

    Returns:
        200: {"status": "completed", "networks_processed": N, "failed": []}
             All networks succeeded.
        500: {"status": "completed", "networks_processed": N, "failed": [...]}
             One or more networks failed. Cloud Scheduler will retry.
        500: {"status": "error", "message": "..."}
             Unhandled exception during validation.
    """
    try:
        logger.info("Validation triggered via HTTP POST /validate")

        # Load config from default path (config.yaml — volume-mounted in container)
        config = Config()

        # Calculate date range: end_date = UTC now - 1 day, start_date = end_date - 7 days
        # Same logic as run_single_validation in main.py
        now_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now_utc - timedelta(days=1)
        start_date = end_date - timedelta(days=7)

        logger.info(
            "Running validation for date range %s -> %s",
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

        # Bridge async run_validation into sync Flask handler
        result: Dict[str, Any] = asyncio.run(
            run_validation(config, start_date, end_date)
        )

        # Build response summary
        # networks_processed = count of network keys in result (exclude internal keys starting with _)
        network_data = result.get('network_data', {})
        networks_processed = len([k for k in network_data.keys() if not k.startswith('_')])

        # Extract failed networks list
        failed = result.get('failed_networks', [])

        logger.info(
            "Validation completed: %d networks processed, %d failed",
            networks_processed,
            len(failed)
        )

        if len(failed) == 0:
            return jsonify({
                "status": "completed",
                "networks_processed": networks_processed,
                "failed": failed,
            }), 200
        else:
            # One or more networks failed — return 500 so Cloud Scheduler retries.
            # Use status="completed" (not "error") to distinguish partial network
            # failure from an unhandled system exception (which uses status="error").
            return jsonify({
                "status": "completed",
                "networks_processed": networks_processed,
                "failed": failed,
            }), 500

    except Exception as e:
        logger.exception("Validation failed with exception: %s", str(e))
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


if __name__ == '__main__':
    logger.info("Starting Flask HTTP server on port %d", port)
    app.run(host='0.0.0.0', port=port, debug=False)
