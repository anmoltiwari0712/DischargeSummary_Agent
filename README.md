# 🏥 Clinical Discharge Summary Agent 

 

An agentic AI system that reads messy, incomplete raw patient records (PDFs) and produces a structured, clinically safe discharge summary draft for clinician review. 

 

Built as a take-home assignment for an AI Engineer role — designed from scratch with no LangChain or CrewAI. 

 

--- 

 

## 📋 What It Does 

 

| Capability | Detail | 

|---|---| 

| **PDF Ingestion** | Handles both typed and handwritten hospital records via OCR fallback | 

| **ICD-10 Validation** | Every diagnosis validated and coded using the NLM ICD-10 API | 

| **Drug Normalization** | Indian brand names resolved to generics via RxNorm + local database | 

| **Drug Interactions** | Key medication pairs checked against OpenFDA | 

| **No Fabrication** | Missing fields flagged explicitly — never invented | 

| **Conflict Detection** | Disagreements between document sections flagged for clinician review | 

| **Critical Alerts** | Sodium <120, HbA1c >10%, DAMA, pending results all auto-flagged | 

| **PDF Output** | Generates a formatted clinical discharge summary PDF | 

| **Feedback Loop** | Clinician scores summaries across 5 dimensions — stored for RL loop | 

| **Web UI** | Gradio interface for upload → generate → review → score | 

 

--- 

 

## 🏗️ Architecture 

 

``` 

Patient PDF (71 pages, typed + handwritten) 

        ↓ 

PDF Ingestion Layer (PyMuPDF + pdfplumber + Tesseract OCR) 

        ↓ 

Python Extraction Engine 

  ├── Section parser (DIAGNOSIS, HISTORY, HOSPITAL COURSE, MEDICATIONS...) 

  ├── ICD-10 API  → validates and codes every diagnosis 

  ├── RxNorm API  → normalizes Indian brand names to generics 

  └── OpenFDA API → checks drug interactions 

        ↓ 

Structured JSON Summary 

  ├── All fields or explicit [MISSING — REQUIRES CLINICIAN REVIEW] flags 

  ├── Conflict flags with source attribution 

  └── Critical clinical alerts 

        ↓ 

Formatted PDF Output + Gradio Web UI 

        ↓ 

Clinician Feedback (5-dimension scoring → SQLite → RL loop) 

``` 

 

--- 

 

## 🛠️ Tech Stack 

 

| Layer | Technology | 

|---|---| 

| Language | Python 3.11 | 

| PDF Extraction | PyMuPDF, pdfplumber | 

| OCR | Tesseract + pytesseract + pdf2image | 

| Medical APIs | NLM ICD-10, RxNorm, OpenFDA (all free, no key needed) | 

| LLM (optional) | Groq API — Llama 3.3 70B (free tier) | 

| PDF Generation | ReportLab | 

| Web UI | Gradio | 

| Feedback Storage | SQLite (built-in Python) | 

| Data Validation | Pydantic | 

 

--- 

 

## 📁 Project Structure 

 

``` 

discharge-agent/ 

├── agent/ 

│   ├── __init__.py 

│   ├── loop.py          # Agent loop (LLM-driven tool calling) 

│   ├── tools.py         # Tool definitions + implementations 

│   ├── prompts.py       # System prompt + no-fabrication rules 

│   └── trace.py         # Step-by-step observability logger 

│ 

├── ingestion/ 

│   ├── __init__.py 

│   └── pdf_reader.py    # PDF extraction + OCR fallback 

│ 

├── feedback/ 

│   ├── __init__.py 

│   ├── store.py         # SQLite feedback storage 

│   ├── collector.py     # CLI scoring tool 

│   └── retriever.py     # Fetch top examples for RL loop 

│ 

├── data/ 

│   └── real/ 

│       └── patient_001.pdf   # Input patient records 

│ 

├── output/ 

│   ├── summaries/            # JSON + PDF outputs 

│   └── traces/               # Agent reasoning traces 

│ 

├── ui/ 

│   └── app.py               # Gradio web interface 

│ 

├── main.py                  # Entry point (Python extraction pipeline) 

├── pdf_generator.py         # JSON → formatted PDF 

├── .env                     # API keys (gitignored) 

├── .env.example 

└── requirements.txt 

``` 

 

--- 

 

## 🚀 Quick Start 

 

### 1. Prerequisites 

 

```bash 

# Mac 

brew install tesseract poppler 

 

# Python 3.11 via pyenv 

brew install pyenv 

pyenv install 3.11.9 

pyenv global 3.11.9 

``` 

 

### 2. Clone and install 

 

```bash 

git clone https://github.com/your-username/discharge-agent.git 

cd discharge-agent 

python -m venv .venv 

source .venv/bin/activate 

pip install -r requirements.txt 

``` 

 

### 3. Configure environment 

 

