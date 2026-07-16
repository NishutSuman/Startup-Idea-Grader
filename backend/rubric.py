"""
The rubric and the stage prompts — this is the 'how I think about startups' that
Mesa cares about most. Five stages, sixteen atoms, one hundred points.

Weights are opinions. Tune them to your own view before the interview and be
ready to defend each one. (All atom points must total 100.)
"""

GRADE_BANDS = [
    (85, "A", "Strong, worth pursuing"),
    (70, "B", "Promising, with conditions"),
    (58, "C", "Mixed, needs sharpening"),
    (46, "D", "Weak, reconsider"),
    (34, "E", "Very weak"),
    (0,  "F", "Pass"),
]

# Each stage is graded by its own focused prompt (better than one giant prompt).
STAGES = [
    {
        "key": "market",
        "name": "Market & Opportunity",
        "role": "a sharp early-stage investor who scrutinises the problem and the market before anything else",
        "estimates": "market_sizing",  # ask the model for TAM/SAM/SOM
        "atoms": [
            {"key": "problem_severity", "name": "Problem severity & urgency", "points": 10,
             "good": "a specific, urgent, frequent problem for a clear user; people already build painful workarounds (painkiller, not vitamin)",
             "bad": "a vague nice-to-have; nobody is actively looking for a fix"},
            {"key": "market_size", "name": "Market size & growth", "points": 8,
             "good": "many buyers with budget and willingness to pay, in a large or fast-growing market",
             "bad": "tiny or shrinking market, or nobody who will actually pay"},
            {"key": "why_now", "name": "Why now (timing)", "points": 5,
             "good": "a recent shift (new tech, behaviour, regulation, falling cost) makes this newly possible or urgent",
             "bad": "could have been built years ago; no reason it works now"},
            {"key": "competition", "name": "Competition & alternatives", "points": 7,
             "good": "clear-eyed about incumbents and substitutes, with a credible angle to win",
             "bad": "claims 'no competition' or ignores the obvious alternative (including 'do nothing')"},
        ],
    },
    {
        "key": "product",
        "name": "Product & Moat",
        "role": "a product-minded investor who probes differentiation and defensibility",
        "estimates": None,
        "atoms": [
            {"key": "differentiation", "name": "Solution & differentiation", "points": 8,
             "good": "a meaningfully better fix (about 10x better, cheaper, or faster), not a marginal tweak",
             "bad": "barely better than what exists, or a feature rather than a product"},
            {"key": "defensibility", "name": "Moat & defensibility", "points": 7,
             "good": "something that compounds and resists copying: network effects, proprietary data, brand, switching costs",
             "bad": "trivially cloneable the moment it works"},
            {"key": "feasibility", "name": "Feasibility to build", "points": 5,
             "good": "realistically buildable with sane resources and available tech",
             "bad": "needs breakthroughs, huge capital, or capabilities the founder lacks"},
        ],
    },
    {
        "key": "finance",
        "name": "Business & Finance",
        "role": "a numbers-driven investor focused on how the business actually makes money",
        "estimates": "unit_economics",  # ask the model for CAC/LTV/margin/capital
        "atoms": [
            {"key": "business_model", "name": "Business model clarity", "points": 6,
             "good": "a clear, believable way to charge someone who values it",
             "bad": "no obvious revenue model, or 'we'll figure out monetisation later'"},
            {"key": "unit_economics", "name": "Unit economics", "points": 9,
             "good": "each sale plausibly earns more than it costs to acquire and serve (healthy LTV vs CAC and margin)",
             "bad": "loses money per unit with no path to fixing it"},
            {"key": "capital_efficiency", "name": "Capital efficiency", "points": 7,
             "good": "can reach proof or revenue without enormous upfront capital",
             "bad": "needs heavy capital before any validation"},
        ],
    },
    {
        "key": "gtm",
        "name": "Go-to-Market & Growth",
        "role": "a growth-focused investor who cares about distribution, partnerships and retention",
        "estimates": None,
        "atoms": [
            {"key": "distribution", "name": "Distribution & marketing", "points": 6,
             "good": "a specific, affordable channel to reach the first 1,000 real customers",
             "bad": "'we'll go viral' or 'run ads' with no concrete channel"},
            {"key": "partnerships", "name": "Partnerships & channels", "points": 4,
             "good": "credible partners or channels that unlock reach or trust",
             "bad": "depends on partners who have no reason to cooperate"},
            {"key": "retention", "name": "Retention & engagement", "points": 6,
             "good": "a real reason users come back; people would be upset if it vanished",
             "bad": "one-time use, or no hook to bring users back"},
        ],
    },
    {
        "key": "execution",
        "name": "Execution & Team",
        "role": "a pragmatic investor betting on the people and the operational reality",
        "estimates": None,
        "atoms": [
            {"key": "founder_fit", "name": "Founder-market fit", "points": 6,
             "good": "a real edge here: insight, experience, or unfair access",
             "bad": "no particular reason this founder wins"},
            {"key": "operations", "name": "Operations & scalability", "points": 4,
             "good": "delivery gets easier (or cheaper) as it grows",
             "bad": "linear, manual effort that gets harder at scale"},
            {"key": "red_flags", "name": "Red flags & key risks", "points": 2,
             "good": "risks are acknowledged and addressable",
             "bad": "fatal legal, regulatory, or dependency risks ignored"},
        ],
    },
]

