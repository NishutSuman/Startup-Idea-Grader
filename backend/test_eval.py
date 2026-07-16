"""
Quick end-to-end test of the evaluation pipeline (no web UI).

Run it with a key in the environment (a FREE Gemini key works and costs nothing):
    cd backend
    GEMINI_API_KEY=your_key ./.venv/bin/python test_eval.py
    # or:  PROVIDER=anthropic ANTHROPIC_API_KEY=... ./.venv/bin/python test_eval.py
"""
import os
import textwrap
import config
config.load_env()          # load .env before pipeline reads PIPELINE_WORKERS
import pipeline

PROVIDER = os.environ.get("PROVIDER", "gemini")
GROUNDING = os.environ.get("GROUNDING", "reasoned")

IDEA = (
    "You know how at every big Indian wedding there's a crazy amount of food left over that "
    "just gets thrown in the bin? What if there was an app that connects wedding caterers and "
    "banquet halls with nearby orphanages and NGOs, so the extra food gets picked up and "
    "delivered the same night instead of wasted. Maybe the caterers pay a small fee, or we make "
    "money from companies' CSR budgets. Thinking of starting in Bangalore."
)


def wrap(s, indent="      "):
    return textwrap.fill(str(s), width=96, initial_indent=indent, subsequent_indent=indent)


def main():
    print(f"\nPROVIDER={PROVIDER}  GROUNDING={GROUNDING}\n")
    print("IDEA:\n" + wrap(IDEA, "  ") + "\n")
    print("Evaluating (5 stages)…\n")

    result = pipeline.evaluate({"the_idea": IDEA}, PROVIDER, None, GROUNDING)

    g = result["grade"]
    print("=" * 98)
    print(f"  OVERALL: {result['total_score']}/100   Grade {g['grade']} — {g['label']}"
          f"   (grounded: {result['grounded']})")
    print("=" * 98)

    for st in result["stages"]:
        print(f"\n### {st['stage_name']}")
        for a in st.get("atoms", []):
            print(f"  • {a.get('name')}: {a.get('score')}/10")
            print(wrap("why: " + str(a.get("reasoning", ""))))
            if a.get("concerns"):
                print(wrap("watch: " + str(a.get("concerns"))))
        if st.get("estimates"):
            print("  estimates:", st["estimates"])

    syn = result.get("synthesis", {})
    print("\n" + "=" * 98)
    print("  PANEL VERDICT")
    print("=" * 98)
    print(wrap(syn.get("overall_summary", ""), "  "))
    print("\n  Strengths:")
    for s in syn.get("top_strengths", []):
        print(wrap("+ " + s))
    print("\n  Risks:")
    for s in syn.get("key_risks", []):
        print(wrap("- " + s))
    print("\n  Questions for the founder:")
    for s in syn.get("questions_for_founder", []):
        print(wrap("? " + s))
    print("\n  Verdict:")
    print(wrap(syn.get("verdict", ""), "  "))
    print()


if __name__ == "__main__":
    main()