```bash 

cp .env.example .env 

# Edit .env and add your Groq API key (optional — Python extraction works without it) 

``` 

 

### 4. Add patient PDF 

 

```bash 

mkdir -p data/real 

# Copy your patient PDF to: 

cp your_patient_records.pdf data/real/patient_001.pdf 

``` 

 

### 5. Generate summary 

 

```bash 

# Python extraction pipeline (no LLM tokens needed) 

python main.py 

 

# Generate formatted PDF from the JSON output 

python pdf_generator.py 

``` 

 

### 6. Launch web UI 

 

```bash 

python ui/app.py 

# Opens at http://localhost:7860 

``` 

 

### 7. Score the output (feedback loop) 

 

```bash 

python -m feedback.collector 

``` 

 

--- 

 

## 📊 Output Example 

 

```json 

{ 

  "note": "AI-GENERATED DRAFT — REQUIRES CLINICIAN REVIEW", 

  "diagnoses": { 

    "primary": { 

      "name": "Acute Gastroenteritis with Dehydration", 

      "icd10_code": "A09", 

      "icd10_description": "Infectious gastroenteritis and colitis, unspecified" 

    }, 

    "secondary": [ 

      { "name": "Urinary Tract Infection", "icd10_code": "N39.0" }, 

      { "name": "Uncontrolled Type 2 Diabetes Mellitus", "icd10_code": "E11.9" }, 

      { "name": "Acute Kidney Injury", "icd10_code": "N17.9" } 

    ] 

  }, 

  "discharge_medications": [ 

    "TAB. RACTIPER 40MG 1-0-0 x7 DAYS [Generic: Rabeprazole — Proton Pump Inhibitor]", 

    "TAB. EMESET 4MG 1-1-1 x3 DAYS [Generic: Ondansetron — Antiemetic]" 

  ], 

  "clinician_flags": [ 

    "CRITICAL: Sodium 114 mmol/L — severely below normal range (<120 mmol/L)", 

    "CRITICAL: HbA1c 13.9% — severely uncontrolled diabetes mellitus", 

    "CONFLICT [Sodium level]: 127 mmol/L (Page 1) vs 114 mmol/L (ABG Page 28)", 

    "DISCHARGE AGAINST MEDICAL ADVICE", 

    "PENDING: Urine culture and sensitivity — result awaited" 

  ], 

  "total_flags": 15 

} 

``` 

 

--- 

 

## 🔒 Safety Design 

 

This system is built around a strict no-fabrication principle: 

 

- Every field contains either an extracted value or `[MISSING — REQUIRES CLINICIAN REVIEW]` 

- Conflicts between document sections are flagged with source attribution — never resolved arbitrarily 

- Pending lab results are recorded as pending — never estimated 

- Handwritten pages with poor OCR quality are flagged rather than guessed 

- The output is explicitly labelled as a draft requiring clinician review 

- No real patient data is used — the input PDF contains de-identified records 

 

--- 

 

## 🤖 Agent Design 

 

The system uses a **hybrid architecture**: 

 

1. **Python extraction layer** — deterministic parsing of clinical sections using keyword-based extraction. Handles the mechanical parts reliably without LLM token consumption. 

 

2. **Medical API enrichment** — ICD-10, RxNorm, and OpenFDA provide grounded medical knowledge. This is the RAG layer — the agent retrieves real medical facts rather than relying on LLM training data. 

 

3. **LLM agent loop** (optional, Groq/Llama 3.3 70B) — used for conflict detection and flag enrichment when token budget allows. Implements a real agent loop with tool calling, step cap, and observability trace. 

 

4. **Feedback RL loop** — clinicians score summaries across 5 dimensions. Scores are stored in SQLite and top-scoring examples are retrieved as few-shot context for future runs. 

 

--- 

 

## 📈 Feedback Dimensions 

 

| Dimension | Weight | Description | 

|---|---|---| 

| Completeness | 20% | All required fields filled or explicitly flagged | 

| Accuracy | 25% | Values match source documents | 

| Flag Quality | 20% | Real problems correctly identified | 

| No Fabrication | 25% | Nothing invented beyond source material | 

| Coherence | 10% | Readable and clinically useful | 

 

--- 

 

## 🌐 API Dependencies 

 

| API | Purpose | Key Required | Cost | 

|---|---|---|---| 

| NLM ICD-10 API | Diagnosis code lookup | No | Free | 

| RxNorm API | Drug name normalization | No | Free | 

| OpenFDA | Drug interaction lookup | No | Free | 

| Groq API | LLM inference (optional) | Yes | Free tier | 

 

--- 

 

## ⚠️ Disclaimer 

 

This system is for research and demonstration purposes only. It is not a medical device and must not be used for clinical decision-making without review by a qualified healthcare professional. All patient data used in development is synthetic or de-identified. 

 

--- 

 

## 📄 License 

 

MIT License — see LICENSE file for details. 

 

 