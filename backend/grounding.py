"""
Optional 'live market data' grounding. Uses Tavily (free tier, built for LLM
grounding) if TAVILY_API_KEY is set; otherwise returns None and the pipeline
falls back to reasoned estimates. Kept isolated so it can never break grading.
"""
import os
import requests


def search(query, max_results=5):
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": key,
                "query": f"market size, key competitors, and target demographics for: {query}",
                "max_results": max_results,
                "search_depth": "basic",
            },
            timeout=30,
        )
        if not r.ok:
            return None
        results = r.json().get("results", [])
        lines = [f"- {x.get('title','')}: {x.get('content','')[:280]} (source: {x.get('url','')})"
                 for x in results]
        return "\n".join(lines) if lines else None
    except Exception:
        return None  # grounding must never crash the evaluation
