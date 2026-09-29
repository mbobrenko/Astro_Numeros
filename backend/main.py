"""
Backend API for "Квадрат Пифагора" — Telegram-based auth, credit balance
for paid "разборы" (readings), and payments.

Payment provider: Lava.top (gate.lava.top) is the active processor for both
audiences — RUB/RU-card checkout for the ru UI, USD via Lava's PayPal rail for
the en UI, from one integration. The earlier YooKassa integration is kept
in place but dormant (routes under /api/pay/yookassa/*, not called by the
frontend) in case it's needed again later.

NOTE on Lava.top field names: gate.lava.top's own docs pages returned 403s
when this integration was written, so the exact request/response field names
below are reconstructed from secondary sources (their public API overview,
a third-party SDK's README, and a real integration's bugfix notes — see the
comments near LAVA_API_BASE). Before relying on this in production, run
lava_test_invoice.py once with real credentials and compare the raw response
against what invoice-creation/webhook code below expects, and adjust field
names if they differ.

Run locally for testing:
    pip install -r requirements.txt
    export TELEGRAM_BOT_TOKEN=...       # from @BotFather
    export SESSION_SECRET=some-long-random-string
    export LAVA_API_KEY=...             # Lava.top dashboard -> Integrations -> API
    export LAVA_WEBHOOK_SECRET=...      # the webhook key you set in that same dashboard page
    export LAVA_OFFER_PACK3_RU=...      # offerId (UUID) of the RU "3 readings" product in Lava.top
    export LAVA_OFFER_PACK3_EN=...      # offerId (UUID) of the EN "3 readings" product in Lava.top
    export LAVA_OFFER_PACK10_RU=...
    export LAVA_OFFER_PACK10_EN=...
    export LAVA_OFFER_PACK15_RU=...
    export LAVA_OFFER_PACK15_EN=...
    export FRONTEND_URL=https://your-domain.example
    uvicorn main:app --host 0.0.0.0 --port 8000

In production this sits behind nginx, which also serves the static
site (index.html) and reverse-proxies /api/* to this process.
See deploy/nginx.conf and deploy/pifagor-api.service.
"""

import hashlib
import hmac
import os
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-change-me")
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY", "")

LAVA_API_BASE = "https://gate.lava.top"
LAVA_API_KEY = os.environ.get("LAVA_API_KEY", "")
LAVA_WEBHOOK_SECRET = os.environ.get("LAVA_WEBHOOK_SECRET", "")

# One Lava.top product (offer) per pack PER LANGUAGE — separate RU/EN cards,
# each with its own cover/description/post-payment text in that language.
LAVA_OFFERS = {
    "pack3":  {"ru": os.environ.get("LAVA_OFFER_PACK3_RU", ""),  "en": os.environ.get("LAVA_OFFER_PACK3_EN", "")},
    "pack10": {"ru": os.environ.get("LAVA_OFFER_PACK10_RU", ""), "en": os.environ.get("LAVA_OFFER_PACK10_EN", "")},
    "pack15": {"ru": os.environ.get("LAVA_OFFER_PACK15_RU", ""), "en": os.environ.get("LAVA_OFFER_PACK15_EN", "")},
}

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8080")
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "app.db"))
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Packs are the source of truth for price/credits — never trust amounts from the client.
# RUB prices as agreed; USD prices are a display default for the EN UI until a real
# foreign-currency payment channel exists (see conversation notes) — YooKassa will
# still charge the RUB amount even when the UI shows the EN/$ price.
PACKS = {
    "pack3":  {"credits": 3,  "amount_rub": 399,  "amount_usd": 5.99,  "label_ru": "3 разбора",  "label_en": "3 readings"},
    "pack10": {"credits": 10, "amount_rub": 999,  "amount_usd": 11.99, "label_ru": "10 разборов", "label_en": "10 readings"},
    "pack15": {"credits": 15, "amount_rub": 1399, "amount_usd": 15.99, "label_ru": "15 разборов", "label_en": "15 readings"},
}

