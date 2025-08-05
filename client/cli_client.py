import time
import requests
import qrcode

SERVER = "http://localhost:8000"
CLIENT_ID = "cli-client"
CLIENT_SECRET = "secret"

def main():
    # Step 1: obtain device code
    resp = requests.post(f"{SERVER}/device_authorization", data={"client_id": CLIENT_ID})
    data = resp.json()
    print("Visit this URL to authorize:")
    print(data["verification_uri_complete"])

    # show QR code
    qr = qrcode.QRCode(border=1)
    qr.add_data(data["verification_uri_complete"])
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    # Step 2: poll token endpoint
    while True:
        token_resp = requests.post(
            f"{SERVER}/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": data["device_code"],
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
        token_json = token_resp.json()
        if token_resp.status_code == 200 and "access_token" in token_json:
            print("Access Token:", token_json["access_token"])
            break
        else:
            print("Waiting for authorization...")
            time.sleep(data.get("interval", 5))

if __name__ == "__main__":
    main()
