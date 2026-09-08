"""
Stage 6: FastAPI backend.

POST /upload   - upload a PDF, runs full pipeline, stores facts
POST /compare  - compare two already-uploaded documents by doc_id
GET  /documents - list uploaded documents
GET  /facts/{doc_id} - view facts for one document
"""

import sys
import os
import shutil

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "storage"))

from fastapi import FastAPI, UploadFile, File, HTTPException
from pipeline import process_pdf, compare_documents
from db import init_db, save_document, save_facts, get_facts_by_doc, get_all_documents, save_relationship

app = FastAPI(title="Fact Knowledge Layer")

init_db()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploaded_pdfs")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), max_pages: int = 5):
    """
    Accepts a PDF, runs it through the full extraction pipeline,
    and stores the resulting facts in SQLite.
    """
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        facts = process_pdf(save_path, max_pages=max_pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction pipeline failed: {e}")

    if not facts:
        return {"message": "No valid facts extracted (extraction may have failed — see server logs).", "facts": []}

    doc_id = facts[0]["source_doc_id"]
    doc_name = facts[0]["source_doc"]
    save_document(doc_id, doc_name)
    save_facts(facts)

    return {"doc_id": doc_id, "doc_name": doc_name, "fact_count": len(facts), "facts": facts}


@app.get("/documents")
def list_documents():
    return get_all_documents()


@app.get("/facts/{doc_id}")
def get_facts(doc_id: str):
    facts = get_facts_by_doc(doc_id)
    if not facts:
        raise HTTPException(status_code=404, detail="No facts found for this doc_id")
    return facts


@app.post("/compare")
def compare(doc_id_a: str, doc_id_b: str):
    """
    Compares facts from two already-uploaded documents and classifies
    each matched pair as corroboration / contradiction / reconciled.
    """
    facts_a = get_facts_by_doc(doc_id_a)
    facts_b = get_facts_by_doc(doc_id_b)

    if not facts_a or not facts_b:
        raise HTTPException(status_code=404, detail="One or both doc_ids have no stored facts")

    results = compare_documents(facts_a, facts_b)

    for r in results:
        save_relationship(
            r["fact_a"].get("id"), r["fact_b"].get("id"),
            r["relationship"], r["explanation"]
        )

    return results