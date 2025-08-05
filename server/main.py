import uuid
import time
from typing import Optional

import requests
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI(title="OAuth2 Demo Server")

# In-memory stores
clients = {
    "browser-client": {
        "client_secret": "secret",
        "redirect_uri": "http://localhost:8000/client/callback",
    },
    "cli-client": {
        "client_secret": "secret",
        "redirect_uri": None,
    },
}

auth_codes = {}
device_codes = {}
tokens = {}


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
    client = clients.get(client_id)
    if not client or client["redirect_uri"] != redirect_uri:
        return HTMLResponse("Invalid client", status_code=400)
    code = uuid.uuid4().hex
    auth_codes[code] = {"client_id": client_id}
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
):
    if grant_type == "authorization_code":
        if code not in auth_codes:
            return {"error": "invalid_grant"}
        client = clients.get(client_id)
        if (
            not client
            or client["client_secret"] != client_secret
            or client["redirect_uri"] != redirect_uri
        ):
            return {"error": "invalid_client"}
        access_token = uuid.uuid4().hex
        tokens[access_token] = {"client_id": client_id}
        del auth_codes[code]
        return {"access_token": access_token, "token_type": "bearer"}
    elif grant_type == "urn:ietf:params:oauth:grant-type:device_code":
        record = device_codes.get(device_code)
        if not record:
            return {"error": "invalid_grant"}
        if not record.get("approved"):
            return {"error": "authorization_pending"}
        access_token = uuid.uuid4().hex
        tokens[access_token] = {"client_id": record["client_id"]}
        del device_codes[device_code]
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        return {"error": "unsupported_grant_type"}


# ---- Device Authorization Flow ----
@app.post("/device_authorization")
def device_authorization(client_id: str = Form(...)):
    if client_id not in clients:
        return {"error": "invalid_client"}
    device_code = uuid.uuid4().hex
    user_code = uuid.uuid4().hex[:8]
    device_codes[device_code] = {
        "user_code": user_code,
        "client_id": client_id,
        "approved": False,
    }
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
        for record in device_codes.values():
            if record["user_code"] == user_code:
                record["approved"] = True
                return HTMLResponse(
                    "<p>Device authorized. You may return to your device.</p>"
                )
        return HTMLResponse("<p>Invalid user code.</p>", status_code=400)
    html = (
        "<form method='get'>"
        "<label>User Code: <input name='user_code'/></label>"
        "<button type='submit'>Submit</button></form>"
    )
    return HTMLResponse(html)
