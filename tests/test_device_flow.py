import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os
import base64
import hashlib
from fastapi.testclient import TestClient
from server.main import app


client = TestClient(app)


def base64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def test_device_authorization_flow():
    code_verifier = base64url_encode(os.urandom(32))
    code_challenge = base64url_encode(
        hashlib.sha256(code_verifier.encode()).digest()
    )
    resp = client.post(
        "/device_authorization",
        data={
            "client_id": "cli-client",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        },
    )
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
            "code_verifier": code_verifier,
        },
    )
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    assert "access_token" in token_data
