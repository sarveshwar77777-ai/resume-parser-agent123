from pydantic import BaseModel
from enum import Enum
from typing import Optional

class FieldStatus(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"

class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    MISSING = "MISSING"

class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ExtractorStatus(str, Enum):
    OK = "OK"
    UNKNOWN = "UNKNOWN"

class FieldResult(BaseModel):
    field_id: str
    category: str
    status: FieldStatus
    value: str
    evidence: str
    source_section: str

class FitReportItem(BaseModel):
    requirement: str
    match_status: MatchStatus
    explanation: str
    evidence_ref: str  # field_id reference
    confidence: Confidence

class ExtractorResult(BaseModel):
    raw_text: str
    status: ExtractorStatus
    message: str

class SegmenterResult(BaseModel):
    sections: dict[str, str]  # section_name -> content
    unmatched_headers: list[str]  # headers that didn't match allowlist

class ParseResult(BaseModel):
    fields: list[FieldResult]
    fit_report: list[FitReportItem]
    raw_text: str
    sections: dict[str, str]
    extractor_status: ExtractorStatus
    extractor_message: str
