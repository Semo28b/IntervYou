from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class UnreadablePDFError(ValueError):
    pass


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
