from fastapi.testclient import TestClient
import v1.main as main_module
from v1.main import app

client = TestClient(app)


def test_websocket_gateway_connection_lifecycle():
    """Verify that the WebSocket connection accepts clients, sets _gateway_ws, and resets it on disconnect."""
    # Ensure initially it is None
    assert main_module._gateway_ws is None

    # Connect to the WebSocket endpoint
    with client.websocket_connect("/ws/gateway") as websocket:
        # Once connected, the global variable should hold the reference
        assert main_module._gateway_ws is not None
        
        # We can send messages to keep the connection alive or trigger the handler
        websocket.send_text("ping")

    # Once the context block exits, the socket disconnects and global state is reset
    assert main_module._gateway_ws is None
