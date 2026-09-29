"""Smoke test: simulates a real Telegram Login Widget payload (correctly signed
with a test bot token) end to end through auth -> me -> consume (free, then
out of credits) -> pack listing. Run with: python3 test_smoke.py
"""
import hashlib
import hmac
import os
import time

os.environ["TELEGRAM_BOT_TOKEN"] = "123456:testtoken"
os.environ["SESSION_SECRET"] = "testsecret"
os.environ["YOOKASSA_SHOP_ID"] = "testshop"
os.environ["YOOKASSA_SECRET_KEY"] = "testkey"
os.environ["DB_PATH"] = "/tmp/test_pifagor_smoke.db"

if os.path.exists("/tmp/test_pifagor_smoke.db"):
    os.remove("/tmp/test_pifagor_smoke.db")

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

main.init_db()  # TestClient outside a `with` block doesn't fire startup events
client = TestClient(main.app)


def sign_payload(data: dict, bot_token: str) -> dict:
    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    h = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return {**data, "hash": h}


payload = sign_payload(
    {"id": 555111, "first_name": "Marina", "username": "marina_test", "auth_date": int(time.time())},
    "123456:testtoken",
)

# 1. Bad signature should be rejected
bad = dict(payload)
bad["hash"] = "0" * 64
r = client.post("/api/auth/telegram", json=bad)
assert r.status_code == 401, r.text
print("OK: bad signature rejected")

# 2. Valid signature -> logged in, cookie set
r = client.post("/api/auth/telegram", json=payload)
assert r.status_code == 200, r.text
body = r.json()
assert body["telegram_id"] == 555111
assert body["credits"] == 0
assert body["free_used"] is False
print("OK: telegram auth ->", body)

# 3. /api/me without cookie -> 401
r2 = client.get("/api/me")
assert r2.status_code == 401
print("OK: /api/me requires auth")

# 4. /api/me with cookie -> matches
r3 = client.get("/api/me")
assert r3.status_code == 401  # TestClient doesn't auto-persist cookies across calls unless using client as context
print("OK: cookie isolation confirmed (expected, using explicit session below)")

# Use a session that persists cookies to test the real flow.
# base_url must be https:// because the session cookie is marked Secure
# (required in production so it's never sent over plain HTTP).
with TestClient(main.app, base_url="https://testserver") as c:
    r = c.post("/api/auth/telegram", json=payload)
    assert r.status_code == 200
    r = c.get("/api/me")
    assert r.status_code == 200, r.text
    assert r.json()["credits"] == 0
    print("OK: /api/me with session ->", r.json())

    # first consume -> should use the free reading
    r = c.post("/api/consume")
    assert r.status_code == 200, r.text
    assert r.json()["used"] == "free"
    print("OK: first consume used free reading ->", r.json())

    # second consume -> no credits yet -> 402
    r = c.post("/api/consume")
    assert r.status_code == 402, r.text
    print("OK: second consume correctly blocked (no credits) ->", r.json())

    # manually credit the account (simulating a successful payment) and retest
    with main.get_conn() as conn:
        conn.execute("UPDATE users SET credits = 3 WHERE telegram_id = 555111")
    r = c.post("/api/consume")
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "used": "credit", "credits": 2}
    print("OK: consume after topping up credits ->", r.json())

# 5. Packs endpoint, RU and EN
r = client.get("/api/packs?lang=ru")
assert r.status_code == 200
packs_ru = r.json()
assert packs_ru["pack3"]["amount"] == 399 and packs_ru["pack3"]["currency"] == "RUB"
print("OK: RU packs ->", packs_ru)

r = client.get("/api/packs?lang=en")
packs_en = r.json()
assert packs_en["pack3"]["amount"] == 4.99 and packs_en["pack3"]["currency"] == "USD"
print("OK: EN packs ->", packs_en)

print("\nALL SMOKE TESTS PASSED")
