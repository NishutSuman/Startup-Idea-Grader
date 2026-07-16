"""
Orchestrates the staged evaluation:
  intake -> (optional grounding) -> 5 stage prompts in parallel -> weighted score in code -> synthesis verdict.
"""
import os
import time
import concurrent.futures as cf

# Free tiers rate-limit hard, so keep concurrency low by default. Paid keys can raise it.
MAX_WORKERS = int(os.environ.get("PIPELINE_WORKERS", "2"))

from rubric import (STAGES, stage_system_prompt, synthesis_system_prompt,
                    expand_system_prompt, grade_for)
from providers import complete, parse_json
import grounding

_POINTS = {a["key"]: a["points"] for s in STAGES for a in s["atoms"]}
_STAGE_POINTS = {s["key"]: sum(a["points"] for a in s["atoms"]) for s in STAGES}


def _retry(fn, tries=2):
    # _gemini already falls back across models internally, so keep the outer retry light.
    last = None
    for i in range(tries):
        try:
            return fn()
        except RuntimeError as e:  # transient provider errors (429/503/overload)
            last = e
            if any(x in str(e).lower() for x in ("429", "503", "overload", "quota", "rate")):
                time.sleep(1.5 * (i + 1))
                continue
            raise
    raise last


def brief_text(inputs):
    parts = [f"{k.replace('_', ' ').title()}: {v}" for k, v in inputs.items() if v]
    return "\n".join(parts) if parts else "(no details provided)"


def expand_idea(idea, provider, key):
    raw = _retry(lambda: complete(provider, key, expand_system_prompt(),
                                  f"Idea title: {idea}", max_tokens=800))
    return parse_json(raw)


def _run_stage(stage, brief, provider, key, ground_text):
    system = stage_system_prompt(stage, ground_text if stage["key"] == "market" else None)
    raw = _retry(lambda: complete(provider, key, system, "Startup idea:\n\n" + brief, max_tokens=2200))
    data = parse_json(raw)
    data["stage"] = stage["key"]
    data["stage_name"] = stage["name"]
    return data


def evaluate(inputs, provider, key, grounding_mode):
    brief = brief_text(inputs)
    ground_text = grounding.search(brief) if grounding_mode == "live" else None

    # Run the five stages concurrently; keep original order in the result.
    done = {}
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(_run_stage, s, brief, provider, key, ground_text): s for s in STAGES}
        for fut in cf.as_completed(futures):
            s = futures[fut]
            done[s["key"]] = fut.result()
    stages = [done[s["key"]] for s in STAGES]

    # Weighted 0-100 score, computed HERE (not by the model). Also a 0-100 score per stage.
    earned = 0.0
    for st in stages:
        stage_earned = 0.0
        for atom in st.get("atoms", []):
            pts = _POINTS.get(atom.get("key"), 0)
            score = float(atom.get("score", 0) or 0)
            stage_earned += (score / 10.0) * pts
        earned += stage_earned
        possible = _STAGE_POINTS.get(st.get("stage"), 0)
        st["stage_score"] = round(stage_earned / possible * 100) if possible else 0
        st["stage_weight"] = possible
    total = round(earned)
    grade = grade_for(total)

    # Synthesis / verdict.
    score_summary = "\n".join(
        f"{st['stage_name']}: " +
        ", ".join(f"{a.get('name','?')} {a.get('score','?')}/10" for a in st.get("atoms", []))
        for st in stages
    )
    syn = parse_json(_retry(lambda: complete(
        provider, key, synthesis_system_prompt(),
        f"Idea:\n{brief}\n\nPer-area scores:\n{score_summary}\n\nWeighted total: {total}/100 (grade {grade['grade']})",
        max_tokens=900)))

    return {
        "total_score": total,
        "grade": grade,
        "grounded": bool(ground_text),
        "brief": brief,
        "stages": stages,
        "synthesis": syn,
    }
