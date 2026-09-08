"""
Validates raw fact dicts returned by the LLM against our expected schema.
This is a defensive layer — we never fully trust LLM output structure,
no matter how good the prompt is. Anything malformed is skipped and
logged, never allowed to crash downstream code.
"""

REQUIRED_FIELDS = ["entity", "attribute", "value", "unit", "temporal_scope", "raw_evidence", "confidence"]


def validate_fact(fact) -> tuple[bool, str]:
    """
    Checks a single fact dict against our schema.
    Returns (is_valid, reason_if_invalid).
    """
    if not isinstance(fact, dict):
        return False, f"Expected a dict, got {type(fact).__name__}: {fact!r}"

    for field in REQUIRED_FIELDS:
        if field not in fact:
            return False, f"Missing required field '{field}'"

    value = fact["value"]
    if value is not None and not isinstance(value, (int, float)):
        if isinstance(value, str):
            try:
                fact["value"] = float(value) if "." in value else int(value)
            except ValueError:
                return False, f"'value' must be a number or null, got non-numeric string: {value!r}"
        else:
            return False, f"'value' must be a number or null, got {type(value).__name__}: {value!r}"

    if not isinstance(fact["confidence"], (int, float)) or not (0 <= fact["confidence"] <= 1):
        return False, f"'confidence' must be a number between 0 and 1, got {fact['confidence']!r}"

    if not isinstance(fact["entity"], str) or not fact["entity"].strip():
        return False, "'entity' must be a non-empty string"

    return True, ""


def validate_facts_batch(raw_result: dict) -> tuple[list, list]:
    """
    Takes the raw dict returned by extract_facts_v2 (with a "facts" array)
    and splits it into (valid_facts, skipped_with_reasons).
    """
    valid_facts = []
    skipped = []

    facts_list = raw_result.get("facts", [])
    if not isinstance(facts_list, list):
        return [], [{"item": facts_list, "reason": "'facts' was not a list"}]

    for fact in facts_list:
        is_valid, reason = validate_fact(fact)
        if is_valid:
            valid_facts.append(fact)
        else:
            skipped.append({"item": fact, "reason": reason})
            print(f"[validation] Skipped malformed fact: {reason}")

    return valid_facts, skipped


if __name__ == "__main__":
    example_v1_output = {
        "facts": [
            {"entity": "PTL", "attribute": "YoY growth", "value": "30%+"},
            "",
            {"entity": "TL", "attribute": "YoY revenue growth", "value": 40, "unit": "percent",
             "temporal_scope": "FY24", "raw_evidence": "40% YoY revenue growth", "confidence": 0.9},
        ]
    }

    valid, skipped = validate_facts_batch(example_v1_output)
    print(f"\nValid facts: {len(valid)}")
    print(f"Skipped facts: {len(skipped)}")
    for s in skipped:
        print(f"  - {s['reason']}")