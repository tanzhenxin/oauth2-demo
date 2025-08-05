import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)

def test_device_authorization_flow():
    resp = client.post("/device_authorization", data={"client_id": "cli-client"})
    assert resp.status_code == 200
    data = resp.json()
    assert "device_code" in data
    device_code = data["device_code"]
    user_code = data["user_code"]

    # simulate user visiting verification URL
    verify_resp = client.get("/device", params={"user_code": user_code})
    assert verify_resp.status_code == 200

    token_resp = client.post(
        "/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": "cli-client",
            "client_secret": "secret",
        },
    )
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    assert "access_token" in token_data
