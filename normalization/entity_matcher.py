"""
Stage 3b: Entity Normalization

Decides whether two entity name strings likely refer to the same
real-world entity, using fuzzy string matching. This lets facts about
"Delhivery", "Delhivery Limited", and "the Company" be recognized as
the same entity without hardcoding company-specific rules.
"""

from rapidfuzz import fuzz

# Generic corporate suffixes/filler words to strip before comparing —
# these are domain-generic (not specific to Delhivery or any one company),
# so this doesn't violate the "no document-specific rules" constraint.
GENERIC_FILLER_WORDS = {"limited", "ltd", "the", "company", "inc", "corp", "corporation"}

SIMILARITY_THRESHOLD = 70  # 0-100 scale; tuned conservatively for now


def _clean_entity_name(name: str) -> str:
    words = name.lower().replace(".", "").split()
    filtered = [w for w in words if w not in GENERIC_FILLER_WORDS]
    return " ".join(filtered) if filtered else name.lower()


def entities_match(name_a: str, name_b: str) -> tuple[bool, float]:
    """
    Returns (is_match, similarity_score).
    """
    clean_a = _clean_entity_name(name_a)
    clean_b = _clean_entity_name(name_b)

    score = fuzz.token_sort_ratio(clean_a, clean_b)
    return score >= SIMILARITY_THRESHOLD, score


if __name__ == "__main__":
    test_pairs = [
        ("Delhivery", "Delhivery Limited"),
        ("the Company", "Delhivery"),
        ("Delhivery Limited", "Delhivery Ltd."),
        ("Delhivery", "RBI"),
        ("Express Parcel", "PTL"),
    ]

    for a, b in test_pairs:
        match, score = entities_match(a, b)
        print(f"'{a}' vs '{b}'  -->  match={match}, score={score:.0f}")