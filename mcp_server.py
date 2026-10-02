"""
Telegram Connector — MCP Server
Exposes the Railway connector as Claude tools.

Configure in ~/.claude/settings.json:
  "mcpServers": {
    "telegram-connector": {
      "command": "C:/Users/29abh/Projects/Trading/.venv/Scripts/python",
      "args":    ["C:/Users/29abh/Projects/Trading/telegram_connector/mcp_server.py"],
      "env": {
        "TELEGRAM_CONNECTOR_URL": "<railway url>",
        "TELEGRAM_BOT_TOKEN":     "<your token>",
        "TELEGRAM_CHAT_ID":       "<your chat id>"
      }
    }
  }

bot_token and chat_id fall back to env vars when not supplied by the caller.
"""

import os
import requests
from mcp.server.fastmcp import FastMCP

CONNECTOR       = os.environ.get("TELEGRAM_CONNECTOR_URL", "https://telegramconnector-production.up.railway.app")
DEFAULT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DEFAULT_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0") or "0")

mcp = FastMCP("telegram-connector")


def _tok(bot_token: str | None) -> str:
    return bot_token or DEFAULT_TOKEN


def _cid(chat_id: int | None) -> int:
    return chat_id or DEFAULT_CHAT_ID


@mcp.tool()
def send_message(
    text: str,
    parse_mode: str = "HTML",
    bot_token: str | None = None,
    chat_id: int | None = None,
) -> dict:
    """Send a plain text or HTML-formatted message to a Telegram chat."""
    r = requests.post(f"{CONNECTOR}/send", json={
        "bot_token": _tok(bot_token), "chat_id": _cid(chat_id),
        "text": text, "parse_mode": parse_mode,
    }, timeout=20)
    return r.json()


@mcp.tool()
def send_trade_alert(
    symbol: str,
    signal: str,
    entry: float,
    target: float,
    stop_loss: float,
    setup: str,
    oi_change_pct: float | None = None,
    atm_iv: float | None = None,
    fii_flow: str | None = None,
    bot_token: str | None = None,
    chat_id: int | None = None,
) -> dict:
    """Send a formatted swing trade alert to a Telegram chat."""
    r = requests.post(f"{CONNECTOR}/send/trade-alert", json={
        "bot_token": _tok(bot_token), "chat_id": _cid(chat_id),
        "symbol": symbol, "signal": signal,
        "entry": entry, "target": target, "stop_loss": stop_loss,
        "setup": setup, "oi_change_pct": oi_change_pct,
        "atm_iv": atm_iv, "fii_flow": fii_flow,
    }, timeout=20)
    return r.json()


@mcp.tool()
def send_error_alert(
    component: str,
    error: str,
    bot_token: str | None = None,
    chat_id: int | None = None,
) -> dict:
    """Send a silent pipeline error alert to a Telegram chat."""
    r = requests.post(f"{CONNECTOR}/send/error-alert", json={
        "bot_token": _tok(bot_token), "chat_id": _cid(chat_id),
        "component": component, "error": error,
    }, timeout=20)
    return r.json()


@mcp.tool()
def verify_bot(bot_token: str | None = None) -> dict:
    """Verify a Telegram bot token is valid. Returns bot info."""
    r = requests.post(f"{CONNECTOR}/verify", json={
        "bot_token": _tok(bot_token),
    }, timeout=10)
    return r.json()


if __name__ == "__main__":
    mcp.run(transport="stdio")