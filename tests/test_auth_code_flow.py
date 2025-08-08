import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from server.main import app
from server.database import get_db
from urllib.parse import urlparse, parse_qs

client = TestClient(app)

def test_authorization_code_flow():
    # 1. Authorize
    auth_resp = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": "browser-client",
            "redirect_uri": "http://localhost:8000/client/callback",
            "state": "abc",
        },
        follow_redirects=False,  # We want to inspect the redirect
    )
    assert auth_resp.status_code == 307  # 307 is temporary redirect
    redirect_url = auth_resp.headers["location"]
    parsed_url = urlparse(redirect_url)
    query_params = parse_qs(parsed_url.query)
    assert "code" in query_params
    code = query_params["code"][0]

    # 2. Token
    token_resp = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://localhost:8000/client/callback",
            "client_id": "browser-client",
            "client_secret": "secret",
        },
    )
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    assert "access_token" in token_data
    assert "token_type" in token_data
    assert "expires_in" in token_data
