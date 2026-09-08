"""
Stage 3a: Unit Normalization

Converts fact values into one consistent base unit per unit-family,
so Stage 4 can compare numbers directly without re-parsing anything.
"""

# Base unit for money: raw INR (rupees). Everything converts to this.
MONEY_CONVERSIONS = {
    "INR_crore": 10_000_000,      # 1 crore = 1,00,00,000
    "INR_lakh": 100_000,          # 1 lakh = 1,00,000
    "INR_million": 1_000_000,
    "INR": 1,
}

# Units that don't need conversion — already comparable as-is
PASSTHROUGH_UNITS = {"percent", "days", "count", None}


def normalize_fact(fact: dict) -> dict:
    """
    Returns a NEW fact dict with two extra fields added:
    - normalized_value: value converted to base unit (if applicable)
    - normalized_unit: the base unit name used
    Leaves the original value/unit untouched for evidence/display purposes.
    """
    normalized = dict(fact)  # shallow copy, don't mutate the original
    value = fact.get("value")
    unit = fact.get("unit")

    if value is None:
        normalized["normalized_value"] = None
        normalized["normalized_unit"] = None
    elif unit in MONEY_CONVERSIONS:
        normalized["normalized_value"] = value * MONEY_CONVERSIONS[unit]
        normalized["normalized_unit"] = "INR"
    elif unit in PASSTHROUGH_UNITS:
        normalized["normalized_value"] = value
        normalized["normalized_unit"] = unit
    else:
        # Unknown unit — don't guess, just pass through unchanged
        # and flag it so we can see these cases later.
        normalized["normalized_value"] = value
        normalized["normalized_unit"] = unit
        normalized["normalization_warning"] = f"Unrecognized unit '{unit}', left unconverted"

    return normalized


if __name__ == "__main__":
    test_facts = [
        {"entity": "Delhivery", "attribute": "EBITDA", "value": 127, "unit": "INR_crore", "temporal_scope": "FY24"},
       {"entity": "Delhivery", "attribute": "EBITDA", "value": 1270, "unit": "INR_million", "temporal_scope": "FY24"},
        {"entity": "Delhivery", "attribute": "growth", "value": 30, "unit": "percent", "temporal_scope": "FY24"},
    ]

    for f in test_facts:
        result = normalize_fact(f)
        print(f"{f['value']} {f['unit']}  -->  {result['normalized_value']} {result['normalized_unit']}")