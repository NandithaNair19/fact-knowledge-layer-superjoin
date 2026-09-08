"""
End-to-end pipeline: PDF -> extracted, validated, normalized facts.
Also handles cross-document comparison (matching + classification).

This is the orchestration layer that ties together every stage we've
built so far. Nothing here is hardcoded to any specific document —
it works on whatever PDF path and page text it's given.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "extraction"))
sys.path.append(os.path.join(os.path.dirname(__file__), "normalization"))
sys.path.append(os.path.join(os.path.dirname(__file__), "comparison"))

from pdf_extractor import extract_pdf
from fact_extractor import extract_facts_v2
from validator import validate_facts_batch
from normalizer import normalize_fact
from matcher import find_candidate_pairs
from classifier import classify_pair


def process_pdf(path: str, max_pages: int = 5) -> list[dict]:
    """
    Runs one PDF through Stages 1-3: text extraction, LLM fact extraction,
    validation, normalization. Returns a flat list of clean, normalized
    facts, each tagged with its source doc_name and page_number.
    """
    chunks = extract_pdf(path)
    all_facts = []

    pages_to_process = chunks[:max_pages]
    print(f"Processing {len(pages_to_process)} of {len(chunks)} pages from {os.path.basename(path)}...")

    for chunk in pages_to_process:
        if not chunk.text.strip():
            continue  # skip blank pages, nothing to extract

        raw_result = extract_facts_v2(chunk.text)
        valid_facts, skipped = validate_facts_batch(raw_result)

        if skipped:
            print(f"  [page {chunk.page_number}] skipped {len(skipped)} malformed fact(s)")

        for fact in valid_facts:
            normalized = normalize_fact(fact)
            # Tag every fact with exactly where it came from — this is
            # what makes every fact traceable back to its evidence.
            normalized["source_doc"] = chunk.doc_name
            normalized["source_doc_id"] = chunk.doc_id
            normalized["source_page"] = chunk.page_number
            all_facts.append(normalized)

    print(f"  -> {len(all_facts)} valid facts extracted from {os.path.basename(path)}")
    return all_facts


def compare_documents(facts_a: list[dict], facts_b: list[dict]) -> list[dict]:
    """
    Finds candidate matching facts across two fact lists and classifies
    each pair as corroboration / contradiction / reconciled.
    """
    pairs = find_candidate_pairs(facts_a, facts_b)
    results = []

    for fact_a, fact_b, entity_score in pairs:
        classification = classify_pair(fact_a, fact_b)
        results.append({
            "fact_a": fact_a,
            "fact_b": fact_b,
            "relationship": classification["relationship"],
            "explanation": classification["explanation"],
        })

    return results


if __name__ == "__main__":
    # Real end-to-end test: two different Delhivery documents,
    # a small number of pages each to keep this fast.
    facts_prospectus = process_pdf("sample_pdfs/01-delhivery-prospectus-2022-excerpt.pdf", max_pages=15)
    facts_earnings = process_pdf("sample_pdfs/03-delhivery-q4-fy24-earnings-presentation.pdf", max_pages=15)

    print("\n--- CROSS-DOCUMENT COMPARISON ---\n")
    comparisons = compare_documents(facts_prospectus, facts_earnings)

    if not comparisons:
        print("No matching fact pairs found between these page ranges.")
    else:
        for c in comparisons:
            print(f"[{c['relationship'].upper()}]")
            print(f"  A ({c['fact_a']['source_doc']}, p{c['fact_a']['source_page']}): {c['fact_a']['entity']} / {c['fact_a']['attribute']} = {c['fact_a']['value']} {c['fact_a']['unit']} ({c['fact_a']['temporal_scope']})")
            print(f"  B ({c['fact_b']['source_doc']}, p{c['fact_b']['source_page']}): {c['fact_b']['entity']} / {c['fact_b']['attribute']} = {c['fact_b']['value']} {c['fact_b']['unit']} ({c['fact_b']['temporal_scope']})")
            print(f"  Explanation: {c['explanation']}\n")
    # Dump all facts for manual inspection — helps us find genuinely
    # good real examples of each relationship type across the full
    # extracted set, not just the small comparison window above.
    import json
    with open("all_extracted_facts.json", "w") as f:
        json.dump({
            "prospectus_facts": facts_prospectus,
            "earnings_facts": facts_earnings,
        }, f, indent=2)
    print(f"\nSaved {len(facts_prospectus) + len(facts_earnings)} total facts to all_extracted_facts.json for inspection.")