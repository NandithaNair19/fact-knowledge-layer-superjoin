"""
Stage 2: Fact Extraction (version 2 — strict atomic schema)
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a precise fact-extraction engine. You read fragments of text \
from real-world documents (which may be messy, fragmented slide text, or clean prose) \
and extract discrete factual claims.

STRICT SCHEMA — every fact must have exactly these fields:
- entity: the subject the fact is about (a company, a person, a segment, a country — NOT a time period)
- attribute: what is being measured or stated about the entity
- value: a PURE NUMBER only (no currency symbols, no "Cr", no "%", no "+", no commas as separators). If the fact is not numeric (e.g. a qualitative claim), set value to null.
- unit: the unit for the value, as a short string (e.g. "INR_crore", "percent", "days", "count"). Use null if not applicable.
- temporal_scope: the time period the fact applies to (e.g. "FY24", "Q4 FY23"), or null if none is stated.
- raw_evidence: the exact short snippet of the ORIGINAL text that supports this fact (verbatim, not paraphrased).
- confidence: your own confidence this extraction is correct, from 0.0 to 1.0.

RULES:
- Never bundle a number and its unit together in "value" — they are always separate fields.
- Never treat a time period (FY24, Q3, etc.) as an "entity".
- If a sentence describes a CHANGE (e.g. "increased by X to Y from Z"), extract each distinct number as its own separate fact, not one combined fact.
- Output ONLY a JSON object with a single key "facts", whose value is an array of fact objects. No other text.
- If the text is a long list (e.g. table of contents, index), extract at most the 10 most significant facts — do not attempt to extract every single line.

EXAMPLE:
Input text: "FY24 EBITDA increased by Rs. 578 Cr to Rs. 127 Cr from Rs. (452 Cr) in FY23"
Output:
{
  "facts": [
    {"entity": "Delhivery", "attribute": "EBITDA", "value": 127, "unit": "INR_crore", "temporal_scope": "FY24", "raw_evidence": "Rs. 127 Cr", "confidence": 0.95},
    {"entity": "Delhivery", "attribute": "EBITDA", "value": -452, "unit": "INR_crore", "temporal_scope": "FY23", "raw_evidence": "Rs. (452 Cr) in FY23", "confidence": 0.95},
    {"entity": "Delhivery", "attribute": "EBITDA year-over-year increase", "value": 578, "unit": "INR_crore", "temporal_scope": "FY24", "raw_evidence": "increased by Rs. 578 Cr", "confidence": 0.9}
  ]
}
"""


def extract_facts_v2(text: str, max_retries: int = 2) -> dict:
    """
    Sends page text to Groq using the strict schema above.
    Includes retry logic and input truncation to avoid token-limit
    failures on very long or list-heavy pages.
    """
    truncated_text = text[:3000]

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                response_format={"type": "json_object"},
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Text:\n{truncated_text}"}
                ]
            )
            raw_content = response.choices[0].message.content
            return json.loads(raw_content)

        except Exception as e:
            print(f"[extraction attempt {attempt + 1} failed] {e}")
            if attempt == max_retries:
                return {"facts": [], "extraction_failed": True, "error": str(e)}

    return {"facts": [], "extraction_failed": True}


if __name__ == "__main__":
    from pdf_extractor import extract_pdf

    chunks = extract_pdf("../sample_pdfs/03-delhivery-q4-fy24-earnings-presentation.pdf")
    target_page = next(c for c in chunks if c.page_number == 5)

    print("--- INPUT TEXT ---")
    print(target_page.text)
    print("\n--- PARSED FACTS ---")
    result = extract_facts_v2(target_page.text)
    print(json.dumps(result, indent=2))