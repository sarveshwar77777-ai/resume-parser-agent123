import re
from typing import List
from models import FieldResult, FieldStatus, SegmenterResult

FIELD_DEFINITIONS = [
    ("FULL-NAME", "Contact"),
    ("EMAIL", "Contact"),
    ("PHONE", "Contact"),
    ("URL-LINKEDIN", "Contact"),
    ("DEGREE-HIGHEST", "Education"),
    ("JOB-RECENT", "Experience"),
    ("LOCATION", "Contact"),
    ("SKILLS-LIST", "Skills"),
    ("CERTIFICATIONS-LIST", "Certifications"),
    ("PROJECTS-NOTABLE", "Projects"),
]

EMAIL_REGEX = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+')
PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}')
URL_REGEX = re.compile(r'(?:https?://)?(?:www\.)?(?:linkedin\.com/in/[\w-]+|github\.com/[\w-]+)|https?://\S+')
DEGREE_REGEX = re.compile(r'(?:Ph\.?D|Doctorate|Master(?:\'s)?|M\.?S\.?|M\.?B\.?A\.?|M\.?A\.?|M\.?Eng|Bachelor(?:\'s)?|B\.?S\.?|B\.?A\.?|B\.?E\.?|B\.?Tech|Associate(?:\'s)?)', re.IGNORECASE)
YEAR_REGEX = re.compile(r'((?:19|20)\d{2})')
ZIP_REGEX = re.compile(r'\b\d{5}(?:-\d{4})?\b')
CITY_STATE_REGEX = re.compile(r'[A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z]{2}')

def parse_fields(segmenter_result: SegmenterResult) -> List[FieldResult]:
    """Parses fields deterministically based on segmenter output."""
    sections = segmenter_result.sections
    all_text = "\n".join(sections.values())
    results = []

    for field_id, category in FIELD_DEFINITIONS:
        primary_text = sections.get(category, "")
        status = FieldStatus.NOT_FOUND
        value = ""
        evidence = ""
        source_section = category

        if field_id == "FULL-NAME":
            lines = primary_text.splitlines()
            for line in lines:
                line = line.strip()
                if not line: continue
                if EMAIL_REGEX.search(line) or PHONE_REGEX.search(line) or URL_REGEX.search(line) or ZIP_REGEX.search(line) or CITY_STATE_REGEX.search(line):
                    continue
                if re.match(r'^[A-Za-z\s.-]{2,30}$', line):
                    value = line
                    evidence = line
                    status = FieldStatus.FOUND
                    break

        elif field_id == "EMAIL":
            matches = EMAIL_REGEX.findall(primary_text)
            if not matches:
                matches = EMAIL_REGEX.findall(all_text)
                if matches: source_section = "Fallback"
            if matches:
                value = matches[0]
                evidence = value
                status = FieldStatus.AMBIGUOUS if len(matches) > 1 else FieldStatus.FOUND

        elif field_id == "PHONE":
            matches = PHONE_REGEX.findall(primary_text)
            if not matches:
                matches = PHONE_REGEX.findall(all_text)
                if matches: source_section = "Fallback"
            if matches:
                value = matches[0]
                evidence = value
                status = FieldStatus.AMBIGUOUS if len(matches) > 1 else FieldStatus.FOUND

        elif field_id == "URL-LINKEDIN":
            matches = URL_REGEX.findall(primary_text)
            if not matches:
                matches = URL_REGEX.findall(all_text)
                if matches: source_section = "Fallback"
            if matches:
                value = matches[0]
                evidence = value
                status = FieldStatus.AMBIGUOUS if len(matches) > 1 else FieldStatus.FOUND

        elif field_id == "DEGREE-HIGHEST":
            lines = primary_text.splitlines()
            degrees = []
            for line in lines:
                deg_match = DEGREE_REGEX.search(line)
                if deg_match:
                    year_match = YEAR_REGEX.search(line)
                    evidence_str = line.strip()
                    degrees.append((deg_match.group(), evidence_str))
            
            if degrees:
                ranks = {"phd": 4, "doctorate": 4, "master": 3, "m.s": 3, "m.b.a": 3, "m.a": 3, "meng": 3, 
                         "bachelor": 2, "b.s": 2, "b.a": 2, "b.e": 2, "b.tech": 2, "associate": 1}
                def get_rank(d):
                    for k, v in ranks.items():
                        if k in d[0].lower(): return v
                    return 0
                degrees.sort(key=get_rank, reverse=True)
                value = degrees[0][0]
                evidence = degrees[0][1]
                status = FieldStatus.FOUND

        elif field_id == "JOB-RECENT":
            lines = primary_text.splitlines()
            for line in lines:
                if len(line.strip()) > 5:
                    value = line.strip()
                    evidence = value
                    status = FieldStatus.FOUND
                    break

        elif field_id == "LOCATION":
            matches = CITY_STATE_REGEX.findall(primary_text) or ZIP_REGEX.findall(primary_text)
            if matches:
                value = matches[0]
                evidence = value
                status = FieldStatus.FOUND

        elif field_id == "SKILLS-LIST":
            if primary_text:
                items = re.split(r'[,|•\n]', primary_text)
                cleaned = list(dict.fromkeys([i.strip() for i in items if len(i.strip()) > 1]))
                if cleaned:
                    value = ", ".join(cleaned)
                    evidence = primary_text[:100] + "..." if len(primary_text) > 100 else primary_text
                    status = FieldStatus.FOUND

        elif field_id == "CERTIFICATIONS-LIST":
            if primary_text:
                lines = [re.sub(r'^[\W\d]+', '', line).strip() for line in primary_text.splitlines() if line.strip()]
                if lines:
                    value = "; ".join(lines)
                    evidence = "; ".join(lines[:3])
                    status = FieldStatus.FOUND

        elif field_id == "PROJECTS-NOTABLE":
            if primary_text:
                lines = [line.strip() for line in primary_text.splitlines() if len(line.strip()) > 10]
                if lines:
                    value = "; ".join(lines[:3])
                    evidence = value
                    status = FieldStatus.FOUND

        results.append(FieldResult(
            field_id=field_id,
            category=category,
            status=status,
            value=value,
            evidence=evidence,
            source_section=source_section
        ))

    return results
