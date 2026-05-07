"""E2E test fixtures — reuse integration conftest fixtures."""
# Re-export all fixtures from integration conftest so e2e tests can use them.
from tests.integration.conftest import (  # noqa: F401
    anyio_backend,
    test_engine,
    db_session,
    mock_kafka_producer,
    mock_redis,
    client,
    auth_headers,
    admin_auth_headers,
)
