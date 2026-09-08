"""
Loads the already-extracted facts (from all_extracted_facts.json) into
SQLite. This avoids needing new Groq calls — reuses real extraction
results from earlier in the session.
"""

import json
import os
import sys

sys.path.append(os.path.dirname(__file__))
from db import init_db, save_document, save_facts

JSON_PATH = os.path.join(os.path.dirname(__file__), "..", "all_extracted_facts.json")


def seed():
    init_db()

    with open(JSON_PATH) as f:
        data = json.load(f)

    for key, facts in data.items():
        if not facts:
            continue
        doc_id = facts[0]["source_doc_id"]
        doc_name = facts[0]["source_doc"]
        save_document(doc_id, doc_name)
        ids = save_facts(facts)
        print(f"Loaded {len(ids)} facts from {doc_name} (doc_id={doc_id})")


if __name__ == "__main__":
    seed()