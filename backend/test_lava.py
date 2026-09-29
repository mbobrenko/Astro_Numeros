"""Tests the Lava.top payment flow with httpx calls monkeypatched (no real
network/credentials needed). Verifies: invoice creation stores a pending
payment row and returns a payment URL; missing/invalid email is rejected;
the webhook re-check credits a payment once Lava reports it completed, and
never double-credits on a repeat webhook call.
Run with: python3 test_lava.py
"""
import os
import time
import hashlib
import hmac
import json

os.environ["TELEGRAM_BOT_TOKEN"] = "123456:testtoken"
os.environ["SESSION_SECRET"] = "testsecret"
os.environ["LAVA_API_KEY"] = "test-lava-key"
os.environ["LAVA_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["LAVA_OFFER_PACK3_RU"] = "offer-pack3-ru-uuid"
os.environ["LAVA_OFFER_PACK3_EN"] = "offer-pack3-en-uuid"
os.environ["LAVA_OFFER_PACK10_RU"] = "offer-pack10-ru-uuid"
os.environ["LAVA_OFFER_PACK10_EN"] = "offer-pack10-en-uuid"
os.environ["LAVA_OFFER_PACK15_RU"] = "offer-pack15-ru-uuid"
os.environ["LAVA_OFFER_PACK15_EN"] = "offer-pack15-en-uuid"
os.environ["DB_PATH"] = "/tmp/test_pifagor_lava.db"

if os.path.exists("/tmp/test_pifagor_lava.db"):
    os.remove("/tmp/test_pifagor_lava.db")

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

main.init_db()

# --- fake Lava.top server, swapped in for httpx.post/httpx.get ---
fake_invoices = {}  # invoice_id -> status
next_invoice_id = [1]


class FakeResp:
    def __init__(self, status_code, json_body):
        self.status_code = status_code
        self._json = json_body
        self.text = json.dumps(json_body)

    def json(self):
        return self._json


invoice_requests = []  # records each request body for offerId assertions


def fake_post(url, json=None, headers=None, timeout=None):
    assert url == "https://gate.lava.top/api/v3/invoice"
    assert headers["X-Api-Key"] == "test-lava-key"
    assert json["email"], "email must be present"
    invoice_requests.append(json)
    inv_id = f"inv-{next_invoice_id[0]}"
    next_invoice_id[0] += 1
    fake_invoices[inv_id] = "PENDING"
    return FakeResp(200, {"id": inv_id, "paymentUrl": f"https://lava.top/pay/{inv_id}"})


def fake_get(url, headers=None, timeout=None):
    assert headers["X-Api-Key"] == "test-lava-key"
    inv_id = url.rsplit("/", 1)[-1]
    status = fake_invoices.get(inv_id, "UNKNOWN")
    return FakeResp(200, {"status": status})


main.httpx.post = fake_post
main.httpx.get = fake_get

client = TestClient(main.app, base_url="https://testserver")

with client as c:
    # log in
    def sign(data, token):
        cs = "\n".join(f"{k}={data[k]}" for k in sorted(data))
        key = hashlib.sha256(token.encode()).digest()
        return hmac.new(key, cs.encode(), hashlib.sha256).hexdigest()

    payload = {"id": 777, "first_name": "Marina", "auth_date": int(time.time())}
    payload["hash"] = sign(payload, "123456:testtoken")
    r = c.post("/api/auth/telegram", json=payload)
    assert r.status_code == 200, r.text
    print("OK: logged in")

    # missing email -> 422
    r = c.post("/api/pay/create", json={"pack": "pack3", "lang": "ru"})
    assert r.status_code == 422, r.text
    print("OK: missing email rejected")

    # bad email -> 422
    r = c.post("/api/pay/create", json={"pack": "pack3", "lang": "ru", "email": "not-an-email"})
    assert r.status_code == 422, r.text
    print("OK: malformed email rejected")

    # unknown pack -> 400
    r = c.post("/api/pay/create", json={"pack": "pack999", "lang": "ru", "email": "m@example.com"})
    assert r.status_code == 400, r.text
    print("OK: unknown pack rejected")

    # RU purchase -> RUB currency, RU offerId, no paymentProvider override
    r = c.post("/api/pay/create", json={"pack": "pack10", "lang": "ru", "email": "marina@example.com"})
    assert r.status_code == 200, r.text
    ru_url = r.json()["confirmation_url"]
    assert ru_url.startswith("https://lava.top/pay/")
    ru_req = invoice_requests[-1]
    assert ru_req["offerId"] == "offer-pack10-ru-uuid", ru_req
    assert ru_req["currency"] == "RUB" and "paymentProvider" not in ru_req
    print("OK: RU pack10 purchase created with the RU offerId ->", r.json())

    # EN purchase -> USD currency + PayPal rail + the separate EN offerId
    r = c.post("/api/pay/create", json={"pack": "pack3", "lang": "en", "email": "marina@example.com"})
    assert r.status_code == 200, r.text
    en_url = r.json()["confirmation_url"]
    en_req = invoice_requests[-1]
    assert en_req["offerId"] == "offer-pack3-en-uuid", en_req
    assert en_req["currency"] == "USD" and en_req["paymentProvider"] == "PAYPAL"
    print("OK: EN pack3 purchase created with the separate EN offerId ->", r.json())

    # balance still 0 (nothing paid yet)
    r = c.get("/api/me")
    assert r.json()["credits"] == 0
    print("OK: balance still 0 before payment completes")

    # webhook fires before Lava actually marks anything COMPLETED -> nothing credited yet
    r = c.post("/api/pay/lava/webhook", json={"whatever": "shape"},
               headers={"Authorization": "Basic " + __import__("base64").b64encode(b"x:test-webhook-secret").decode()})
    assert r.status_code == 200, r.text
    print("OK: webhook with nothing completed yet ->", r.json())
    assert r.json()["credited"] == 0

    # webhook without correct auth -> 401
    r = c.post("/api/pay/lava/webhook", json={}, headers={"Authorization": "Basic eDp3cm9uZw=="})
    assert r.status_code == 401, r.text
    print("OK: webhook rejects wrong auth")

    # now mark BOTH fake invoices completed on Lava's side, then re-fire the webhook
    for inv_id in fake_invoices:
        fake_invoices[inv_id] = "COMPLETED"
    r = c.post("/api/pay/lava/webhook", json={"anything": True},
               headers={"Authorization": "Basic " + __import__("base64").b64encode(b"x:test-webhook-secret").decode()})
    assert r.status_code == 200, r.text
    print("OK: webhook after completion ->", r.json())
    assert r.json()["credited"] == 2, "both pending payments should have been credited"

    r = c.get("/api/me")
    balance = r.json()["credits"]
    assert balance == 13, f"expected 10+3=13 credits, got {balance}"
    print("OK: balance after both purchases credited ->", balance)

    # firing the webhook again must NOT double-credit
    r = c.post("/api/pay/lava/webhook", json={},
               headers={"Authorization": "Basic " + __import__("base64").b64encode(b"x:test-webhook-secret").decode()})
    assert r.json()["credited"] == 0, "should not re-credit already-succeeded payments"
    r = c.get("/api/me")
    assert r.json()["credits"] == 13, "balance must not change on repeat webhook"
    print("OK: repeat webhook does not double-credit, balance still ->", r.json()["credits"])

print("\nALL LAVA TESTS PASSED")
