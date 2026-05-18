import os
import sys
from pathlib import Path
import pytest

# Add the src/gateway_auth directory to the sys.path so modules can be imported directly
gateway_auth_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(gateway_auth_dir))

# Set up mock environment variables for service configuration
os.environ["OAUTH_GOOGLE_CLIENT_ID"] = "mock-client-id"
os.environ["OAUTH_GOOGLE_CLIENT_SECRET"] = "mock-client-secret"
os.environ["OAUTH_GOOGLE_REDIRECT_URI"] = "http://localhost:5500/auth/google"
os.environ["OAUTH_GOOGLE_BASE_URL"] = "http://localhost:8000"
os.environ["AGENT_SERVER"] = "http://localhost:8001"
os.environ["FILE_OPS_SERVER"] = "http://localhost:8002"
os.environ["EVENT_DB_URL"] = "http://localhost:8003"
os.environ["EVENT_DB_WS_URL"] = "ws://localhost:8003/ws/gateway"
