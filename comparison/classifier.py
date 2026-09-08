"""
Stage 4b: Fact Classification

Given a matched pair of facts, decides whether they corroborate,
contradict, or can be reconciled through context (e.g. differing
time scope). Deterministic checks handle the clear cases; the LLM
is only invoked to explain genuinely ambiguous reconciliations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "normalization"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "extraction"))

from normalizer import normalize_fact
from llm_client import client  # reuse the already-configured Groq client

VALUE_TOLERANCE = 0.02  # 2% relative tolerance, to allow for rounding differences


def _values_approximately_equal(v1, v2) -> bool:
    if v1 is None or v2 is None:
        return v1 == v2
    if v1 == 0 and v2 == 0:
        return True
    return abs(v1 - v2) / max(abs(v1), abs(v2), 1e-9) <= VALUE_TOLERANCE


def _explain_reconciliation(fact_a: dict, fact_b: dict) -> str:
    """
    Calls the LLM only for the explanation text, once we already know
    (deterministically) that the scopes differ and this needs context.
    """
    prompt = f"""Two facts appear to conflict but may be reconcilable due to context.

Fact A: {fact_a['entity']} / {fact_a['attribute']} = {fact_a['value']} {fact_a['unit']}, scope: {fact_a['temporal_scope']}
Fact B: {fact_b['entity']} / {fact_b['attribute']} = {fact_b['value']} {fact_b['unit']}, scope: {fact_b['temporal_scope']}

In one short sentence, explain why these are NOT a real contradiction, based on their differing scope/context. If they genuinely can't be reconciled, say so plainly."""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


def classify_pair(fact_a: dict, fact_b: dict) -> dict:
    """
    Returns a dict describing the relationship between two matched facts:
    { "relationship": "corroboration" | "contradiction" | "reconciled",
      "explanation": str }
    """
    norm_a = normalize_fact(fact_a)
    norm_b = normalize_fact(fact_b)

    same_scope = fact_a.get("temporal_scope") == fact_b.get("temporal_scope")
    values_equal = _values_approximately_equal(norm_a["normalized_value"], norm_b["normalized_value"])

    if same_scope and values_equal:
        return {"relationship": "corroboration", "explanation": "Same entity, attribute, time period, and value (after normalization)."}

    if same_scope and not values_equal:
        return {"relationship": "contradiction", "explanation": f"Same time period ({fact_a['temporal_scope']}), but values differ: {norm_a['normalized_value']} vs {norm_b['normalized_value']} (normalized)."}

    # Different scopes — ask the LLM to explain the likely reconciliation
    explanation = _explain_reconciliation(fact_a, fact_b)
    return {"relationship": "reconciled", "explanation": explanation}


if __name__ == "__main__":
    pair_corroborate = (
        {"entity": "Delhivery", "attribute": "EBITDA", "value": 127, "unit": "INR_crore", "temporal_scope": "FY24"},
        {"entity": "Delhivery Limited", "attribute": "EBITDA", "value": 1270, "unit": "INR_million", "temporal_scope": "FY24"},
    )
    pair_contradict = (
        {"entity": "Delhivery", "attribute": "revenue", "value": 8142, "unit": "INR_crore", "temporal_scope": "FY24"},
        {"entity": "Delhivery Limited", "attribute": "revenue", "value": 9000, "unit": "INR_crore", "temporal_scope": "FY24"},
    )
    pair_reconcile = (
        {"entity": "Delhivery", "attribute": "revenue", "value": 2076, "unit": "INR_crore", "temporal_scope": "Q4 FY24"},
        {"entity": "Delhivery Limited", "attribute": "revenue", "value": 8142, "unit": "INR_crore", "temporal_scope": "FY24"},
    )

    for label, (fa, fb) in [("CORROBORATE test", pair_corroborate), ("CONTRADICT test", pair_contradict), ("RECONCILE test", pair_reconcile)]:
        print(f"--- {label} ---")
        result = classify_pair(fa, fb)
        print(result)
        print()