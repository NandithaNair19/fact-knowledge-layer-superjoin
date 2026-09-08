"""
Stage 4a: Fact Matching

Finds candidate pairs of facts (possibly from different documents) that
are likely describing the same underlying real-world fact — same entity,
same attribute, same time period. Classification (corroborate/contradict/
reconcile) happens in a separate step, on these matched pairs.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "normalization"))

from entity_matcher import entities_match
from rapidfuzz import fuzz

ATTRIBUTE_SIMILARITY_THRESHOLD = 60


def _attributes_match(attr_a: str, attr_b: str) -> bool:
    score = fuzz.token_sort_ratio(attr_a.lower(), attr_b.lower())
    return score >= ATTRIBUTE_SIMILARITY_THRESHOLD


def _temporal_scopes_match(scope_a, scope_b) -> bool:
    """
    For now: exact match only (both "FY24", or both None).
    Deliberately NOT trying to be clever about "FY24 vs Q1-Q4 FY24"
    here — that nuance belongs in the classification step, where we
    decide if a mismatch is a real contradiction or a reconcilable
    scope difference.
    """
    return scope_a == scope_b


def find_candidate_pairs(facts_a: list, facts_b: list) -> list[tuple]:
    """
    Returns a list of (fact_a, fact_b) tuples that are plausibly
    about the same real-world fact, based on entity + attribute
    similarity. Facts from the same list are never paired with
    each other (we're comparing ACROSS documents, not within one).
    """
    candidates = []

    for fa in facts_a:
        for fb in facts_b:
            entity_ok, entity_score = entities_match(fa["entity"], fb["entity"])
            if not entity_ok:
                continue

            if not _attributes_match(fa["attribute"], fb["attribute"]):
                continue

            candidates.append((fa, fb, entity_score))

    return candidates


if __name__ == "__main__":
    doc_a_facts = [
        {"entity": "Delhivery", "attribute": "EBITDA", "value": 127, "unit": "INR_crore", "temporal_scope": "FY24"},
        {"entity": "Delhivery", "attribute": "PAT loss", "value": -1008, "unit": "INR_crore", "temporal_scope": "FY23"},
    ]
    doc_b_facts = [
        {"entity": "Delhivery Limited", "attribute": "EBITDA", "value": 127, "unit": "INR_crore", "temporal_scope": "FY24"},
        {"entity": "Delhivery Limited", "attribute": "net loss", "value": -1008, "unit": "INR_crore", "temporal_scope": "FY23"},
        {"entity": "RBI", "attribute": "repo rate", "value": 6.5, "unit": "percent", "temporal_scope": "FY24"},
    ]

    pairs = find_candidate_pairs(doc_a_facts, doc_b_facts)
    print(f"Found {len(pairs)} candidate pair(s):\n")
    for fa, fb, score in pairs:
        print(f"  A: {fa['entity']} / {fa['attribute']} / {fa['value']} {fa['temporal_scope']}")
        print(f"  B: {fb['entity']} / {fb['attribute']} / {fb['value']} {fb['temporal_scope']}")
        print(f"  (entity match score: {score:.0f})\n")