TOTAL_POINTS = sum(a["points"] for s in STAGES for a in s["atoms"])  # must be 100
assert TOTAL_POINTS == 100, f"Rubric points total {TOTAL_POINTS}, must be 100"


def grade_for(score):
    for cutoff, letter, label in GRADE_BANDS:
        if score >= cutoff:
            return {"grade": letter, "label": label}
    return {"grade": "F", "label": "Pass"}


def _atoms_block(stage):
    lines = []
    for a in stage["atoms"]:
        lines.append(
            f'- {a["name"]} (key "{a["key"]}", worth {a["points"]} pts)\n'
            f'    HIGH score: {a["good"]}\n'
            f'    LOW score:  {a["bad"]}'
        )
    return "\n".join(lines)


def stage_system_prompt(stage, grounding_text=None):
    """One focused prompt per stage. Role + rubric + calibration + grounding + strict JSON."""
    ground = ""
    if grounding_text:
        ground = ("\n\nREFERENCE DATA (recent, from web search — use it and cite figures where relevant):\n"
                  + grounding_text.strip())

    estimates_hint = ""
    estimates_schema = ""
    if stage.get("estimates") == "market_sizing":
        estimates_hint = ("\nAlso estimate the market size. State assumptions explicitly; approximate is fine, "
                          "but show the reasoning (top-down or bottom-up).")
        estimates_schema = (', "estimates": {"TAM": "...", "SAM": "...", "SOM": "...", '
                            '"assumptions": ["..."]}')
    elif stage.get("estimates") == "unit_economics":
        estimates_hint = ("\nAlso rough out the unit economics: a plausible price, cost to serve, gross margin, "
                          "and a CAC vs LTV sense-check. State assumptions.")
        estimates_schema = (', "estimates": {"price": "...", "CAC": "...", "LTV": "...", '
                            '"gross_margin": "...", "capital_needed": "...", "assumptions": ["..."]}')

    return (
        f"You are {stage['role']}.\n"
        f"Evaluate ONLY the '{stage['name']}' dimension of the startup idea below, strictly against the criteria.\n"
        f"Score each criterion 0-10 using the anchors. An average idea scores about 5 — do NOT flatter, and "
        f"reserve 9-10 for genuinely exceptional answers.{ground}\n\n"
        f"CRITERIA:\n{_atoms_block(stage)}\n\n"
        f"RULES:\n"
        f"- Judge only what the founder states. Never invent facts.\n"
        f"- Where the idea is silent on something important, say so and let it lower the score — vagueness is a real weakness.\n"
        f"- Be concrete and quote the founder's own words as evidence. No generic platitudes.\n"
        f"- Do NOT compute any total; scores are weighted in code.{estimates_hint}\n\n"
        f"Return ONLY valid JSON, no markdown:\n"
        f'{{"atoms": [{{"key": "<criterion key>", "name": "<criterion name>", "score": <0-10>, '
        f'"reasoning": "...", "evidence": "...", "concerns": "..."}}]{estimates_schema}}}'
    )


def synthesis_system_prompt():
    """Final professional assessment, given the brief and all stage scores."""
    return (
        "You are a senior startup evaluator writing the final assessment of an idea after it was scored "
        "across five areas (market, product, finance, go-to-market, execution).\n"
        "Be decisive, specific, and professional. Do NOT use TV-show or 'I am in / I am out' language.\n\n"
        "Return ONLY valid JSON, no markdown:\n"
        '{"overall_summary": "2-3 sentences, the honest bottom line", '
        '"recommendation": "exactly one of: Pursue, Refine, Reconsider, Pass", '
        '"top_strengths": ["3 short, concrete strengths"], '
        '"key_risks": ["3 short, concrete risks"], '
        '"questions_for_founder": ["the 3-5 most important questions to resolve next"], '
        '"verdict": "one professional sentence stating the recommendation and the single most important reason"}'
    )


def expand_system_prompt():
    """Mode B: turn a one-line idea into a structured brief with assumption options."""
    return (
        "A founder gave only a short idea title, which is not enough to evaluate. Your job is to make it gradeable "
        "by proposing sensible assumptions the founder can confirm or edit.\n"
        "For each field, propose 3-4 realistic, DISTINCT options (short phrases) the founder can pick from.\n"
        "Do not evaluate the idea. Only structure it.\n\n"
        "Return ONLY valid JSON, no markdown:\n"
        '{"fields": [{"key": "target_customer", "question": "Who is the primary customer?", "options": ["...","...","..."]}, '
        '{"key": "core_problem", "question": "What problem does it solve?", "options": ["..."]}, '
        '{"key": "business_model", "question": "How does it make money?", "options": ["..."]}, '
        '{"key": "geography", "question": "Where does it start?", "options": ["..."]}, '
        '{"key": "key_differentiator", "question": "What makes it different?", "options": ["..."]}]}'
    )
