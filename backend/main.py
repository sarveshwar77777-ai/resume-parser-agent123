from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import sys
import logging
import traceback

# Ensure backend/ is on sys.path so sibling imports work regardless of
# where the process is started (Vercel runs from the repo root).
sys.path.insert(0, os.path.dirname(__file__))

from models import ParseResult, ExtractorStatus
from pipeline.extractor import extract
from pipeline.segmenter import segment  
from pipeline.field_parser import parse_fields
from pipeline.scorer import score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Resume Parser Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
os.makedirs(frontend_dir, exist_ok=True)
index_path = os.path.join(frontend_dir, "index.html")
if not os.path.exists(index_path):
    with open(index_path, "w") as f:
        f.write("<html><body><h1>Resume Parser Agent Frontend</h1></body></html>")

# ---------------------------------------------------------------------------
# Supabase client (lazy-initialised; None when env vars are absent)
# ---------------------------------------------------------------------------
_supabase_client = None

def _get_supabase():
    """Return the Supabase client, creating it on first call.
    Returns None if the required env vars are not set."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        logger.warning("SUPABASE_URL / SUPABASE_SERVICE_KEY not set – persistence disabled")
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialised")
        return _supabase_client
    except Exception as exc:
        logger.error(f"Failed to create Supabase client: {exc}")
        return None


# ---------------------------------------------------------------------------
# Static files & root route
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(index_path)


# ---------------------------------------------------------------------------
# POST /parse – resume parsing + optional persistence
# ---------------------------------------------------------------------------
@app.post("/parse", response_model=ParseResult)
async def parse_resume(file: UploadFile = File(...), job_description: str = Form(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please choose a resume file.")
    if not job_description or not job_description.strip():
        raise HTTPException(status_code=400, detail="Please add a job description.")
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Limit 10MB.")
        
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ["pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Only .pdf and .docx files are accepted.")
        
    try:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Limit 10MB.")
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        logger.info(f"Extracting file {file.filename}")
        
        extractor_res = extract(content, file.filename)
        
        if extractor_res.status == ExtractorStatus.UNKNOWN:
            result = ParseResult(
                fields=[],
                fit_report=[],
                raw_text=extractor_res.raw_text,
                sections={},
                extractor_status=extractor_res.status,
                extractor_message=extractor_res.message
            )
            # Persist even on UNKNOWN status
            _persist_result(file.filename, result)
            return result
            
        segmenter_res = segment(extractor_res.raw_text)
        fields = parse_fields(segmenter_res)
        fit_report = score(fields, job_description)
        
        result = ParseResult(
            fields=fields,
            fit_report=fit_report,
            raw_text=extractor_res.raw_text,
            sections=segmenter_res.sections,
            extractor_status=extractor_res.status,
            extractor_message=extractor_res.message
        )

        _persist_result(file.filename, result)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during parse: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error during parsing.")


def _persist_result(filename: str, result: ParseResult) -> None:
    """Insert a row into Supabase parse_results.  Never raises."""
    try:
        sb = _get_supabase()
        if sb is None:
            return

        row = {
            "filename": filename,
            "fields": [f.model_dump() for f in result.fields],
            "fit_report": [r.model_dump() for r in result.fit_report],
            "extractor_status": result.extractor_status.value,
        }
        sb.table("parse_results").insert(row).execute()
        logger.info(f"Persisted parse result for {filename}")
    except Exception as exc:
        logger.error(f"Supabase insert failed (non-fatal): {exc}")
        logger.error(traceback.format_exc())


# ---------------------------------------------------------------------------
# GET /history – recent parse results
# ---------------------------------------------------------------------------
@app.get("/history")
def get_history():
    """Return the 50 most recent rows from parse_results."""
    sb = _get_supabase()
    if sb is None:
        return {"rows": [], "message": "Database not configured"}

    try:
        resp = (
            sb.table("parse_results")
            .select("*")
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return {"rows": resp.data}
    except Exception as exc:
        logger.error(f"Supabase select failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch history.")
