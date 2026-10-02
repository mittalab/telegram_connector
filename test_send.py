"""
Manual smoke test — hits the running connector service on localhost:8000.
Run:  python test_send.py
Requires: uvicorn app:app running in another terminal.
"""

import requests

BASE_URL  = "http://localhost:8181"
BOT_TOKEN = "8819449715:AAErfcO08JiVHzfiMBF7l_H63YJwtPDWDsI"
CHAT_ID   = 6888091818


def post(path: str, payload: dict) -> dict:
    r = requests.post(f"{BASE_URL}{path}", json=payload, timeout=20)
    return r.status_code, r.json()


def run():
    results = []

    # ── 1. Verify token ─────────────────────────────────────────────────────
    print("[1] POST /verify")
    code, body = post("/verify", {"bot_token": BOT_TOKEN})
    ok = code == 200
    print(f"    {code}  {body}")
    results.append(("verify", ok))

    # ── 2. Raw text ──────────────────────────────────────────────────────────
    print("\n[2] POST /send  (plain text)")
    code, body = post("/send", {
        "bot_token": BOT_TOKEN,
        "chat_id":   CHAT_ID,
        "text":      "connector smoke test — plain text delivery working.",
    })
    ok = code == 200
    print(f"    {code}  {body}")
    results.append(("send plain", ok))

    # ── 3. Trade alert ───────────────────────────────────────────────────────
    print("\n[3] POST /send/trade-alert")
    code, body = post("/send/trade-alert", {
        "bot_token":    BOT_TOKEN,
        "chat_id":      CHAT_ID,
        "symbol":       "RELIANCE",
        "signal":       "LONG",
        "entry":        1354.50,
        "target":       1410.00,
        "stop_loss":    1325.00,
        "setup":        "Breakout above 52-week high on volume surge",
        "oi_change_pct": 8.3,
        "atm_iv":       22.4,
        "fii_flow":     "Buying (+₹2,100 Cr)",
    })
    ok = code == 200
    print(f"    {code}  {body}")
    results.append(("trade alert", ok))

    # ── 4. Daily summary ─────────────────────────────────────────────────────
    print("\n[4] POST /send/daily-summary")
    code, body = post("/send/daily-summary", {
        "bot_token": BOT_TOKEN,
        "chat_id":   CHAT_ID,
        "date_str":  "02-Oct-2026",
        "signals": [
            {"symbol": "RELIANCE",   "signal": "LONG",  "entry": 1354, "target": 1410, "stop_loss": 1325},
            {"symbol": "HDFCBANK",   "signal": "LONG",  "entry": 1912, "target": 1980, "stop_loss": 1875},
            {"symbol": "TATAMOTORS", "signal": "SHORT", "entry": 942,  "target": 905,  "stop_loss": 965},
        ],
        "vix":              13.45,
        "fii_net":          -4439.76,
        "dii_net":           6002.90,
        "nifty_change_pct":  0.48,
    })
    ok = code == 200
    print(f"    {code}  {body}")
    results.append(("daily summary", ok))

    # ── 5. Error alert (silent) ──────────────────────────────────────────────
    print("\n[5] POST /send/error-alert")
    code, body = post("/send/error-alert", {
        "bot_token": BOT_TOKEN,
        "chat_id":   CHAT_ID,
        "component": "test_send.py",
        "error":     "This is a test error alert — not a real failure.",
    })
    ok = code == 200
    print(f"    {code}  {body}")
    results.append(("error alert", ok))

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    all_ok = all(ok for _, ok in results)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print("=" * 50)
    print("RESULT:", "PASS" if all_ok else "FAIL")


if __name__ == "__main__":
    run()