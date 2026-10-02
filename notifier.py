"""
Core Telegram send functions — stateless, no globals.
All functions take bot_token and chat_id explicitly.
"""

import time
from datetime import datetime

import requests


def _base_url(bot_token: str) -> str:
    return f"https://api.telegram.org/bot{bot_token}"


def send_message(
    bot_token: str,
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    disable_notification: bool = False,
) -> int:
    """Send a message. Returns message_id.
    Raises ConnectionError on network failure, ValueError if Telegram rejects it."""
    payload = {
        "chat_id":              chat_id,
        "text":                 text,
        "parse_mode":           parse_mode,
        "disable_notification": disable_notification,
    }
    try:
        r = requests.post(f"{_base_url(bot_token)}/sendMessage", json=payload, timeout=15)
    except requests.RequestException as e:
        raise ConnectionError(f"Network error: {e}") from e

    result = r.json()
    if not result.get("ok"):
        raise ValueError(f"Telegram error: {result.get('description', result)}")
    return result["result"]["message_id"]


def verify_bot(bot_token: str) -> dict:
    """Confirm token is valid. Returns bot info dict or raises ValueError."""
    r = requests.get(f"{_base_url(bot_token)}/getMe", timeout=10)
    result = r.json()
    if not result.get("ok"):
        raise ValueError(f"Invalid bot token: {result.get('description', result)}")
    return result["result"]


def discover_chat_id(bot_token: str) -> int | None:
    """Return chat ID from the most recent message sent to the bot."""
    r = requests.get(f"{_base_url(bot_token)}/getUpdates", timeout=10)
    data = r.json()
    if not data.get("ok"):
        return None
    updates = data.get("result", [])
    if not updates:
        return None
    msg = updates[-1].get("message") or updates[-1].get("channel_post") or {}
    return msg.get("chat", {}).get("id")


# ── Formatters (no credentials needed) ─────────────────────────────────────

def format_trade_alert(
    symbol: str,
    signal: str,
    entry: float,
    target: float,
    stop_loss: float,
    setup: str,
    oi_change_pct: float | None = None,
    atm_iv: float | None = None,
    fii_flow: str | None = None,
) -> str:
    now    = datetime.now().strftime("%d-%b-%Y %H:%M")
    rr     = abs(target - entry) / abs(entry - stop_loss) if entry != stop_loss else 0
    pct_t  = (target - entry) / entry * 100
    pct_sl = (stop_loss - entry) / entry * 100
    label  = "BUY" if signal == "LONG" else "SELL"

    lines = [
        f"<b>SWING TRADE ALERT — {label}</b>",
        f"<code>{now} IST</code>",
        "",
        f"<b>{symbol}</b>  |  NSE",
        f"Signal    : <b>{signal}</b>",
        f"Entry     : <code>{entry:,.2f}</code>",
        f"Target    : <code>{target:,.2f}</code>  ({pct_t:+.1f}%)",
        f"Stop Loss : <code>{stop_loss:,.2f}</code>  ({pct_sl:+.1f}%)",
        f"R:R       : <code>1 : {rr:.1f}</code>",
        "",
        f"Setup     : {setup}",
    ]
    if oi_change_pct is not None:
        direction = "buildup" if oi_change_pct > 0 else "unwinding"
        lines.append(f"OI        : {oi_change_pct:+.1f}% ({direction})")
    if atm_iv is not None:
        lines.append(f"ATM IV    : {atm_iv:.1f}%")
    if fii_flow:
        lines.append(f"FII Flow  : <i>{fii_flow}</i>")
    return "\n".join(lines)


def format_daily_summary(
    date_str: str,
    signals: list[dict],
    vix: float | None = None,
    fii_net: float | None = None,
    dii_net: float | None = None,
    nifty_change_pct: float | None = None,
) -> str:
    lines = [f"<b>POST-MARKET SUMMARY</b>", f"<code>{date_str}</code>", ""]
    if nifty_change_pct is not None:
        lines.append(f"NIFTY   : {nifty_change_pct:+.2f}%")
    if vix is not None:
        lines.append(f"VIX     : {vix:.2f}")
    if fii_net is not None:
        lines.append(f"FII     : {fii_net:+,.0f} Cr")
    if dii_net is not None:
        lines.append(f"DII     : {dii_net:+,.0f} Cr")
    lines.append("")
    if signals:
        lines.append(f"<b>Signals ({len(signals)})</b>")
        for s in signals:
            lines.append(
                f"  <code>{s['symbol']:<12}</code> {s['signal']}  "
                f"E:{s['entry']:.0f}  T:{s['target']:.0f}  SL:{s['stop_loss']:.0f}"
            )
    else:
        lines.append("<i>No signals today.</i>")
    return "\n".join(lines)


def format_error_alert(component: str, error: str) -> str:
    now = datetime.now().strftime("%d-%b-%Y %H:%M")
    return (
        f"<b>PIPELINE ERROR</b>\n"
        f"<code>{now} IST</code>\n\n"
        f"Component : {component}\n"
        f"Error     : <code>{error[:300]}</code>"
    )


def send_trade_alerts(bot_token: str, chat_id: int, alerts: list[dict]) -> list[int]:
    """Send multiple alerts, respecting Telegram's 1 msg/sec limit per chat."""
    message_ids = []
    for alert in alerts:
        mid = send_message(bot_token, chat_id, format_trade_alert(**alert))
        message_ids.append(mid)
        time.sleep(1.1)
    return message_ids