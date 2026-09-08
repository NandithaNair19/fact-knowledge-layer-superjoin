"""
Stage 2: Fact Extraction (version 1 — deliberately basic)

Goal: send one page of text to the LLM and see what facts come back,
with only a loose prompt. This version is NOT final — we're using it
to observe the model's natural behavior before tightening the schema.
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def extract_facts_v1(text: str) -> str:
    """
    Sends raw page text to Groq, asks for facts as JSON.
    Returns the raw string response (not yet parsed) so we can
    inspect exactly what the model outputs before we trust it.
    """
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You extract factual claims from document text. Output only valid JSON."
            },
            {
                "role": "user",
                "content": f"Extract all meaningful facts from this text as a JSON object with a 'facts' array. Each fact should have entity, attribute, and value fields.\n\nText:\n{text}"
            }
        ]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    from pdf_extractor import extract_pdf

    chunks = extract_pdf("../sample_pdfs/03-delhivery-q4-fy24-earnings-presentation.pdf")

    # Let's test on page 5 specifically — the one with FY24 headline numbers
    target_page = next(c for c in chunks if c.page_number == 5)

    print("--- INPUT TEXT ---")
    print(target_page.text)
    print("\n--- RAW LLM OUTPUT ---")
    result = extract_facts_v1(target_page.text)
    print(result)