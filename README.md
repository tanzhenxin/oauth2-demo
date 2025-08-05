# OAuth2 Demo

This repository provides a minimal OAuth2 authorization server and example clients for both browser and CLI environments. It demonstrates:

- **Authorization Code Flow** for browser-based applications and browser-capable CLI sessions.
- **Device Authorization Flow** for non-browser/CLI environments, including QR code support.

## Requirements

- Python 3.11+
- Node.js 18+
- `pip install -r requirements.txt`
- `npm install`

## Running the Server

```bash
uvicorn server.main:app --reload
```

### Browser Client Demo

1. Visit [http://localhost:8000/client](http://localhost:8000/client).
2. Click **Login with OAuth2**.
3. You will be redirected back with an access token displayed.

### CLI Client Demo

```bash
# Device flow (no browser available)
node client/cli_client.js

# Authorization code flow (opens browser)
node client/cli_client.js browser
```

For the device flow, the script prints a verification URL and displays a QR code. Open the URL (or scan the QR code) and authorize the device. The CLI polls the server until authorization completes and then prints the access token.

## Running Tests

```bash
pytest
```
