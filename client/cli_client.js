#!/usr/bin/env node
import http from 'http';
import { URL, URLSearchParams } from 'url';
import open from 'open';
import qrcode from 'qrcode-terminal';
import crypto from 'crypto';

const SERVER = 'http://localhost:8000';
const CLIENT_ID = 'cli-client';
const CLIENT_SECRET = 'secret';
const REDIRECT_URI = 'http://localhost:8081/callback';

async function runBrowserFlow() {
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, REDIRECT_URI);
    const code = url.searchParams.get('code');
    res.end('Authorization complete. You can close this window.');
    server.close();
    if (!code) {
      console.error('No code received');
      return;
    }
    const tokenResp = await fetch(`${SERVER}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        client_id: CLIENT_ID,
        client_secret: CLIENT_SECRET,
        redirect_uri: REDIRECT_URI,
      }),
    });
    const tokenJson = await tokenResp.json();
    console.log('Access Token:', tokenJson.access_token);
  });
  server.listen(8081, () => {
    const authUrl = new URL(`${SERVER}/authorize`);
    authUrl.searchParams.set('response_type', 'code');
    authUrl.searchParams.set('client_id', CLIENT_ID);
    authUrl.searchParams.set('redirect_uri', REDIRECT_URI);
    authUrl.searchParams.set('state', 'xyz');
    console.log('Opening browser for authorization...');
    open(authUrl.toString());
  });
}

async function runDeviceFlow() {
  const base64url = (buf) =>
    buf
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
  const codeVerifier = base64url(crypto.randomBytes(32));
  const codeChallenge = base64url(
    crypto.createHash('sha256').update(codeVerifier).digest()
  );
  const resp = await fetch(`${SERVER}/device_authorization`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: CLIENT_ID,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
    }),
  });
  const data = await resp.json();
  console.log('Visit this URL to authorize:');
  console.log(data.verification_uri_complete);
  qrcode.generate(data.verification_uri_complete, { small: true });

  while (true) {
    await new Promise((r) => setTimeout(r, (data.interval || 5) * 1000));
    const tokenResp = await fetch(`${SERVER}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'urn:ietf:params:oauth:grant-type:device_code',
        device_code: data.device_code,
        client_id: CLIENT_ID,
        code_verifier: codeVerifier,
      }),
    });
    const tokenJson = await tokenResp.json();
    if (tokenJson.access_token) {
      console.log('Access Token:', tokenJson.access_token);
      break;
    }
    if (tokenJson.error && tokenJson.error !== 'authorization_pending') {
      console.error('Error:', tokenJson.error);
      break;
    }
    console.log('Waiting for authorization...');
  }
}

const mode = process.argv[2];
if (mode === 'browser') {
  runBrowserFlow();
} else {
  runDeviceFlow();
}
