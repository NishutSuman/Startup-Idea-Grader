"""FastAPI server: /health, /expand, /evaluate, /history. CORS + rate limiting."""
import os
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import config
config.load_env()  # load backend/.env (keys, ALLOWED_ORIGIN) before anything reads env

import db
import pipeline

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Founder Idea AI Evaluator")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def _rate_limited(request: Request, exc):
    return JSONResponse(status_code=429, content={"error": "Rate limit reached — try again shortly."})


_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGIN", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # Always allow any localhost/127.0.0.1 port in dev, so CORS never blocks local testing.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init()


class ExpandReq(BaseModel):
    idea: str
    provider: str = "gemini"
    api_key: Optional[str] = None


class EvalReq(BaseModel):
    mode: str = "structured"          # 'structured' | 'quick'
    inputs: dict                      # the pitch fields
    provider: str = "gemini"          # 'gemini' | 'openai' | 'anthropic'
    api_key: Optional[str] = None     # bring-your-own; else server env key
    grounding: str = "reasoned"       # 'reasoned' | 'live'


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/expand")
@limiter.limit("20/hour")
def expand(req: ExpandReq, request: Request):
    try:
        data = pipeline.expand_idea(req.idea, req.provider, req.api_key)
        return {"fields": data.get("fields", [])}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.post("/evaluate")
@limiter.limit("10/hour")
def evaluate(req: EvalReq, request: Request):
    try:
        result = pipeline.evaluate(req.inputs, req.provider, req.api_key, req.grounding)
        db.save(req.mode, req.provider, req.grounding, req.inputs, result)
        return result
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.get("/history")
def history():
    return {"items": db.recent()}


@app.get("/history/{eid}")
def history_item(eid: int):
    rec = db.get(eid)
    if not rec:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return rec
