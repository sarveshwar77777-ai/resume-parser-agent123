# Resume Parser Agent

A FastAPI web application that extracts information from PDF and DOCX resumes, then compares a candidate profile against a job description.

## Features

- Resume upload support for PDF and DOCX files
- Candidate profile extraction for contact details, education, experience, skills, certifications, and projects
- Job-fit report with matched and missing requirements
- Optional Gemini-enhanced matching when `GEMINI_API_KEY` is configured

## Run locally

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --reload-exclude '.venv/*' --port 8001
```

Open http://127.0.0.1:8001 in your browser.

## Optional Gemini setup

Set `GEMINI_API_KEY` before starting the server to use Gemini for enhanced job-fit matching. Without it, the app uses deterministic keyword matching.
