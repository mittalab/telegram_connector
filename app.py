"""
Telegram Connector — FastAPI service
Every request supplies its own bot_token and chat_id.

Run:
    uvicorn app:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import notifier

app = FastAPI(title="Telegram Connector")


# ── Shared credential fields (mixed into every request body) ────────────────

class Credentials(BaseModel):
    bot_token: str
    chat_id:   int


# ── /send — raw text ────────────────────────────────────────────────────────

class SendRequest(Credentials):
    text:                 str
    parse_mode:           str  = "HTML"
    disable_notification: bool = False


class SendResponse(BaseModel):
    message_id: int


@app.post("/send", response_model=SendResponse)
def send(req: SendRequest):
    try:
        mid = notifier.send_message(
            req.bot_token, req.chat_id, req.text,
            parse_mode=req.parse_mode,
            disable_notification=req.disable_notification,
        )
    except (ConnectionError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"message_id": mid}


# ── /send/trade-alert ───────────────────────────────────────────────────────

class TradeAlertRequest(Credentials):
    symbol:        str
    signal:        str           # "LONG" or "SHORT"
    entry:         float
    target:        float
    stop_loss:     float
    setup:         str
    oi_change_pct: float | None = None
    atm_iv:        float | None = None
    fii_flow:      str   | None = None


@app.post("/send/trade-alert", response_model=SendResponse)
def send_trade_alert(req: TradeAlertRequest):
    text = notifier.format_trade_alert(
        symbol        = req.symbol,
        signal        = req.signal,
        entry         = req.entry,
        target        = req.target,
        stop_loss     = req.stop_loss,
        setup         = req.setup,
        oi_change_pct = req.oi_change_pct,
        atm_iv        = req.atm_iv,
        fii_flow      = req.fii_flow,
    )
    try:
        mid = notifier.send_message(req.bot_token, req.chat_id, text)
    except (ConnectionError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"message_id": mid}


# ── /send/daily-summary ─────────────────────────────────────────────────────

class SignalEntry(BaseModel):
    symbol:    str
    signal:    str
    entry:     float
    target:    float
    stop_loss: float


class DailySummaryRequest(Credentials):
    date_str:          str
    signals:           list[SignalEntry] = Field(default_factory=list)
    vix:               float | None = None
    fii_net:           float | None = None
    dii_net:           float | None = None
    nifty_change_pct:  float | None = None


@app.post("/send/daily-summary", response_model=SendResponse)
def send_daily_summary(req: DailySummaryRequest):
    text = notifier.format_daily_summary(
        date_str         = req.date_str,
        signals          = [s.model_dump() for s in req.signals],
        vix              = req.vix,
        fii_net          = req.fii_net,
        dii_net          = req.dii_net,
        nifty_change_pct = req.nifty_change_pct,
    )
    try:
        mid = notifier.send_message(req.bot_token, req.chat_id, text)
    except (ConnectionError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"message_id": mid}


# ── /send/error-alert ───────────────────────────────────────────────────────

class ErrorAlertRequest(Credentials):
    component: str
    error:     str


@app.post("/send/error-alert", response_model=SendResponse)
def send_error_alert(req: ErrorAlertRequest):
    text = notifier.format_error_alert(req.component, req.error)
    try:
        mid = notifier.send_message(req.bot_token, req.chat_id, text, disable_notification=True)
    except (ConnectionError, ValueError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"message_id": mid}


# ── /verify ─────────────────────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    bot_token: str


@app.post("/verify")
def verify(req: VerifyRequest):
    try:
        return notifier.verify_bot(req.bot_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))