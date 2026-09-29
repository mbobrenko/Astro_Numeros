"""One-off script: creates a single real test invoice against the live
Lava.top API and prints the raw response, so we can confirm the exact
field names main.py's create_lava_invoice() expects (id/paymentUrl etc.)
before relying on them in production. Public docs for gate.lava.top
returned 403s while this integration was written, so those field names
were reconstructed from secondary sources and need this one live check.

Usage:
    export LAVA_API_KEY=...
    export LAVA_TEST_OFFER_ID=...   # any one real offerId from your dashboard
    python3 lava_test_invoice.py you@example.com

This does NOT charge anything by itself — it only creates an invoice
(a payment page/link); nothing is charged unless someone completes
checkout on that page.
"""
import json
import os
import sys

import httpx

api_key = os.environ.get("LAVA_API_KEY")
offer_id = os.environ.get("LAVA_TEST_OFFER_ID")
email = sys.argv[1] if len(sys.argv) > 1 else None

if not api_key or not offer_id or not email:
    print(__doc__)
    sys.exit(1)

body = {
    "email": email,
    "offerId": offer_id,
    "currency": "RUB",
    "buyerLanguage": "RU",
}

resp = httpx.post(
    "https://gate.lava.top/api/v3/invoice",
    json=body,
    headers={"X-Api-Key": api_key, "Content-Type": "application/json"},
    timeout=15,
)
print("HTTP status:", resp.status_code)
print("Raw response body:")
try:
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
except Exception:
    print(resp.text)

print(
    "\nCompare the field names above against create_lava_invoice() in main.py "
    "(it currently looks for id/paymentId/invoiceId/contractId and "
    "paymentUrl/url/link) and adjust there if they differ."
)
