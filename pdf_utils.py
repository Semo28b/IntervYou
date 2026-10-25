import re
import unicodedata
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

_CONTACT_PATTERN = re.compile(
    r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"
    r"|\bhttps?://(?:www\.)?linkedin\.com\b",
    re.IGNORECASE,
)
_PHONE_PATTERN = re.compile(r"\+?\d[\d \t().-]{8,}\d")
_CV_SIGNAL_PATTERNS = (
    _CONTACT_PATTERN,
    re.compile(
        r"^\s*(?:education|academic\s*background|"
        r"المؤهلات التعليمية|المؤهل العلمي|التعليم)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^\s*(?:(?:work|professional)\s*experience|experience|"
        r"work\s+history|employment\s+history|الخبرة(?:\s+(?:العملية|المهنية))?|"
        r"الخبرات العملية|التاريخ الوظيفي)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^\s*(?:skills|core\s*skills|core\s*competencies|"
        r"competencies|المهارات|الكفاءات الأساسية)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"\b(?:19|20)\d{2}\s*(?:[-–—]|to)\s*"
        r"(?:(?:19|20)\d{2}|present|current|now)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:languages?|certifications?|licenses?|"
        r"(?:academic\s*)?projects?|career\s*objective|"
        r"professional\s*summary|profile|"
        r"اللغات|المشاريع|الشهادات|الدورات التدريبية|الإنجازات|"
        r"الملخص المهني|الهدف المهني)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    ),
)
_CHAPTER_HEADING_PATTERN = re.compile(r"^\s*chapter\s+\d+\b", re.IGNORECASE | re.MULTILINE)
_CONTENTS_HEADING_PATTERN = re.compile(
    r"^\s*(?:table\s+of\s+contents|contents)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_FIGURE_TABLE_CAPTION_PATTERN = re.compile(
    r"^\s*(?:figure|table)\s+\d+(?:[.: -])",
    re.IGNORECASE | re.MULTILINE,
)
_MAX_CV_PAGES = 5
_MAX_CV_TEXT_CHARACTERS = 25_000


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return normalized.translate(str.maketrans({"ی": "ي", "ک": "ك"}))


class UnreadablePDFError(ValueError):
    pass


def looks_like_cv(text: str, page_count: int | None = None) -> bool:
    if (
        (page_count is not None and page_count > _MAX_CV_PAGES)
        or len(text) > _MAX_CV_TEXT_CHARACTERS
    ):
        return False

    text = _normalize_text(text)
    normalized_text = re.sub(
        r"(?<![A-Za-z])((?:[A-Za-z][ \t]){2,}[A-Za-z])"
        r"(?![ \t][A-Za-z](?:[ \t]|$))(?![A-Za-z])",
        lambda match: re.sub(r"\s+", "", match.group()),
        text,
    )
    has_contact = _CONTACT_PATTERN.search(normalized_text) is not None or any(
        len(re.sub(r"\D", "", number)) >= 10
        for number in _PHONE_PATTERN.findall(normalized_text)
    )
    signals = (
        has_contact,
        *(
            pattern.search(normalized_text) is not None
            for pattern in _CV_SIGNAL_PATTERNS[1:]
        ),
    )
    if sum(signals) < 3:
        return False

    chapter_count = len(_CHAPTER_HEADING_PATTERN.findall(normalized_text))
    caption_count = len(_FIGURE_TABLE_CAPTION_PATTERN.findall(normalized_text))
    looks_like_manual_or_report = (
        chapter_count >= 3
        or _CONTENTS_HEADING_PATTERN.search(normalized_text) is not None
        or caption_count >= 3
    )
    return not looks_like_manual_or_report


def extract_pdf_text_with_page_count(pdf_bytes: bytes) -> tuple[str, int]:
    if not pdf_bytes:
        raise UnreadablePDFError("The uploaded PDF is empty.")

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = reader.pages
        page_text = [page.extract_text() or "" for page in pages]
    except PdfReadError as exc:
        raise UnreadablePDFError("The uploaded PDF could not be read.") from exc

    text = _normalize_text("\n".join(page_text)).strip()
    if not text:
        raise UnreadablePDFError("The PDF does not contain readable text.")
    return text, len(pages)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    text, _ = extract_pdf_text_with_page_count(pdf_bytes)
    return text
