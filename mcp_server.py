"""
Telegram Connector — MCP Server
Exposes the Railway connector as Claude tools.

Register in Claude settings:
  command : python
  args    : ["C:/Users/29abh/Projects/Trading/telegram_connector/mcp_server.py"]
"""

import requests
from mcp.server.fastmcp import FastMCP

CONNECTOR = "https://telegramconnector-production.up.railway.app"

mcp = FastMCP("telegram-connector")


@mcp.tool()
def send_message(bot_token: str, chat_id: int, text: str, parse_mode: str = "HTML") -> dict:
    """Send a plain text (or HTML-formatted) message to a Telegram chat."""
    r = requests.post(f"{CONNECTOR}/send", json={
        "bot_token": bot_token, "chat_id": chat_id,
        "text": text, "parse_mode": parse_mode,
    }, timeout=20)
    return r.json()


@mcp.tool()
def send_trade_alert(
    bot_token: str, chat_id: int,
    symbol: str, signal: str,
    entry: float, target: float, stop_loss: float,
    setup: str,
    oi_change_pct: float = None, atm_iv: float = None, fii_flow: str = None,
) -> dict:
    """Send a formatted swing trade alert to a Telegram chat."""
    r = requests.post(f"{CONNECTOR}/send/trade-alert", json={
        "bot_token": bot_token, "chat_id": chat_id,
        "symbol": symbol, "signal": signal,
        "entry": entry, "target": target, "stop_loss": stop_loss,
        "setup": setup, "oi_change_pct": oi_change_pct,
        "atm_iv": atm_iv, "fii_flow": fii_flow,
    }, timeout=20)
    return r.json()


@mcp.tool()
def send_error_alert(bot_token: str, chat_id: int, component: str, error: str) -> dict:
    """Send a silent pipeline error alert to a Telegram chat."""
    r = requests.post(f"{CONNECTOR}/send/error-alert", json={
        "bot_token": bot_token, "chat_id": chat_id,
        "component": component, "error": error,
    }, timeout=20)
    return r.json()


@mcp.tool()
def verify_bot(bot_token: str) -> dict:
    """Verify a Telegram bot token is valid. Returns bot info."""
    r = requests.post(f"{CONNECTOR}/verify", json={"bot_token": bot_token}, timeout=10)
    return r.json()


if __name__ == "__main__":
    mcp.run(transport="stdio")