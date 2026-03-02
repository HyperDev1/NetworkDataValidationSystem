"""
Tests for server.py /validate endpoint response code logic.

Covers:
    Test 1: empty failed_networks → 200
    Test 2: one failed network → 500
    Test 3: multiple failed networks → 500
    Test 4: exception raised during validation → 500 (existing behavior preserved)
    Test 5: partial failure 500 body contains status="completed" (not "error")

Import strategy:
    server.py imports `from main import run_validation`, which transitively requires
    pyarrow, google-cloud libs, GCP credentials, and also replaces sys.stdout at module
    level (breaks pytest capture). We stub `main` and all heavy transitive deps in
    sys.modules before importing server so the Flask app can be imported and tested in
    isolation without any of those side-effects.
"""
import sys
import types
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import pytest


# ---------------------------------------------------------------------------
# Stub out all transitive deps BEFORE importing server / main.
# Order matters: stubs must be registered before any import of server.py.
# ---------------------------------------------------------------------------

def _stub(name):
    mod = types.ModuleType(name)
    # Make attribute access return new MagicMocks so sub-attribute chains work
    mod.__getattr__ = lambda self, attr: MagicMock()  # type: ignore[attr-defined]
    return mod


_STUBS = [
    'pyarrow',
    'pyarrow.parquet',
    'google',
    'google.cloud',
    'google.cloud.storage',
    'google.cloud.bigquery',
    'google.auth',
    'google.auth.transport',
    'google.auth.transport.requests',
    'google.oauth2',
    'google.oauth2.service_account',
    'google.oauth2.credentials',
    'google.api_core',
    'google.api_core.exceptions',
    'src.exporters.gcs_exporter',
    'src.exporters',
    'src.notifiers.slack_notifier',
    'src.notifiers',
    'src.fetchers.factory',
    'src.fetchers.applovin_fetcher',
    'src.fetchers',
    'src.enums',
]

for _name in _STUBS:
    if _name not in sys.modules:
        sys.modules[_name] = MagicMock()

# Stub the `main` module completely to prevent sys.stdout replacement and
# transitive heavy imports.  server.py only needs `run_validation` from it.
_main_stub = types.ModuleType('main')
_main_stub.run_validation = AsyncMock()  # type: ignore[attr-defined]
sys.modules['main'] = _main_stub

# Now import server — this should succeed without side-effects
import server  # noqa: E402
from server import app  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def make_validation_result(failed_networks=None, network_keys=None):
    """Build a mock run_validation result dict."""
    if failed_networks is None:
        failed_networks = []
    if network_keys is None:
        network_keys = ['meta', 'unity']
    network_data = {k: {} for k in network_keys}
    return {
        'network_data': network_data,
        'failed_networks': failed_networks,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidateResponseCodes:

    def test_empty_failed_networks_returns_200(self, client):
        """Test 1: result with failed_networks=[] → validate() returns HTTP 200."""
        mock_result = make_validation_result(failed_networks=[], network_keys=['meta', 'unity'])

        with patch('server.Config'), \
             patch('server.run_validation', new_callable=AsyncMock, return_value=mock_result):
            response = client.post('/validate')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'completed'
        assert data['failed'] == []

    def test_one_failed_network_returns_500(self, client):
        """Test 2: result with failed_networks=["meta"] → validate() returns HTTP 500."""
        mock_result = make_validation_result(failed_networks=['meta'], network_keys=['meta', 'unity'])

        with patch('server.Config'), \
             patch('server.run_validation', new_callable=AsyncMock, return_value=mock_result):
            response = client.post('/validate')

        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'completed'
        assert 'meta' in data['failed']

    def test_multiple_failed_networks_returns_500(self, client):
        """Test 3: result with failed_networks=["meta", "unity"] → validate() returns HTTP 500."""
        mock_result = make_validation_result(
            failed_networks=['meta', 'unity'],
            network_keys=['meta', 'unity']
        )

        with patch('server.Config'), \
             patch('server.run_validation', new_callable=AsyncMock, return_value=mock_result):
            response = client.post('/validate')

        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'completed'
        assert 'meta' in data['failed']
        assert 'unity' in data['failed']

    def test_exception_returns_500_error(self, client):
        """Test 4: exception raised during validation → validate() returns HTTP 500 (existing behavior preserved)."""
        with patch('server.Config', side_effect=Exception('Config load failed')):
            response = client.post('/validate')

        assert response.status_code == 500
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Config load failed' in data['message']

    def test_partial_failure_body_has_completed_status(self, client):
        """Test 5: 500 partial failure body contains status="completed" (not "error") and failed=["meta"]."""
        mock_result = make_validation_result(failed_networks=['meta'], network_keys=['meta'])

        with patch('server.Config'), \
             patch('server.run_validation', new_callable=AsyncMock, return_value=mock_result):
            response = client.post('/validate')

        assert response.status_code == 500
        data = response.get_json()
        # Distinguishes partial failure from system crash
        assert data['status'] == 'completed', "Partial failure should be 'completed', not 'error'"
        assert data['failed'] == ['meta']
        assert 'networks_processed' in data
