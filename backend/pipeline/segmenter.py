import re
from models import SegmenterResult

SECTION_HEADERS = {
    "Contact": [r"contact\s*(?:info(?:rmation)?|details)?", r"personal\s*(?:info(?:rmation)?|details)"],
    "Education": [r"education(?:al)?(?:\s*background)?", r"academics?", r"qualifications?"],
    "Experience": [r"(?:work|professional|employment)?\s*(?:experience|history)", r"employment", r"career\s*(?:history|summary)"],
    "Skills": [r"(?:technical\s*)?skills", r"(?:core\s*)?competenc(?:y|ies)", r"technologies", r"areas?\s*of\s*expertise", r"technical\s*proficienc(?:y|ies)"],
    "Certifications": [r"certifications?", r"certificates?", r"licen[cs]es?", r"professional\s*certifications?"],
    "Projects": [r"(?:personal|notable|key|selected)?\s*projects?"],
}

COMPILED_HEADERS = {
    k: [re.compile(f"^{p}$", re.IGNORECASE) for p in v] 
    for k, v in SECTION_HEADERS.items()
}

def segment(raw_text: str) -> SegmenterResult:
    """Segments raw resume text into sections based on headers.
    
    Algorithm:
    1. Split raw text into lines.
    2. Scan for lines matching any header pattern (short line, matches variant).
    3. Assign text between headers to the matched section.
    4. Text before the first header -> assigned to 'Contact'.
    5. Text under unrecognized headers -> logged, not assigned to any section.
    6. Never invent a section without a header match.
    """
    sections: dict[str, str] = {}
    unmatched_headers: list[str] = []
    
    current_section = "Contact"  # text before first header goes to Contact
    sections["Contact"] = ""
    lines = raw_text.splitlines()
    
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            # Preserve paragraph breaks within sections
            if current_section != "_UNMATCHED_" and current_section in sections and sections[current_section]:
                sections[current_section] += "\n"
            continue
            
        # Clean potential header (strip bullets, numbers, colons)
        cleaned_header = re.sub(r'^[\W\d]+|:+\s*$', '', stripped_line).strip()
        
        is_header = False
        if 0 < len(cleaned_header) < 60:
            for section_name, patterns in COMPILED_HEADERS.items():
                if any(p.match(cleaned_header) for p in patterns):
                    current_section = section_name
                    if current_section not in sections:
                        sections[current_section] = ""
                    is_header = True
                    break
            
            if not is_header and re.match(r'^[A-Z][A-Z\s]+$', cleaned_header) and len(cleaned_header) > 3:
                # Potentially unmatched header — record and stop assigning
                unmatched_headers.append(cleaned_header)
                current_section = "_UNMATCHED_"
                is_header = True  # treat as header so content isn't appended
                
        if not is_header and current_section != "_UNMATCHED_":
            if current_section not in sections:
                sections[current_section] = ""
            if sections[current_section]:
                sections[current_section] += "\n" + stripped_line
            else:
                sections[current_section] = stripped_line

    # Clean up: strip trailing whitespace from all sections, remove empty ones
    sections = {k: v.strip() for k, v in sections.items() if v.strip()}
                
    return SegmenterResult(sections=sections, unmatched_headers=unmatched_headers)
