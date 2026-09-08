# fact-knowledge-layer

A system that reads PDF documents, extracts factual claims (numbers, statements, dates), links every fact back to its exact source evidence, and identifies when facts across different documents corroborate each other, genuinely contradict each other, or only *appear* to contradict due to differing context (like time period or units).

Built for the **Superjoin VIT 2026 Engineering Intern** hiring assignment.

---

## What is this?

Important facts about a company or a country's economy are usually scattered across many documents — a prospectus, an annual report, an earnings call deck, a government survey — each stating things slightly differently, at different points in time, using different units.

This tool answers a simple question: **when two documents both talk about "the same thing," do they actually agree?**

It does this by:

1. Reading a PDF, page by page, extracting both plain text and any tables
2. Using an LLM to pull out structured factual claims from that text (entity, attribute, value, unit, time period), always tied back to the exact sentence it came from
3. Validating every extracted fact against a strict schema, so malformed or incomplete extractions are caught and skipped rather than silently corrupting results
4. Normalizing values (e.g. converting crore/lakh/million to one common base) and entity names (e.g. "Delhivery" vs "Delhivery Limited") so facts from different documents can be compared fairly
5. Matching facts across two documents that are likely about the same underlying claim
6. Classifying each matched pair as a **corroboration**, a **contradiction**, or a **reconciled** difference (with a plain-English explanation of why it's reconciled)
7. Serving all of this through a browser-based API where you can upload PDFs and inspect results directly

---

## Architecture

```
PDF Upload
   |
   v
Text + Table Extraction (PyMuPDF + pdfplumber)
   |
   v
Fact Extraction (Groq LLM, strict atomic JSON schema)
   |
   v
Validation (schema check -- malformed entries skipped, not crashed on)
   |
   v
Normalization (unit conversion + fuzzy entity name matching)
   |
   v
Cross-Document Matching (entity + attribute similarity)
   |
   v
Classification (corroboration / contradiction / reconciled)
   |
   v
SQLite Storage
   |
   v
FastAPI endpoints (browser-based /docs UI for upload + inspection)
```
---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.10+ | Core language |
| PyMuPDF (fitz) | Fast PDF text extraction, page by page |
| pdfplumber | Table structure extraction from PDFs |
| Groq API (`openai/gpt-oss-20b`) | LLM-based fact extraction + reconciliation explanations |
| RapidFuzz | Fuzzy string matching for entity name normalization |
| FastAPI | Backend API, with auto-generated browser UI at `/docs` |
| Uvicorn | ASGI server for FastAPI |
| SQLite | Local storage for facts and relationships — zero setup, file-based |
| python-dotenv | Loads the Groq API key from `.env` |

Everything here is free and open-source. No paid service is required to run this project.

---

## Project Structure

```text
fact-knowledge-layer/
│
├── extraction/
│   ├── pdf_extractor.py      # Stage 1: PDF -> page-tagged text + tables
│   ├── llm_client.py          # Groq connectivity setup
│   ├── fact_extractor.py      # Stage 2: LLM-based fact extraction (strict schema)
│   └── validator.py           # Schema validation, catches malformed LLM output
│
├── normalization/
│   ├── normalizer.py          # Unit conversion (crore/lakh/million -> INR)
│   └── entity_matcher.py      # Fuzzy entity name matching (RapidFuzz)
│
├── comparison/
│   ├── matcher.py              # Finds candidate matching fact pairs across documents
│   └── classifier.py           # Classifies pairs: corroboration / contradiction / reconciled
│
├── storage/
│   ├── db.py                   # SQLite schema + read/write functions
│   └── seed_db.py              # Loads previously-extracted facts into the DB
│
├── api/
│   └── main.py                 # FastAPI app: /upload, /compare, /documents, /facts/{doc_id}
│
├── sample_pdfs/                 # Starter dataset (Delhivery + macroeconomy documents)
├── pipeline.py                   # Orchestrates all stages end-to-end
├── requirements.txt
├── .env.example
└── README.md
```

---

## Prerequisites

**1. Python 3.10+**
```bash
python3 --version
```

**2. A free Groq API key** (no credit card required)
- Sign up at [console.groq.com](https://console.groq.com)
- Go to **API Keys** → **Create API Key**
- Copy the key (starts with `gsk_...`)

**3. Git**
```bash
git --version
```

---

## Setup

**Step 1 — Clone the repo:**
```bash
git clone https://github.com/YOUR_USERNAME/fact-knowledge-layer.git
cd fact-knowledge-layer
```

**Step 2 — Create a virtual environment:**
```bash
# Mac/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python3 -m venv venv
venv\Scripts\Activate.ps1
```

**Step 3 — Install dependencies:**
```bash
pip install -r requirements.txt
```

**Step 4 — Configure your API key:**
```bash
cp .env.example .env
```
Open `.env` and add your Groq key:
```env
GROQ_API_KEY=your_actual_key_here
```

**Step 5 — Initialize the database:**
```bash
cd storage
python3 db.py
cd ..
```

**Step 6 — Run the API:**
```bash
uvicorn api.main:app --reload
```

Open **http://127.0.0.1:8000/docs** in your browser.

---

## Using the Web UI

FastAPI's auto-generated Swagger interface at `/docs` doubles as a full upload-and-inspect UI — no separate frontend needed.

### Upload and extract facts from a PDF
1. Open `http://127.0.0.1:8000/docs`
2. Expand **POST /upload**
3. Click **Try it out**
4. Choose a PDF file (see `sample_pdfs/` for the starter dataset)
5. Set `max_pages` (start small, e.g. `5`, to stay within free-tier rate limits)
6. Click **Execute**

You'll get back every extracted fact, each with its `entity`, `attribute`, `value`, `unit`, `temporal_scope`, `raw_evidence` (the exact source sentence), `source_page`, and a `confidence` score — this is what makes every fact traceable back to its exact evidence.

### Compare two documents
1. Upload two PDFs as above, and note their `doc_id` from each response (also visible via **GET /documents**)
2. Expand **POST /compare**
3. Enter both `doc_id_a` and `doc_id_b`
4. Click **Execute**

You'll get back every matched fact pair, labeled `corroboration`, `contradiction`, or `reconciled`, with a plain-English explanation for reconciled cases.

### Other endpoints
- **GET /documents** — list everything uploaded so far
- **GET /facts/{doc_id}** — view all facts extracted from one specific document

---
## Video Demo

[text](https://drive.google.com/file/d/1k-fUOzvf6L9TG1qt1woLum-M05phhepV/view?usp=sharing)

---
## Approach

### Why an atomic fact schema

Every fact is stored as:
```json
{
  "entity": "...",
  "attribute": "...",
  "value": <pure number, or null>,
  "unit": "...",
  "temporal_scope": "...",
  "raw_evidence": "<exact source sentence>",
  "confidence": <0.0-1.0>
}
```

This wasn't the first design — it came directly out of an early failure. An initial, loosely-specified prompt produced facts where value, unit, and time period were all bundled into one messy string, like `"value": "Rs. 578 Cr"` or `"10 lakh rupees in FY23"`. This made numeric comparison across documents impossible without writing fragile re-parsing logic downstream. Rewriting the prompt with an explicit, rigid schema plus one worked few-shot example fixed this reliably — the model needed to be *shown* the decomposition, not just told about it in the abstract. See **Limitations** for the full list of real failures encountered and how each was handled.

### Why no document-specific rules

The extraction prompt describes a fully generic schema — it has no mention of "revenue," "EBITDA," or any Delhivery-specific term. It was tested successfully against **two independent, unrelated datasets**: Delhivery corporate filings (prospectus, annual report, earnings deck) and India macroeconomic reports (Economic Survey, RBI Annual Report, IMF Article IV) — with zero dataset-specific code paths. The same extraction, normalization, and comparison logic runs identically regardless of which PDF is uploaded.

### Why comparison is a hybrid of logic and LLM calls

Determining whether two facts have the *same* value, once normalized, is pure arithmetic — it doesn't need an LLM. So corroboration and contradiction are detected with deterministic Python (`==` within a small tolerance), which is fast, free, and 100% reliable. The LLM is invoked *only* for the "reconciled" case — to generate a human-readable explanation of *why* two different-looking numbers (e.g. quarterly vs. annual revenue) aren't actually a contradiction. This keeps LLM usage — and free-tier rate-limit exposure — to the minimum necessary.

### Why validation is a separate, defensive layer

LLM output is never trusted blindly, no matter how carefully the prompt is written. A dedicated validation step checks every fact against the schema — right fields present, right types — before anything downstream touches it. This directly caught and gracefully handled several real malformed outputs during development (see Limitations).

### AI tools used
- **Groq API** (`openai/gpt-oss-20b`) — fact extraction and reconciliation explanations, chosen for its genuinely free tier (no credit card) to avoid any payment dependency, per the assignment's guidance to keep credentials/paid services out of the repo
- **Claude (Anthropic)** — used throughout as a design and pair-programming assistant: architecture planning, prompt design and debugging, and code review

---

## Limitations and Next Steps

### Real failures encountered during development, and how they were handled

1. **Bundled value/unit strings.** An early, loosely-specified prompt returned values like `"30%+"` or `"Rs. 578 Cr"` as single strings instead of separate numeric fields. **Fixed** by rewriting the prompt with a strict schema and a worked few-shot example forcing decomposition into `value` + `unit` + `temporal_scope`.

2. **Malformed JSON array entries.** The same early version occasionally returned a stray empty string (`""`) as an array element instead of a proper fact object — which would crash naive parsing code. **Fixed** by adding a dedicated validation layer that checks every entry's type and required fields, skipping and logging anything malformed instead of crashing.

3. **Groq API JSON-validation rejection.** With a longer, stricter prompt, the model occasionally produced output that failed Groq's own `json_validate_failed` check entirely, returning nothing. **Fixed** with retry logic (up to 2 retries per extraction call); if all retries fail, the page is marked `extraction_failed: true` and the pipeline continues rather than crashing.

4. **Token-limit truncation on dense pages.** A table-of-contents-style page produced so many candidate facts that the model's response was cut off mid-generation before completing valid JSON. **Fixed** by capping input text length per page and increasing the model's max output tokens.

5. **Free-tier rate limiting.** Groq's free tier caps both per-minute (8,000 tokens) and per-day (200,000 tokens) usage. Both were hit during development while processing ~30 pages across two documents. Per-minute limits are handled transparently by the existing retry logic (a few seconds' wait resolves them); the daily cap does not resolve quickly and can cause `/upload` to fail for the rest of that day on the free tier. This is a genuine trade-off of using a free/open-source-only stack rather than a paid API — documented honestly rather than hidden.

### Other known limitations

6. **Generic entity naming on context-poor pages.** When a page doesn't explicitly name the company (e.g. a slide just says "EBITDA: ₹127 Cr"), the model falls back to a generic label like "Company," reducing cross-document match precision.

7. **Attribute-phrasing sensitivity.** Cross-document matching relies on fuzzy string similarity between attribute names. Conceptually identical facts phrased very differently (e.g. "Restated loss" vs. "PAT loss") may not be recognized as comparable.

8. **Structural content extracted as facts.** Table-of-contents lines (e.g. "GENERAL SECTION ... page 1") are sometimes extracted as technically-true but not meaningful "facts."

9. **No cross-page context propagation.** A unit-scope declaration stated once on one page (e.g. "all amounts in INR million," seen in the Delhivery annual report's financial notes) is not currently carried forward to later pages processed independently.

10. **No dedicated frontend.** Given the project's time constraints, the UI is FastAPI's auto-generated Swagger interface rather than a custom-built one. This fully satisfies the "simple API or UI" requirement but isn't a polished end-user experience.

### What I would build next
- Semantic (embedding-based) attribute matching, replacing pure fuzzy string matching
- Document-level entity context propagated into every page's extraction call
- A lightweight page classifier to skip structural/non-factual pages (TOC, index)
- Async/queued batch processing with rate-limit-aware backoff, for smoother large-PDF handling on the free tier
- A local Ollama fallback for unlimited-throughput processing when Groq's free tier is exhausted — the extraction function is already isolated behind one interface, so swapping backends wouldn't require touching the rest of the pipeline

---

## Cost Breakdown

| Resource | Cost |
|---|---|
| Python, all pip libraries | Free |
| Groq API (`openai/gpt-oss-20b`) | Free tier — no credit card required, rate-limited |
| SQLite | Free, built into Python |

**Running this project is completely free.** No paid service, credential, or account beyond a free Groq signup is required.

---

## Troubleshooting

### `ModuleNotFoundError` for any package
```bash
pip install -r requirements.txt
```

### `groq.BadRequestError: json_validate_failed`
The model occasionally fails to produce valid JSON, especially on long or list-heavy pages. This is handled automatically by retry logic in `fact_extractor.py` — if you see this in logs but the pipeline continues, no action needed. If it persists across all retries for many pages, you may be hitting Groq's daily token cap (see below).

### `429 rate_limit_exceeded` (tokens per minute)
Wait a few seconds — the built-in retry logic handles this automatically in most cases.

### `429 rate_limit_exceeded` (tokens per day)
Groq's free tier caps total daily usage. This will not resolve quickly; either wait for the daily reset or reduce `max_pages` per upload. This is a known, documented trade-off of the free-tier-only design (see Limitations).

### `/upload` returns `"No valid facts extracted"`
Check the terminal running `uvicorn` for the underlying error — this generic message means the extraction pipeline caught an exception (most commonly a rate limit) and returned gracefully rather than crashing.

### `Port 8000 already in use`
```bash
uvicorn api.main:app --reload --port 8001
```

### `.env` changes not taking effect
Restart the server after editing `.env`:
```bash
Ctrl+C
uvicorn api.main:app --reload
```

---

## Additional Notes

This project was built end-to-end , using a deliberate incremental approach: each pipeline stage was tested against real extracted data before moving to the next, and every real failure encountered during development (listed in full under Limitations) directly informed the retry logic and defensive validation in the final code, rather than being designed around hypothetically.

Two independent starter datasets were tested — Delhivery corporate documents and India macroeconomic reports — to demonstrate the extraction and comparison logic generalizes across domains, not just one company's documents.