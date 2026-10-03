"""
Telegram Connector — FastAPI service + MCP streamable HTTP server

HTTP REST endpoints  : /send, /send/trade-alert, /send/daily-summary,
                       /send/error-alert, /verify
MCP streamable HTTP  : /mcp       ← cloud agents connect here

Run locally:
    uvicorn app:app --host 0.0.0.0 --port 8181
"""

import os
from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import Response

import notifier

# ── MCP server ───────────────────────────────────────────────────────────────

mcp = FastMCP("telegram-connector")

# ── FastAPI app with lifespan to initialize MCP task group ──────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with anyio.create_task_group() as tg:
        mcp.session_manager._task_group = tg
        yield

app = FastAPI(title="Telegram Connector", lifespan=lifespan)

# Optional API key guard for /mcp — set MCP_API_KEY env var to enable.
# Uses a raw ASGI wrapper (not BaseHTTPMiddleware) to avoid breaking streaming.
_MCP_API_KEY = os.environ.get("MCP_API_KEY", "")

class _BearerGuard:
    def __init__(self, inner: ASGIApp):
        self.inner = inner

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http" and _MCP_API_KEY:
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {_MCP_API_KEY}":
                res = Response("Unauthorized", status_code=401)
                await res(scope, receive, send)
                return
        await self.inner(scope, receive, send)

def _check(bot_token: str | None, chat_id: int | None) -> dict | None:
    missing = []
    if not bot_token:
        missing.append("bot_token")
    if not chat_id:
        missing.append("chat_id")
    if missing:
        return {"error": f"Missing required field(s): {', '.join(missing)}"}
    return None


@mcp.tool()
def send_message(
    bot_token: str,
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
) -> dict:
    """Send a plain text or HTML-formatted message to a Telegram chat."""
    err = _check(bot_token, chat_id)
    if err:
        return err
    try:
        return {"message_id": notifier.send_message(bot_token, chat_id, text, parse_mode=parse_mode)}
    except (ConnectionError, ValueError) as e:
        return {"error": str(e)}


@mcp.tool()
def send_trade_alert(
    bot_token: str,
    chat_id: int,
    symbol: str, signal: str,
    entry: float, target: float, stop_loss: float, setup: str,
    oi_change_pct: float | None = None,
    atm_iv: float | None = None,
    fii_flow: str | None = None,
) -> dict:
    """Send a formatted swing trade alert (LONG/SHORT) to a Telegram chat."""
    err = _check(bot_token, chat_id)
    if err:
        return err
    text = notifier.format_trade_alert(
        symbol=symbol, signal=signal, entry=entry, target=target,
        stop_loss=stop_loss, setup=setup, oi_change_pct=oi_change_pct,
        atm_iv=atm_iv, fii_flow=fii_flow,
    )
    try:
        return {"message_id": notifier.send_message(bot_token, chat_id, text)}
    except (ConnectionError, ValueError) as e:
        return {"error": str(e)}


@mcp.tool()
def send_error_alert(
    bot_token: str,
    chat_id: int,
    component: str,
    error: str,
) -> dict:
    """Send a silent pipeline error alert to a Telegram chat."""
    err = _check(bot_token, chat_id)
    if err:
        return err
    text = notifier.format_error_alert(component, error)
    try:
        return {"message_id": notifier.send_message(bot_token, chat_id, text, disable_notification=True)}
    except (ConnectionError, ValueError) as e:
        return {"error": str(e)}


@mcp.tool()
def verify_bot(bot_token: str) -> dict:
    """Verify a Telegram bot token is valid. Returns bot info."""
    if not bot_token:
        return {"error": "Missing required field: bot_token"}
    try:
        return notifier.verify_bot(bot_token)
    except ValueError as e:
        return {"error": str(e)}


# Mount MCP streamable HTTP at /mcp  →  agents connect to /mcp/mcp
app.mount("/mcp", _BearerGuard(mcp.streamable_http_app()))


# ── HTTP REST endpoints ─────────────────────────────────────────────────────

class Credentials(BaseModel):
    bot_token: str
    chat_id:   int


class SendRequest(Credentials):
    text:                 str
    parse_mode:           str  = "HTML"
    disable_notification: bool = False


class SendResponse(BaseModel):
    message_id: int


@app.post("/send", response_model=SendResponse)
def http_send(req: SendRequest):
    try:
        mid = notifier.send_message(
            req.bot_token, req.chat_id, req.text,
            parse_mode=req.parse_mode,
            disable_notification=req.disable_notification,
        )
    except (ConnectionError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"message_id": mid}


class TradeAlertRequest(Credentials):
    symbol:        str
    signal:        str
    entry:         float
    target:        float
    stop_loss:     float
    setup:         str
    oi_change_pct: float | None = None
    atm_iv:        float | None = None
    fii_flow:      str   | None = None


@app.post("/send/trade-alert", response_model=SendResponse)
def http_send_trade_alert(req: TradeAlertRequest):
    text = notifier.format_trade_alert(
        symbol=req.symbol, signal=req.signal, entry=req.entry,
        target=req.target, stop_loss=req.stop_loss, setup=req.setup,
        oi_change_pct=req.oi_change_pct, atm_iv=req.atm_iv, fii_flow=req.fii_flow,
    )
    try:
        mid = notifier.send_message(req.bot_token, req.chat_id, text)
    except (ConnectionError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"message_id": mid}


class SignalEntry(BaseModel):
    symbol:    str
    signal:    str
    entry:     float
    target:    float
    stop_loss: float


class DailySummaryRequest(Credentials):
    date_str:         str
    signals:          list[SignalEntry] = Field(default_factory=list)
    vix:              float | None = None
    fii_net:          float | None = None
    dii_net:          float | None = None
    nifty_change_pct: float | None = None


@app.post("/send/daily-summary", response_model=SendResponse)
def http_send_daily_summary(req: DailySummaryRequest):
    text = notifier.format_daily_summary(
        date_str=req.date_str, signals=[s.model_dump() for s in req.signals],
        vix=req.vix, fii_net=req.fii_net, dii_net=req.dii_net,
        nifty_change_pct=req.nifty_change_pct,
    )
    try:
        mid = notifier.send_message(req.bot_token, req.chat_id, text)
    except (ConnectionError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"message_id": mid}


class ErrorAlertRequest(Credentials):
    component: str
    error:     str


@app.post("/send/error-alert", response_model=SendResponse)
def http_send_error_alert(req: ErrorAlertRequest):
    text = notifier.format_error_alert(req.component, req.error)
    try:
        mid = notifier.send_message(req.bot_token, req.chat_id, text, disable_notification=True)
    except (ConnectionError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"message_id": mid}


class VerifyRequest(BaseModel):
    bot_token: str


@app.post("/verify")
def http_verify(req: VerifyRequest):
    try:
        return notifier.verify_bot(req.bot_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))