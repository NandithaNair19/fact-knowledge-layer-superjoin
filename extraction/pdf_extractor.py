"""
Stage 1: PDF Ingestion & Text Extraction

Goal: turn a PDF into a list of page-level text chunks, each tagged with
enough metadata (doc_id, page_number) that any fact we later pull from
this text can be traced straight back to its exact source.
"""

import pymupdf as fitz
import pdfplumber
import os
import hashlib
from dataclasses import dataclass, field


@dataclass
class PageChunk:
    doc_id: str
    doc_name: str
    page_number: int
    text: str
    tables: list = field(default_factory=list)


def _doc_id_from_path(path: str) -> str:
    """
    Stable short ID for a document, derived from its content hash.
    Same file uploaded twice (even renamed) => same doc_id.
    """
    with open(path, "rb") as f:
        content = f.read()
    return hashlib.sha1(content).hexdigest()[:10]


def extract_pdf(path: str) -> list[PageChunk]:
    """
    Extract page-level text + tables from a PDF.
    No filename-based or content-based special-casing — must generalize
    to any PDF, per the assignment's constraint.
    """
    doc_name = os.path.basename(path)
    doc_id = _doc_id_from_path(path)

    chunks: list[PageChunk] = []

    with fitz.open(path) as pdf:
        page_texts = [page.get_text("text") for page in pdf]

    page_tables = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            page_tables.append(tables)

    for i, text in enumerate(page_texts):
        page_number = i + 1
        tables = page_tables[i] if i < len(page_tables) else []
        chunks.append(
            PageChunk(
                doc_id=doc_id,
                doc_name=doc_name,
                page_number=page_number,
                text=text.strip(),
                tables=tables,
            )
        )

    return chunks


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <path_to_pdf>")
        sys.exit(1)

    result = extract_pdf(sys.argv[1])
    for chunk in result:
        print(f"--- {chunk.doc_name} | page {chunk.page_number} | doc_id={chunk.doc_id} ---")
        print(chunk.text[:300])
        if chunk.tables:
            print(f"[{len(chunk.tables)} table(s) found on this page]")
        print()