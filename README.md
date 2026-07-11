# 🏥 cuCO Agent API Backend

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-orange?style=flat)](https://github.com/langchain-ai/langgraph)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=flat&logo=supabase)](https://supabase.com/)
[![Groq](https://img.shields.io/badge/Groq%20LLaMA--3-orange?style=flat)](https://groq.com/)

An agentic, multi-insurer claim adjudication and Coordination of Benefits (COB) engine. Powered by **FastAPI**, **LangGraph**, and **Groq (LLaMA-3)**, with metadata and storage integrated into **Supabase**.

---

## 🚀 Key Features

1. **Agentic Coordination of Benefits (COB)**:
   - Adjudicates claims through primary and secondary insurers sequentially.
   - Calculates plan-level deductibles, coinsurance rates, copayments, and sub-limits dynamically.
   - Updates Year-To-Date (YTD) accumulators (deductible met, OOP max met) in-memory.

2. **Self-Correction & Reflection Loop**:
   - Validates the correctness of the financial ledger (`primary_paid + secondary_paid + patient_liability_covered + uncovered == total_billed`).
   - If a discrepancy is found (e.g. math errors, inconsistent calculations), the **Reflection Node** uses **LLaMA-3 via Groq** to diagnose the issue and automatically triggers a recalculation loop (up to 3 retries) until the ledger reconciles.

3. **Clear Patient Responsibility Tracking**:
   - Exposes three distinct patient cost fields to prevent reviewer confusion:
     * `patient_liability_covered`: The patient's responsibility for covered services (deductibles, coinsurance, copays).
     * `uncovered_amount`: The amount excluded due to plan sub-limits or uncovered procedures.
     * `total_patient_cost`: The exact total out-of-pocket check the patient owes (`patient_liability_covered + uncovered_amount`).

4. **Unified OCR & Document Parsing**:
   - Accepts `.png`, `.jpg`, `.jpeg`, `.pdf`, and `.txt` claim documents.
   - Extracts text using **Tesseract OCR** (images) and **pdfplumber** (PDFs).
   - Structures extraction into medical keys (`patient_name`, `diagnosis`, `cpt_codes`, `icd10_codes`, etc.) using Groq LLM before inserting metadata into Supabase.

---

## 🛠️ Tech Stack

- **Core**: Python 3.8+, FastAPI, Uvicorn
- **AI & Graph**: LangGraph (state machine engine), Groq (LLaMA-3-70B model)
- **Database & Storage**: Supabase (Postgres & Storage Bucket)
- **Document Processing**: PyTesseract (OCR), PIL (Pillow), pdfplumber

---

## 📋 API Endpoints

| Method | Endpoint | Description | Tags |
|:---|:---|:---|:---|
| **POST** | `/claims` | Creates a new medical claim record (requires a valid `user_id`). | Claims |
| **POST** | `/upload` | Uploads claim files (PDF/images) to Supabase Storage and inserts metadata. | Upload |
| **POST** | `/parse` | Accepts a file upload + `claim_id`, runs OCR/Parsing, and saves structured JSON. | Parse |
| **GET** | `/insurance/{insurer}` | Fetches dynamic coverage parameters for a given insurer plan. | Insurance |
| **POST** | `/insurance/eligibility` | Evaluates CPT codes for plan eligibility. | Insurance |
| **POST** | `/insurance/preauth` | Evaluates if CPT codes require pre-authorization. | Insurance |
| **POST** | `/process-claim` | Runs the full LangGraph COB workflow on a parsed claim. | Root |

---

## ⚙️ Getting Started

### Prerequisites
1. **Python 3.8+**
2. **Tesseract OCR** installed on your system (required for PNG/JPG extraction).

### 1. Clone & Switch Branch
```bash
git checkout arnab
```

### 2. Configure Environment Variables
Create a `.env` file in the project root directory:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
GROQ_API_KEY=your-groq-api-key
```

### 3. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 4. Run the Website & Server
The backend FastAPI server will automatically serve the frontend static files.
```bash
uvicorn app.main:app --reload --app-dir backend
```
👉 Access the Website at: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**
👉 Access the Swagger interactive API docs at: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 🧪 Testing and Verification

The repository contains scripts to run and test core services directly from the workspace:

### 1. LangGraph COB & Reflection Test
Runs the coordination of benefits workflow for mock claims (such as surgery claims with multiple insurers, or physiotherapy claims with sub-limits and uncovered amounts) and prints the full agent step logs.
```bash
python test_agent.py
```
*Outputs are saved to `expected_console_output.txt` for comparison.*

### 2. Unified Parser & OCR Test
Validates image OCR and PDF text extraction using local sample files.
```bash
python test_parser.py
```

### 3. API Route Handler Test
Validates endpoint uploads and Supabase metadata insertion.
```bash
python test_endpoint.py
```
