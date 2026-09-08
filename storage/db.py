"""
Stage 5: SQLite storage for facts and their cross-document relationships.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "facts.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            doc_name TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT,
            doc_name TEXT,
            source_page INTEGER,
            entity TEXT,
            attribute TEXT,
            value REAL,
            unit TEXT,
            temporal_scope TEXT,
            raw_evidence TEXT,
            confidence REAL,
            normalized_value REAL,
            normalized_unit TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_a_id INTEGER,
            fact_b_id INTEGER,
            relationship TEXT,
            explanation TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_document(doc_id: str, doc_name: str):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO documents (doc_id, doc_name) VALUES (?, ?)", (doc_id, doc_name))
    conn.commit()
    conn.close()


def save_facts(facts: list[dict]) -> list[int]:
    conn = get_connection()
    ids = []
    for f in facts:
        cur = conn.execute("""
            INSERT INTO facts (doc_id, doc_name, source_page, entity, attribute, value, unit,
                                temporal_scope, raw_evidence, confidence, normalized_value, normalized_unit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f.get("source_doc_id"), f.get("source_doc"), f.get("source_page"),
            f.get("entity"), f.get("attribute"), f.get("value"), f.get("unit"),
            f.get("temporal_scope"), f.get("raw_evidence"), f.get("confidence"),
            f.get("normalized_value"), f.get("normalized_unit"),
        ))
        ids.append(cur.lastrowid)
    conn.commit()
    conn.close()
    return ids


def get_facts_by_doc(doc_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM facts WHERE doc_id = ?", (doc_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_documents() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM documents").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_relationship(fact_a_id: int, fact_b_id: int, relationship: str, explanation: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO relationships (fact_a_id, fact_b_id, relationship, explanation)
        VALUES (?, ?, ?, ?)
    """, (fact_a_id, fact_b_id, relationship, explanation))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")