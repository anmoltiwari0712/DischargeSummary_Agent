# Clinical Discharge Summary Agent — Design Notes 

 

## What Is Built 

 

An agentic AI system that reads raw hospital records (PDFs containing typed discharge summaries, handwritten ER charts, lab reports, and nursing notes) and produces a structured, clinically safe discharge summary draft for clinician review. 

 

Built from scratch in Python. No LangChain, no CrewAI. 

 

--- 

 

## Agent Loop Design 

 

The system uses a **hybrid agent architecture** — a deliberate choice made after observing that a pure LLM agent loop on noisy OCR text produces hallucinations regardless of prompt strength. 

 

### Layer 1 — Deterministic Python Extraction 

All mechanical extraction is done in Python directly: 

- Section parsing using keyword-based boundary detection (`DIAGNOSIS:`, `COURSE IN THE HOSPITAL`, etc.) 

- Table extraction via pdfplumber 

- OCR fallback via Tesseract for handwritten pages 

 

This layer is fast, reproducible, and consumes zero LLM tokens. It handles the parts of the problem that do not require intelligence. 

 

### Layer 2 — Medical API Enrichment (RAG) 

Rather than asking the LLM to recall medical knowledge from training data (which leads to hallucination), the system retrieves grounded facts from three free APIs: 

 

- **NLM ICD-10 API** — validates and assigns standard codes to every diagnosis 

- **RxNorm API** — resolves Indian brand drug names to generic equivalents and drug class 

- **OpenFDA** — checks for documented interactions between discharge medications 

 

This is the retrieval-augmented generation layer. The agent does not guess what "RACTIPER" is — it looks it up. 

 

### Layer 3 — LLM Agent Loop (Groq / Llama 3.3 70B) 

Used for conflict detection, flag enrichment, and cases requiring language understanding. Implements a real tool-calling loop: 

 

``` 

Receive task 

    ↓ 

Call read_document() → load full PDF text 

    ↓ 

Call extract_structured_data() → get pre-extracted fields 

    ↓ 

Call validate_diagnosis() for each diagnosis → ICD-10 enrichment 

    ↓ 

Call normalize_medication() for each drug → generic name lookup 

    ↓ 

Call lookup_drug_interaction() for key pairs → safety check 

    ↓ 

Call flag_conflict() for any disagreements found 

    ↓ 

Call flag_missing() for any required fields not found 

    ↓ 

Call finalize_summary() → produce structured output 

    ↓ 

[Step cap enforced — stops at MAX_STEPS=25] 

``` 

 

Every step is logged to a JSON trace file with timestamp, thought, action, arguments, and result. This provides full observability into why the agent made each decision. 

 

--- 

 

## No-Fabrication Guardrail 

 

This is the most important design constraint and is enforced at multiple levels: 

 

### 1. Prompt-level enforcement 

The system prompt contains explicit rules: 

- "Never invent, assume, or infer clinical facts" 

- "If a value is not explicitly stated in the source document, flag it as missing" 

- "Garbage OCR text means that field is MISSING — not an invitation to guess" 

- "Copy medication names verbatim — never substitute with a drug you know from medical training" 

 

### 2. Output schema enforcement 

The `finalize_summary` tool rejects calls where key fields contain obvious placeholder strings (e.g. "History", "Hospital course") — forcing the agent to use real extracted values or explicit missing flags. 

 

### 3. Explicit missing field protocol 

Every required field that cannot be found in any source page is populated with: 

``` 

[MISSING — REQUIRES CLINICIAN REVIEW] 

``` 

This is never left blank. A blank field could be mistaken for a field that was checked and found empty. An explicit flag cannot be misread. 

 

### 4. Source attribution 

The system tracks which page each value came from. Conflicts are flagged with source attribution: 

``` 

CONFLICT [Sodium level]: '127 mmol/L' (Page 1 discharge summary)  

vs '114 mmol/L' (Page 28 ABG) — requires clinician review 

``` 

The agent never resolves a conflict by picking one value. Both are surfaced. 

 

### 5. API-grounded drug and diagnosis validation 

Drug names and diagnoses are validated against external databases rather than the LLM's training data. This prevents the most common hallucination pattern — the LLM substituting a plausible-sounding drug name for an unfamiliar brand name. 

 

--- 

 

## Failure and Conflict Handling 

 

### OCR failures 

All 71 pages of the input PDF required OCR (no embedded text). Pages where OCR returns fewer than 50 characters are flagged: 

``` 

EXTRACTION WARNING: Page N — OCR quality insufficient, content may be incomplete 

``` 

The agent does not attempt to interpret noise as clinical data. 

 

