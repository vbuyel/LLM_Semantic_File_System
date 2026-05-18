import uuid
from unittest.mock import MagicMock
from fastapi import Request
import pytest

from v1.gateway_router import _get_headers


def test_get_headers_with_all_fields():
    """Verify that all headers are correctly extracted when they are present in the request."""
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {
        "Authorization": "Bearer my-token",
        "X-Storage-Source": "google-drive",
        "X-Auth-Provider": "google",
        "X-Owner": "john_doe",
        "X-Correlation-ID": "custom-uuid-123",
    }

    # We pass an empty dict to headers to avoid using the shared default during tests
    headers = _get_headers(mock_request, headers={})

    assert headers["Authorization"] == "Bearer my-token"
    assert headers["X-Storage-Source"] == "google-drive"
    assert headers["X-Auth-Provider"] == "google"
    assert headers["X-Owner"] == "john_doe"
    assert headers["X-Correlation-ID"] == "custom-uuid-123"


def test_get_headers_fallbacks():
    """Verify default fallbacks when headers are missing."""
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {}

    headers = _get_headers(mock_request, headers={})

    # Fallbacks should apply
    assert headers["X-Owner"] == "guest"
    assert "Authorization" not in headers
    assert "X-Storage-Source" not in headers
    assert "X-Auth-Provider" not in headers
    
    # Correlation ID should be a newly generated UUID
    corr_id = headers["X-Correlation-ID"]
    assert corr_id is not None
    # Verify it is a valid UUID
    try:
        uuid.UUID(corr_id)
    except ValueError:
        pytest.fail("X-Correlation-ID is not a valid UUID")


def test_get_headers_state_leak():
    """
    Test for mutable default argument bug in _get_headers.
    If default argument sharing is not fixed, the second request will leak
    the first request's headers.
    """
    # Request 1 with auth and owner
    req1 = MagicMock(spec=Request)
    req1.headers = {
        "Authorization": "Bearer secret-token",
        "X-Owner": "alice",
        "X-Correlation-ID": "corr-alice",
    }
    
    # Request 2 with NO auth and default owner/correlation
    req2 = MagicMock(spec=Request)
    req2.headers = {}

    # Call _get_headers without passing second argument (triggering default {})
    res1 = _get_headers(req1)
    res2 = _get_headers(req2)

    # Let's assert that Alice's details did NOT leak into the second request
    assert res1["Authorization"] == "Bearer secret-token"
    assert res1["X-Owner"] == "alice"
    assert res1["X-Correlation-ID"] == "corr-alice"

    assert "Authorization" not in res2, "SECURITY BUG: Authorization header leaked to another request!"
    assert res2["X-Owner"] == "guest"
    assert res2["X-Correlation-ID"] != "corr-alice", "SECURITY BUG: Correlation ID leaked to another request!"
