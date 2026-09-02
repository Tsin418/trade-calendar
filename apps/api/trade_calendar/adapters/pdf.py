import fitz

from trade_calendar.adapters.errors import ParseError, PayloadTooLargeError
from trade_calendar.adapters.types import RawPayload


def extract_pdf_text(payload: RawPayload, max_pages: int = 100) -> str:
    try:
        document = fitz.open(stream=payload.content, filetype="pdf")
    except Exception as exc:
        raise ParseError("invalid PDF payload") from exc
    if document.page_count > max_pages:
        raise PayloadTooLargeError(f"PDF has {document.page_count} pages, limit is {max_pages}")
    text = "\n".join(page.get_text("text") for page in document)
    if not text.strip():
        raise ParseError("PDF contains no extractable text")
    return text

