import uuid
import time
import hashlib
import base64
from typing import Optional

import requests
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from server.database import init_db, get_db

app = FastAPI(title="OAuth2 Demo Server")

# Initialize the database
init_db()


@app.get("/")
def root():
    return {"message": "OAuth2 Demo"}


# ---- Browser client demo ----
@app.get("/client")
def client_page():
    url = (
        "/authorize?response_type=code&client_id=browser-client"
        "&redirect_uri=http://localhost:8000/client/callback&state=abc"
    )
    html = f"<h1>Browser Client</h1><a href='{url}'>Login with OAuth2</a>"
    return HTMLResponse(html)


@app.get("/client/callback")
def client_callback(code: str, state: Optional[str] = None):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": "browser-client",
        "client_secret": "secret",
        "redirect_uri": "http://localhost:8000/client/callback",
    }
    resp = requests.post("http://localhost:8000/token", data=data)
    token = resp.json()
    return HTMLResponse(
        f"<p>Authorization complete.</p><p>Access Token: {token.get('access_token')}</p>"
    )


# ---- Authorization Code Flow ----
@app.get("/authorize")
def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    state: Optional[str] = None,
    scope: Optional[str] = None,
):
    conn = get_db()
    client = conn.execute(
        "SELECT * FROM clients WHERE client_id = ?", (client_id,)
    ).fetchone()
    if not client or client["redirect_uri"] != redirect_uri:
        conn.close()
        return HTMLResponse("Invalid client", status_code=400)

    code = uuid.uuid4().hex
    expires_at = int(time.time()) + 600  # 10 minutes
    conn.execute(
        "INSERT INTO auth_codes (code, client_id, expires_at) VALUES (?, ?, ?)",
        (code, client_id, expires_at),
    )
    conn.commit()
    conn.close()

    redirect = f"{redirect_uri}?code={code}"
    if state:
        redirect += f"&state={state}"
    return RedirectResponse(url=redirect)


# ---- Token Endpoint ----
@app.post("/token")
def token(
    grant_type: str = Form(...),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    client_id: str = Form(None),
    client_secret: str = Form(None),
    device_code: str = Form(None),
    code_verifier: str = Form(None),
):
    conn = get_db()
    if grant_type == "authorization_code":
        auth_code = conn.execute(
            "SELECT * FROM auth_codes WHERE code = ?", (code,)
        ).fetchone()
        if not auth_code or auth_code["expires_at"] < int(time.time()):
            conn.close()
            return {"error": "invalid_grant"}

        client = conn.execute(
            "SELECT * FROM clients WHERE client_id = ?", (client_id,)
        ).fetchone()
        if (
            not client
            or client["client_secret"] != client_secret
            or client["redirect_uri"] != redirect_uri
        ):
            conn.close()
            return {"error": "invalid_client"}

        access_token = uuid.uuid4().hex
        expires_at = int(time.time()) + 3600  # 1 hour
        conn.execute(
            "INSERT INTO tokens (access_token, client_id, expires_at) VALUES (?, ?, ?)",
            (access_token, client_id, expires_at),
        )
        conn.execute("DELETE FROM auth_codes WHERE code = ?", (code,))
        conn.commit()
        conn.close()
        return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}

    elif grant_type == "urn:ietf:params:oauth:grant-type:device_code":
        record = conn.execute(
            "SELECT * FROM device_codes WHERE device_code = ?", (device_code,)
        ).fetchone()
        if not record or record["expires_at"] < int(time.time()):
            conn.close()
            return {"error": "invalid_grant"}
        if not record["approved"]:
            conn.close()
            return {"error": "authorization_pending"}
        if not code_verifier:
            conn.close()
            return {"error": "invalid_request"}

        digest = hashlib.sha256(code_verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        if challenge != record["code_challenge"]:
            conn.close()
            return {"error": "invalid_grant"}

        access_token = uuid.uuid4().hex
        expires_at = int(time.time()) + 3600  # 1 hour
        conn.execute(
            "INSERT INTO tokens (access_token, client_id, expires_at) VALUES (?, ?, ?)",
            (access_token, record["client_id"], expires_at),
        )
        conn.execute("DELETE FROM device_codes WHERE device_code = ?", (device_code,))
        conn.commit()
        conn.close()
        return {"access_token": access_token, "token_type": "bearer", "expires_in": 3600}

    else:
        conn.close()
        return {"error": "unsupported_grant_type"}


# ---- Device Authorization Flow ----
@app.post("/device_authorization")
def device_authorization(
    client_id: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form("S256"),
):
    conn = get_db()
    client = conn.execute(
        "SELECT * FROM clients WHERE client_id = ?", (client_id,)
    ).fetchone()
    if not client:
        conn.close()
        return {"error": "invalid_client"}

    if code_challenge_method != "S256":
        conn.close()
        return {"error": "invalid_request"}

    device_code = uuid.uuid4().hex
    user_code = uuid.uuid4().hex[:8]
    expires_at = int(time.time()) + 600  # 10 minutes
    conn.execute(
        """
        INSERT INTO device_codes
        (device_code, user_code, client_id, approved, code_challenge, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (device_code, user_code, client_id, False, code_challenge, expires_at),
    )
    conn.commit()
    conn.close()

    verification_uri = "http://localhost:8000/device"
    verification_uri_complete = f"{verification_uri}?user_code={user_code}"
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": verification_uri,
        "verification_uri_complete": verification_uri_complete,
        "expires_in": 600,
        "interval": 5,
    }


@app.get("/device")
def device(user_code: Optional[str] = None):
    if user_code:
        conn = get_db()
        record = conn.execute(
            "SELECT * FROM device_codes WHERE user_code = ?", (user_code,)
        ).fetchone()

        if record:
            conn.execute(
                "UPDATE device_codes SET approved = ? WHERE user_code = ?", (True, user_code)
            )
            conn.commit()
            conn.close()
            return HTMLResponse(
                "<p>Device authorized. You may return to your device.</p>"
            )
        else:
            conn.close()
            return HTMLResponse("<p>Invalid user code.</p>", status_code=400)

    html = (
        "<form method='get'>"
        "<label>User Code: <input name='user_code'/></label>"
        "<button type='submit'>Submit</button></form>"
    )
    return HTMLResponse(html)