### API timeouts 

Every external API call is wrapped with a 10-second timeout and try/except. On failure the agent receives an error string and continues — it flags the field for manual review rather than crashing. 

 

### Token limit handling (Groq free tier) 

The Groq free tier has a 100k tokens/day limit. The loop handles this by: 

- Truncating tool result messages before storing in conversation history 

- Trimming the message context window to the last 12 messages 

- On a 413 error, trimming more aggressively to the last 4 messages before retry 

 

### Step cap 

The agent loop enforces `MAX_STEPS=25`. If the cap is hit, the summary is saved with a flag noting it may be incomplete. A partial summary with honest flags is safer than an incomplete run with no output. 

 

### Conflicting clinical data 

When the same field appears with different values in different parts of the document (e.g. sodium 127 mmol/L on page 1 vs 114 mmol/L on page 28 ABG), the agent: 

1. Records both values and their sources via `flag_conflict()` 

2. Includes both in the `clinician_flags` array 

3. Never arbitrarily selects one value as authoritative 

 

--- 

 

## What Is Done 

 

- ✅ PDF ingestion with OCR fallback (PyMuPDF + Tesseract) 

- ✅ Python-based clinical section extraction 

- ✅ ICD-10 diagnosis validation and coding (NLM API) 

- ✅ Drug name normalisation — Indian brand names resolved to generics (RxNorm + local database) 

- ✅ Drug interaction checking (OpenFDA) 

- ✅ No-fabrication enforcement at prompt, schema, and validation layers 

- ✅ Conflict detection with source attribution 

- ✅ Missing field flagging with explicit `[MISSING — REQUIRES CLINICIAN REVIEW]` markers 

- ✅ Critical alert detection (sodium <120, HbA1c >10%, DAMA, pending results) 

- ✅ Step cap and iteration control 

- ✅ Full JSON trace of every agent step 

- ✅ Structured JSON output 

- ✅ Formatted clinical discharge summary PDF output 

- ✅ Gradio web UI (upload PDF → generate → download) 

- ✅ 5-dimension feedback scoring stored in SQLite 

- ✅ Feedback retrieval loop for few-shot improvement 

 

--- 

 

## What Is Not Done / Would Do Next 

 

**Hospital course extraction** — the hospital course section spans two pages and the OCR boundary detection does not reliably locate it. The field is flagged as missing rather than fabricated. Fix: train a lightweight span extractor on clinical document structure. 

 

**Exact admission/discharge dates** — only month and year are readable from OCR. The typed document does not contain explicit date fields in a consistent location. Fix: improve section boundary detection or add a date-specific regex pass. 

 

**Patient demographics** — name, age, and weight are not present in any reliably readable page. Fix: check the admission record pages (46-48) with improved handwriting OCR (higher DPI, pre-processing). 

 

**Full LLM agent reliability** — the Llama 3.3 70B model on the Groq free tier hallucinated in early runs when section extraction returned noisy OCR content. The hybrid Python-first approach was adopted as a more reliable alternative. With a larger context window and better rate limits (or GPT-4o), the full agent loop would be more viable. 

 

**Quantified RL improvement** — the feedback loop infrastructure is built and scoring works. Meaningful improvement measurement requires multiple runs with corrected few-shot examples, which the time constraint did not allow. The baseline composite score is 3.20/5.00. 

 

**Deployment** — the local architecture uses Tesseract OCR which is not available on standard cloud hosting. Deployment would require either containerisation (Docker + Tesseract) or switching to a cloud OCR service (Google Document AI, AWS Textract) for the handwritten pages. 

 

--- 

 

## Key Design Decisions Justified 

 

**Why hybrid Python + LLM rather than pure agent loop?** 

A pure LLM agent loop on 71 pages of noisy OCR text produced consistent hallucinations — the model substituted plausible clinical values when it could not parse garbled text. Python extraction is deterministic and auditable. The LLM adds value for language understanding and conflict detection, not for pattern matching on text. 

 

**Why medical APIs rather than LLM knowledge?** 

Drug names and diagnosis codes retrieved from RxNorm and ICD-10 are grounded in authoritative databases. LLM training data for Indian brand names is sparse and unreliable. API retrieval is the right tool for this lookup problem. 

 

**Why no LangChain/CrewAI?** 

The agent loop, tool dispatcher, and trace logger are ~300 lines of Python. Adding a framework would obscure the decision logic and make it harder to audit — which is the opposite of what a clinical safety system needs. 

 

**Why SQLite for feedback?** 

Zero infrastructure, zero cost, built into Python. Sufficient for the scale of this system. Trivially upgradeable to PostgreSQL for production. 

 

 