"""Stage 4: Scorer — takes structured fields + JD, produces ranked fit report.

Two modes:
1. Deterministic (default): keyword matching between JD and extracted fields.
2. LLM-enhanced (if GEMINI_API_KEY env var is set): uses Gemini for nuanced matching.

The scorer NEVER assigns FOUND/NOT_FOUND — that is the field parser's job only.
It only assigns MATCHED/MISSING.
"""

import os
import re
import json
import logging
from typing import List
from models import FieldResult, FitReportItem, MatchStatus, Confidence

logger = logging.getLogger(__name__)

# Stopwords to exclude from keyword matching
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "with", "on",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "must", "shall", "can", "need", "our", "your", "their", "its", "this",
    "that", "these", "those", "from", "into", "about", "between", "through",
    "during", "before", "after", "above", "below", "not", "but", "also",
    "than", "then", "such", "more", "most", "very", "just", "only", "over",
    "under", "each", "all", "any", "both", "few", "some", "other",
    "years", "year", "experience", "required", "preferred", "strong",
    "ability", "work", "team", "working", "using", "knowledge",
})


def _extract_keywords(text: str, min_length: int = 3) -> set[str]:
    """Extract meaningful keywords from text, filtering stopwords."""
    words = set(re.findall(r'\b[a-z][a-z0-9#+.-]*\b', text.lower()))
    return {w for w in words if len(w) >= min_length and w not in _STOPWORDS}


def deterministic_score(fields: List[FieldResult], job_description: str) -> List[FitReportItem]:
    """Score fields against JD using deterministic keyword matching.
    
    Parses JD into requirement lines, then checks each against
    extracted fields for keyword overlap.
    """
    # Parse JD into requirements: each substantive line/bullet is a requirement
    raw_lines = re.split(r'\n|•|–|—|\*|·', job_description)
    requirements = [line.strip() for line in raw_lines if len(line.strip()) > 10]
    
    if not requirements:
        return []
    
    # Build field lookup (only FOUND/AMBIGUOUS fields — never NOT_FOUND)
    fields_dict = {f.field_id: f for f in fields if f.status.value != "NOT_FOUND"}
    
    # Priority order for matching
    match_targets = [
        ("SKILLS-LIST", "Skills"),
        ("DEGREE-HIGHEST", "Education"),
        ("CERTIFICATIONS-LIST", "Certifications"),
        ("JOB-RECENT", "Experience"),
        ("PROJECTS-NOTABLE", "Projects"),
    ]
    
    report: list[FitReportItem] = []
    
    for req in requirements:
        req_keywords = _extract_keywords(req)
        if not req_keywords:
            continue
            
        best_match = None
        best_overlap = 0
        best_field_id = ""
        
        for field_id, _label in match_targets:
            if field_id not in fields_dict:
                continue
            field_val = fields_dict[field_id].value
            field_keywords = _extract_keywords(field_val)
            
            # Count overlapping keywords
            overlap = len(req_keywords & field_keywords)
            if overlap > best_overlap:
                best_overlap = overlap
                best_field_id = field_id
                best_match = fields_dict[field_id]
        
        if best_match and best_overlap > 0:
            # Determine confidence based on overlap ratio
            ratio = best_overlap / len(req_keywords) if req_keywords else 0
            if ratio >= 0.5:
                confidence = Confidence.HIGH
            elif ratio >= 0.25:
                confidence = Confidence.MEDIUM
            else:
                confidence = Confidence.LOW
            
            matched_words = req_keywords & _extract_keywords(best_match.value)
            explanation = f"Matched keywords [{', '.join(sorted(matched_words))}] found in {best_field_id}."
            
            report.append(FitReportItem(
                requirement=req,
                match_status=MatchStatus.MATCHED,
                explanation=explanation,
                evidence_ref=best_field_id,
                confidence=confidence,
            ))
        else:
            report.append(FitReportItem(
                requirement=req,
                match_status=MatchStatus.MISSING,
                explanation="No matching keywords found in any extracted field.",
                evidence_ref="",
                confidence=Confidence.LOW,
            ))
    
    # Sort: MISSING first, then MATCHED. Within same status, alphabetical by requirement.
    return sorted(report, key=lambda x: (x.match_status == MatchStatus.MATCHED, x.requirement))


def score(fields: List[FieldResult], job_description: str) -> List[FitReportItem]:
    """Scores resume fields against the job description.
    
    Uses LLM-enhanced mode if GEMINI_API_KEY is set, otherwise falls back
    to deterministic keyword matching.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                'gemini-2.0-flash',
                generation_config={"temperature": 0}
            )
            
            fields_data = [f.model_dump() for f in fields]
            
            prompt = f"""You are a resume-to-job-description matcher. Analyze the Job Description below and extract individual requirements. Then match each requirement against the candidate's structured fields.

RULES:
- Output ONLY a valid JSON array of objects.
- Each object MUST have: "requirement" (string), "match_status" ("MATCHED" or "MISSING"), "explanation" (string), "evidence_ref" (field_id string or empty string), "confidence" ("high", "medium", or "low").
- NEVER assign FOUND or NOT_FOUND — only MATCHED or MISSING.
- evidence_ref must be one of the field_ids from the candidate fields, or empty string if no match.
- Be precise: only mark MATCHED if the candidate's field genuinely satisfies the requirement.

Job Description:
{job_description}

Candidate Fields:
{json.dumps(fields_data, indent=2)}

Return ONLY the JSON array, no markdown fences, no explanation."""

            response = model.generate_content(prompt)
            response_text = response.text.strip()
            # Strip markdown code fences if present
            if response_text.startswith('```'):
                response_text = re.sub(r'^```(?:json)?\s*\n?', '', response_text)
                response_text = re.sub(r'\n?```\s*$', '', response_text)
            
            data = json.loads(response_text)
            report = [FitReportItem(**item) for item in data]
            return sorted(report, key=lambda x: (x.match_status == MatchStatus.MATCHED, x.requirement))
            
        except Exception as e:
            logger.warning(f"LLM scoring failed: {e}. Falling back to deterministic.")
            return deterministic_score(fields, job_description)
    else:
        return deterministic_score(fields, job_description)
