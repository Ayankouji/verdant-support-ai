
import json
import hmac
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
from uuid import uuid4

URL = "http://127.0.0.1:8000/webhook"
SECRET = "verdant-demo-secret-2026"

event_id = "test-" + str(uuid4())

payload = {
    "event_id": event_id,
    "type": "message.received",
    "brand_id": "verdant-co",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "customer": {
        "id": "test-customer-001",
        "name": "Test Customer",
        "phone": "9999999999"
    },
    "message": {
        "id": "test-message-" + str(uuid4()),
        "type": "text",
        "text": "How long does delivery take in Mumbai?"
    }
}

body = json.dumps(payload).encode("utf-8")

signature = hmac.new(
    SECRET.encode("utf-8"),
    body,
    hashlib.sha256
).hexdigest()

def send_request(sig):
    req = urllib.request.Request(
        URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": "sha256=" + sig
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            print("HTTP:", response.status)
            print("Response:", response.read().decode())
    except urllib.error.HTTPError as error:
        print("HTTP:", error.code)
        print("Response:", error.read().decode())

print("\n1. INVALID SIGNATURE TEST")
send_request("wrong-signature")

print("\n2. VALID WEBHOOK TEST")
send_request(signature)

print("\n3. DUPLICATE EVENT TEST")
send_request(signature)
