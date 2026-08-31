# Resume Parser Agent

A FastAPI web application that extracts structured information from PDF and DOCX resumes, then compares a candidate profile against a job description to produce a fit report.

**Live Demo:** [resume-parser-agent123.vercel.app](https://resume-parser-agent123.vercel.app)

---

## Features

- **Resume Upload** — supports PDF and DOCX files (up to 10 MB)
- **Profile Extraction** — automatically detects contact details, education, experience, skills, certifications, and projects
- **Job-Fit Report** — matches extracted fields against a job description with confidence scoring
- **Gemini-Enhanced Matching** — optional LLM-powered scoring when `GEMINI_API_KEY` is configured (falls back to deterministic keyword matching)
- **Parse History** — persists every parse result to Supabase and exposes a `/history` endpoint
- **Deployed on Vercel** — serverless Python backend with static frontend served via FastAPI

---

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | Python, FastAPI, Pydantic           |
| Frontend  | HTML, CSS, JavaScript               |
| AI/LLM    | Google Gemini (optional)            |
| Database  | Supabase (PostgreSQL)               |
| Hosting   | Vercel (`@vercel/python`)           |
| Parsing   | pdfplumber (PDF), python-docx (DOCX)|

---

## Project Structure

```
resume-parser-agent123/
├── backend/
│   ├── main.py              # FastAPI app — routes, Supabase integration
│   ├── models.py             # Pydantic models (ParseResult, FieldResult, etc.)
│   ├── requirements.txt      # Python dependencies
│   └── pipeline/
│       ├── extractor.py      # PDF/DOCX text extraction
│       ├── segmenter.py      # Section header detection & splitting
│       ├── field_parser.py   # Regex-based field extraction
│       └── scorer.py         # JD matching (deterministic + Gemini)
├── frontend/
│   ├── index.html            # Main UI
│   ├── app.js                # Frontend logic
│   └── index.css             # Styles
├── vercel.json               # Vercel deployment config
└── README.md
```

---

## API Endpoints

| Method | Endpoint   | Description                                      |
|--------|------------|--------------------------------------------------|
| GET    | `/`        | Serves the frontend UI                           |
| POST   | `/parse`   | Upload a resume + job description, get results   |
| GET    | `/history` | Returns the 50 most recent parse results (JSON)  |

---

## Run Locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Open [http://127.0.0.1:8001](http://127.0.0.1:8001) in your browser.

---

## Environment Variables

| Variable              | Required | Description                                      |
|-----------------------|----------|--------------------------------------------------|
| `GEMINI_API_KEY`      | No       | Enables LLM-enhanced job-fit scoring via Gemini  |
| `SUPABASE_URL`        | No       | Supabase project URL for parse history storage   |
| `SUPABASE_SERVICE_KEY`| No       | Supabase service role key for database access    |

> All features work without these variables — Gemini falls back to keyword matching, and history is disabled without Supabase.

---

## Supabase Setup

1. Create a project at [supabase.com](https://supabase.com)
2. Run this SQL in the SQL Editor:

```sql
CREATE TABLE parse_results (
  id               uuid         DEFAULT gen_random_uuid() PRIMARY KEY,
  filename         text         NOT NULL,
  fields           jsonb        NOT NULL DEFAULT '[]'::jsonb,
  fit_report       jsonb        NOT NULL DEFAULT '[]'::jsonb,
  extractor_status text         NOT NULL,
  created_at       timestamptz  NOT NULL DEFAULT now()
);

CREATE INDEX idx_parse_results_created_at ON parse_results (created_at DESC);
```

3. Add `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to your Vercel project environment variables.

---

## Deploy to Vercel

1. Push this repo to GitHub
2. Import the repo in [vercel.com](https://vercel.com)
3. Set environment variables in Project Settings
4. Deploy — Vercel auto-detects `vercel.json` and builds the Python serverless function

---

## License

This project is for educational and personal use.
