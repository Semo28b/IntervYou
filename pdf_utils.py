import re
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

_CV_SECTION_PATTERNS = (
    re.compile(
        r"\b(?:work|professional)\s+experience\b|\bexperience\b|"
        r"\b(?:employment|work)\s+history\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\beducation\b|\bacademic\s+background\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bskills\b|\bcore\s+competencies\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bprojects?\b|\bcertifications?\b|\blicenses?\b|\bawards?\b|"
        r"\bprofessional\s+summary\b|\bcareer\s+objective\b",
        re.IGNORECASE,
    ),
)
_CONTACT_PATTERN = re.compile(
    r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"
    r"|\bhttps?://(?:www\.)?linkedin\.com\b",
    re.IGNORECASE,
)
_PHONE_PATTERN = re.compile(r"\+?\d[\d \t().-]{8,}\d")


class UnreadablePDFError(ValueError):
    pass


def looks_like_cv(text: str) -> bool:
    normalized_text = re.sub(
        r"(?<![A-Za-z])((?:[A-Za-z][ \t]){2,}[A-Za-z])"
        r"(?![ \t][A-Za-z](?:[ \t]|$))(?![A-Za-z])",
        lambda match: re.sub(r"\s+", "", match.group()),
        text,
    )
    section_count = sum(
        pattern.search(normalized_text) is not None
        for pattern in _CV_SECTION_PATTERNS
    )
    contact_found = _CONTACT_PATTERN.search(normalized_text) is not None or any(
        len(re.sub(r"\D", "", number)) >= 10
        for number in _PHONE_PATTERN.findall(normalized_text)
    )
    has_work_history = (
        _CV_SECTION_PATTERNS[0].search(normalized_text) is not None
    )
    return section_count >= 2 or (contact_found and has_work_history)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        raise UnreadablePDFError("The uploaded PDF is empty.")

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        page_text = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise UnreadablePDFError("The uploaded PDF could not be read.") from exc

    text = "\n".join(page_text).strip()
    if not text:
        raise UnreadablePDFError("The PDF does not contain readable text.")
    return text