SESSION_COOKIE = "pf_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 365  # 1 year
TELEGRAM_AUTH_MAX_AGE = 60 * 60 * 24  # reject stale Telegram login payloads (>24h old)

serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="pf-session")

app = FastAPI(title="Pifagor Square API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def init_db():
    with get_conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                photo_url TEXT,
                credits INTEGER NOT NULL DEFAULT 0,
                free_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                telegram_id INTEGER NOT NULL,
                pack TEXT NOT NULL,
                amount_rub INTEGER NOT NULL,
                credits INTEGER NOT NULL,
                status TEXT NOT NULL,
                yk_payment_id TEXT,
                provider TEXT NOT NULL DEFAULT 'yookassa',
                external_id TEXT,
                email TEXT,
                created_at TEXT NOT NULL
            )
        """)
        # migration for DBs created before provider/external_id/email existed
        cols = {r["name"] for r in c.execute("PRAGMA table_info(payments)")}
        for col, ddl in [
            ("provider", "ALTER TABLE payments ADD COLUMN provider TEXT NOT NULL DEFAULT 'yookassa'"),
            ("external_id", "ALTER TABLE payments ADD COLUMN external_id TEXT"),
            ("email", "ALTER TABLE payments ADD COLUMN email TEXT"),
        ]:
            if col not in cols:
                c.execute(ddl)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@app.on_event("startup")
def on_startup():
    if not TELEGRAM_BOT_TOKEN:
        print("WARNING: TELEGRAM_BOT_TOKEN not set — Telegram login will fail verification.")
    if not LAVA_API_KEY:
        print("WARNING: LAVA_API_KEY not set — payments (active provider) will fail.")
    if not all(LAVA_OFFERS[pack][lang] for pack in LAVA_OFFERS for lang in ("ru", "en")):
        print("WARNING: one or more LAVA_OFFER_pack* ids are not set — create the 3 products in "
              "the Lava.top dashboard first and put their offerId here.")
    if not LAVA_WEBHOOK_SECRET:
        print("WARNING: LAVA_WEBHOOK_SECRET not set — the webhook endpoint will accept unauthenticated calls.")
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        print("NOTE: YooKassa credentials not set — that integration is dormant/unused anyway.")
    init_db()

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def make_session_cookie(telegram_id: int) -> str:
    return serializer.dumps({"tid": telegram_id})


def read_session(request: Request) -> Optional[int]:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        data = serializer.loads(raw, max_age=SESSION_MAX_AGE)
        return int(data["tid"])
    except (BadSignature, KeyError, ValueError, TypeError):
        return None


def require_user(request: Request) -> int:
    tid = read_session(request)
    if tid is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return tid

# ---------------------------------------------------------------------------
# Telegram Login Widget verification
# https://core.telegram.org/widgets/login#checking-authorization
# ---------------------------------------------------------------------------

class TelegramAuthPayload(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


def verify_telegram_payload(payload: TelegramAuthPayload) -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="server_misconfigured")

    data = payload.dict(exclude={"hash"}, exclude_none=True)
    check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, payload.hash):
        raise HTTPException(status_code=401, detail="bad_telegram_signature")

    if time.time() - payload.auth_date > TELEGRAM_AUTH_MAX_AGE:
        raise HTTPException(status_code=401, detail="telegram_auth_expired")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/auth/telegram")
def auth_telegram(payload: TelegramAuthPayload, response: Response):
    verify_telegram_payload(payload)

    with get_conn() as c:
        row = c.execute("SELECT * FROM users WHERE telegram_id = ?", (payload.id,)).fetchone()
        if row is None:
            c.execute(
                "INSERT INTO users (telegram_id, username, first_name, photo_url, credits, free_used, created_at)"
                " VALUES (?, ?, ?, ?, 0, 0, datetime('now'))",
                (payload.id, payload.username, payload.first_name, payload.photo_url),
            )
            row = c.execute("SELECT * FROM users WHERE telegram_id = ?", (payload.id,)).fetchone()
        else:
            c.execute(
                "UPDATE users SET username=?, first_name=?, photo_url=? WHERE telegram_id=?",
                (payload.username, payload.first_name, payload.photo_url, payload.id),
            )

    cookie_val = make_session_cookie(payload.id)
    response.set_cookie(
        SESSION_COOKIE, cookie_val, max_age=SESSION_MAX_AGE,
        httponly=True, secure=True, samesite="lax",
    )
    return {
        "telegram_id": row["telegram_id"],
        "username": row["username"],
        "first_name": row["first_name"],
        "credits": row["credits"],
        "free_used": bool(row["free_used"]),
    }


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    tid = require_user(request)
    with get_conn() as c:
        row = c.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    return {
        "telegram_id": row["telegram_id"],
        "username": row["username"],
        "first_name": row["first_name"],
        "credits": row["credits"],
        "free_used": bool(row["free_used"]),
    }


@app.post("/api/consume")
def consume(request: Request):
    """Spend one reading (free first, then a credit) to unlock the Графики tab
    for the calculation the user is currently viewing."""
    tid = require_user(request)
    with get_conn() as c:
        row = c.execute("SELECT * FROM users WHERE telegram_id = ?", (tid,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="user_not_found")

        if not row["free_used"]:
            c.execute("UPDATE users SET free_used = 1 WHERE telegram_id = ?", (tid,))
            return {"ok": True, "used": "free", "credits": row["credits"]}

        if row["credits"] > 0:
            c.execute("UPDATE users SET credits = credits - 1 WHERE telegram_id = ?", (tid,))
            return {"ok": True, "used": "credit", "credits": row["credits"] - 1}

    return Response(
        status_code=402,
        content='{"ok": false, "reason": "no_credits"}',
        media_type="application/json",
    )


class PayCreateRequest(BaseModel):
    pack: str
    lang: str = "ru"
    email: str

    @field_validator("email")
    @classmethod
    def email_looks_valid(cls, v):
        if not EMAIL_RE.match(v or ""):
            raise ValueError("invalid_email")
        return v


# ---------------------------------------------------------------------------
# Lava.top — active payment provider for both audiences.
#
# One "offer" (product) per pack is created once in the Lava.top dashboard
# (Integrations -> Products), and we invoice against its offerId with the
# currency/rail picked by language: RUB for ru, USD via Lava's PayPal rail
# for en. See the module docstring for the caveat about unverified field
# names — LAVA_FIELD_* below are the single place to adjust them if a real
# test call (lava_test_invoice.py) shows a different shape.
# ---------------------------------------------------------------------------

def _lava_headers():
    return {"X-Api-Key": LAVA_API_KEY, "Content-Type": "application/json"}


def create_lava_invoice(pack_key: str, pack: dict, email: str, lang: str, telegram_id: int, payment_id: str) -> dict:
    is_en = lang == "en"
    offer_id = LAVA_OFFERS.get(pack_key, {}).get("en" if is_en else "ru")
    if not offer_id:
        raise HTTPException(status_code=500, detail=f"lava_offer_not_configured: {pack_key}/{lang}")

    req_body = {
        "email": email,
        "offerId": offer_id,
        "currency": "USD" if is_en else "RUB",
        "buyerLanguage": "EN" if is_en else "RU",
        "successful_return_url": f"{FRONTEND_URL}/?payment=done",
        "failure_return_url": f"{FRONTEND_URL}/?payment=failed",
        "cancel_return_url": f"{FRONTEND_URL}/?payment=cancelled",
        # best-effort correlation id, in case it's echoed back anywhere we can see —
        # the webhook handler does NOT depend on this (see pay_lava_webhook below)
        "utm_source": payment_id,
    }
    if is_en:
        req_body["paymentProvider"] = "PAYPAL"  # international card rail; adjust after a live test if wrong

    resp = httpx.post(f"{LAVA_API_BASE}/api/v3/invoice", json=req_body, headers=_lava_headers(), timeout=15)
    if resp.status_code >= 300:
        raise HTTPException(status_code=502, detail=f"lava_error {resp.status_code}: {resp.text}")
    data = resp.json()

    # defensive parsing: try the field-name variants seen across secondary sources
    invoice_id = data.get("id") or data.get("paymentId") or data.get("invoiceId") or data.get("contractId")
    pay_url = (
        data.get("paymentUrl") or data.get("url") or data.get("link")
        or (data.get("data") or {}).get("paymentUrl")
    )
    if not invoice_id or not pay_url:
        raise HTTPException(
            status_code=502,
            detail=f"lava_unexpected_response: could not find invoice id / payment url in {data!r}",
        )
    return {"invoice_id": str(invoice_id), "pay_url": pay_url}


@app.post("/api/pay/create")
def pay_create(body: PayCreateRequest, request: Request):
    tid = require_user(request)
    pack = PACKS.get(body.pack)
    if pack is None:
        raise HTTPException(status_code=400, detail="unknown_pack")
    if not LAVA_API_KEY:
        raise HTTPException(status_code=500, detail="payments_not_configured")

    payment_id = str(uuid.uuid4())
    lava = create_lava_invoice(body.pack, pack, body.email, body.lang, tid, payment_id)

    with get_conn() as c:
        c.execute(
            "INSERT INTO payments (id, telegram_id, pack, amount_rub, credits, status, provider, external_id, email, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'pending', 'lava', ?, ?, datetime('now'))",
            (payment_id, tid, body.pack, pack["amount_rub"], pack["credits"], lava["invoice_id"], body.email),
        )

    return {"confirmation_url": lava["pay_url"]}


def _lava_invoice_status(invoice_id: str) -> Optional[str]:
    """Re-check an invoice's status directly with Lava.top using our own API key —
    never trust a webhook body alone for something that credits an account."""
    resp = httpx.get(f"{LAVA_API_BASE}/api/v1/invoices/{invoice_id}", headers=_lava_headers(), timeout=15)
    if resp.status_code >= 300:
        return None
    data = resp.json()
    status = data.get("status") or (data.get("data") or {}).get("status")
    return str(status).upper() if status else None


LAVA_SUCCESS_STATUSES = {"COMPLETED", "SUCCESS", "SUCCEEDED", "PAID"}


@app.post("/api/pay/lava/webhook")
def pay_lava_webhook(request: Request, body: dict):
    """Lava.top notification endpoint.

    We deliberately do NOT parse this payload for business logic — public
    sources disagree on its exact shape (a real integration's bugfix notes
    describe refund/chargeback events arriving in "a different shape, no
    contractId"), and getting that parsing wrong would silently drop paid
    orders. Instead any call here (whatever its shape) is treated purely as
    a "go check now" trigger: we re-verify every payment we still have
    marked pending against Lava's own API with our own credentials, and
    credit whichever ones now report success. At this account's volume,
    re-checking all pending rows on every webhook ping is cheap and correct;
    this can be tightened to match on the webhook's own id field once we've
    logged a few real payloads from production.
    """
    if LAVA_WEBHOOK_SECRET:
        auth_ok = False
        _, _, basic_pass = _parse_basic_auth(request.headers.get("authorization", ""))
        if basic_pass and hmac.compare_digest(basic_pass, LAVA_WEBHOOK_SECRET):
            auth_ok = True
        if request.headers.get("x-api-key") and hmac.compare_digest(request.headers["x-api-key"], LAVA_WEBHOOK_SECRET):
            auth_ok = True
        if not auth_ok:
            raise HTTPException(status_code=401, detail="bad_webhook_auth")

    checked = credited = 0
    with get_conn() as c:
        pending = c.execute(
            "SELECT * FROM payments WHERE provider = 'lava' AND status = 'pending'"
        ).fetchall()
        for row in pending:
            checked += 1
            status = _lava_invoice_status(row["external_id"])
            if status not in LAVA_SUCCESS_STATUSES:
                continue
            c.execute(
                "UPDATE users SET credits = credits + ? WHERE telegram_id = ?",
                (row["credits"], row["telegram_id"]),
            )
            c.execute("UPDATE payments SET status = 'succeeded' WHERE id = ?", (row["id"],))
            credited += 1

    return {"ok": True, "checked": checked, "credited": credited}


def _parse_basic_auth(header_value: str):
    """Returns (ok, user, password) from an 'Authorization: Basic ...' header, or (False, None, None)."""
    import base64
    if not header_value.startswith("Basic "):
        return False, None, None
    try:
        decoded = base64.b64decode(header_value[6:]).decode("utf-8")
        user, _, password = decoded.partition(":")
        return True, user, password
    except Exception:
        return False, None, None


# ---------------------------------------------------------------------------
# YooKassa — dormant. Kept working and tested in case it's needed again;
# not called by the frontend (see /api/pay/create above, which uses Lava.top).
# ---------------------------------------------------------------------------

@app.post("/api/pay/yookassa/create")
def pay_create_yookassa(body: PayCreateRequest, request: Request):
    tid = require_user(request)
    pack = PACKS.get(body.pack)
    if pack is None:
        raise HTTPException(status_code=400, detail="unknown_pack")
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        raise HTTPException(status_code=500, detail="payments_not_configured")

    payment_id = str(uuid.uuid4())
    label = pack["label_en"] if body.lang == "en" else pack["label_ru"]

    yk_request = {
        "amount": {"value": f"{pack['amount_rub']:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": f"{FRONTEND_URL}/?payment=done"},
        "capture": True,
        "description": f"Квадрат Пифагора — {label}",
        "metadata": {"telegram_id": tid, "pack": body.pack, "internal_id": payment_id},
    }

    resp = httpx.post(
        "https://api.yookassa.ru/v3/payments",
        json=yk_request,
        auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY),
        headers={"Idempotence-Key": payment_id},
        timeout=15,
    )
    if resp.status_code >= 300:
        raise HTTPException(status_code=502, detail=f"yookassa_error: {resp.text}")
    yk_data = resp.json()

    with get_conn() as c:
        c.execute(
            "INSERT INTO payments (id, telegram_id, pack, amount_rub, credits, status, yk_payment_id, provider, email, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'pending', ?, 'yookassa', ?, datetime('now'))",
            (payment_id, tid, body.pack, pack["amount_rub"], pack["credits"], yk_data["id"], body.email),
        )

    return {"confirmation_url": yk_data["confirmation"]["confirmation_url"]}


@app.post("/api/pay/yookassa/webhook")
def pay_webhook_yookassa(body: dict):
    """YooKassa notification endpoint. Per YooKassa's own recommendation we don't
    trust the webhook body for the payment status — we re-fetch the payment from
    YooKassa's API using our own credentials before crediting anyone."""
    yk_payment_id = (body.get("object") or {}).get("id")
    if not yk_payment_id:
        raise HTTPException(status_code=400, detail="bad_webhook_body")

    resp = httpx.get(
        f"https://api.yookassa.ru/v3/payments/{yk_payment_id}",
        auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY),
        timeout=15,
    )
    if resp.status_code >= 300:
        raise HTTPException(status_code=502, detail="yookassa_verify_failed")
    yk_data = resp.json()

    if yk_data.get("status") != "succeeded":
        return {"ok": True, "ignored": True}

    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM payments WHERE yk_payment_id = ?", (yk_payment_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="payment_not_found")
        if row["status"] == "succeeded":
            return {"ok": True, "already_processed": True}

        c.execute(
            "UPDATE users SET credits = credits + ? WHERE telegram_id = ?",
            (row["credits"], row["telegram_id"]),
        )
        c.execute("UPDATE payments SET status = 'succeeded' WHERE id = ?", (row["id"],))

    return {"ok": True}


@app.get("/api/packs")
def get_packs(lang: str = "ru"):
    out = {}
    for key, p in PACKS.items():
        out[key] = {
            "credits": p["credits"],
            "amount": p["amount_usd"] if lang == "en" else p["amount_rub"],
            "currency": "USD" if lang == "en" else "RUB",
            "label": p["label_en"] if lang == "en" else p["label_ru"],
        }
    return out


@app.get("/api/health")
def health():
    return {"ok": True}
