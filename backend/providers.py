"""
One interface, three providers. Each returns the model's raw text (expected JSON).

Key resolution: use the key passed in the request (bring-your-own), else fall back
to the server env key for that provider. The office key therefore only works where
it is set in the environment (locally), never shipped to the browser.
"""
import os
import json
import re
import time
import requests

# Free Gemini models are individually flaky (429 quota / 503 overload). Try several.
GEMINI_CANDIDATES = ["gemini-2.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]
_GEMINI_RETRYABLE = ("503", "UNAVAILABLE", "overload", "429", "RESOURCE_EXHAUSTED", "quota", "404", "NOT_FOUND")

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash-lite",
}

ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

TIMEOUT = 60


def resolve_key(provider, byo_key):
    key = (byo_key or "").strip() or os.environ.get(ENV_KEYS.get(provider, ""), "").strip()
    if not key:
        raise ValueError(f"No API key for {provider}. Paste your own key, or set {ENV_KEYS[provider]} on the server.")
    return key


def complete(provider, byo_key, system, user, model=None, max_tokens=1500):
    key = resolve_key(provider, byo_key)
    model = model or DEFAULT_MODELS[provider]
    if provider == "anthropic":
        return _anthropic(key, model, system, user, max_tokens)
    if provider == "openai":
        return _openai(key, model, system, user, max_tokens)
    if provider == "gemini":
        return _gemini(key, model, system, user, max_tokens)
    raise ValueError(f"Unknown provider: {provider}")


def _anthropic(key, model, system, user, max_tokens):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "system": system,
              "messages": [{"role": "user", "content": user}]},
        timeout=TIMEOUT,
    )
    _check(r, "Anthropic")
    return r.json()["content"][0]["text"]


def _openai(key, model, system, user, max_tokens):
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "temperature": 0.4,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        timeout=TIMEOUT,
    )
    _check(r, "OpenAI")
    return r.json()["choices"][0]["message"]["content"]


def _gemini(key, model, system, user, max_tokens):
    """Try the chosen model, then fall back across other free models on overload/quota."""
    candidates = [model] + [m for m in GEMINI_CANDIDATES if m != model]
    last = None
    for m in candidates:
        try:
            return _gemini_once(key, m, system, user, max_tokens)
        except RuntimeError as e:
            last = e
            if any(x in str(e) for x in _GEMINI_RETRYABLE):
                time.sleep(1)
                continue
            raise
    raise last


def _gemini_once(key, model, system, user, max_tokens):
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        headers={"Content-Type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": system}]},
              "contents": [{"role": "user", "parts": [{"text": user}]}],
              "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json",
                                   "maxOutputTokens": max_tokens,
                                   # Gemini 2.5/3.x "think" by default and eat the output budget,
                                   # truncating the JSON. Disable it for reliable, cheaper output.
                                   "thinkingConfig": {"thinkingBudget": 0}}},
        timeout=TIMEOUT,
    )
    _check(r, "Gemini")
    data = r.json()
    cands = data.get("candidates", [])
    if not cands:
        raise RuntimeError(f"Gemini returned no candidates: {str(data)[:200]}")
    parts = cands[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    if not text.strip():
        raise RuntimeError(f"Gemini empty output (finishReason={cands[0].get('finishReason')})")
    return text


def _check(r, name):
    if not r.ok:
        raise RuntimeError(f"{name} {r.status_code}: {r.text[:300]}")


def parse_json(raw):
    """Models with JSON mode return clean JSON; salvage fences/prose otherwise."""
    s = (raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", s)
        if m:
            return json.loads(m.group(0))
        raise ValueError("Model did not return valid JSON.")
