"""Read raw text from a referral file.

Two input types in this project:
  * .txt  -- plain UTF-8 referral letters.
  * .pdf  -- one deliberately-corrupt fixture (REF-015) that must fail to parse
             and surface as a System Exception (FILE_UNREADABLE).

A failure here is technical (the file cannot be read at all), which is distinct
from a readable-but-wrong document (NOT_A_REFERRAL) handled downstream.
"""

from __future__ import annotations

import os


class FileUnreadableError(Exception):
    """Raised when a referral file cannot be read or parsed at all."""


def read_referral_text(path: str) -> str:
    """Return the document's text, or raise FileUnreadableError.

    Empty / whitespace-only content is treated as unreadable.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text = _read_pdf(path)
    else:
        text = _read_txt(path)

    if not text or not text.strip():
        raise FileUnreadableError(f"No extractable text in {os.path.basename(path)}")
    return text


def _read_txt(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise FileUnreadableError(f"Could not read text file: {exc}") from exc


def _read_pdf(path: str) -> str:
    """Extract text from a PDF.

    Uses pypdf when available (it raises on a corrupt file). When pypdf is not
    installed we still detect the corrupt fixture structurally: a valid PDF ends
    with an %%EOF marker, and the REF-015 fixture is intentionally truncated
    without one.
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise FileUnreadableError(f"Could not open PDF: {exc}") from exc

    try:
        from pypdf import PdfReader  # type: ignore
        from pypdf.errors import PdfError  # type: ignore
    except ImportError:
        PdfReader = None  # type: ignore
        PdfError = Exception  # type: ignore

    # Structural sanity check first -- catches truncated/corrupt files even when
    # a lenient parser would otherwise return garbage.
    if b"%%EOF" not in raw:
        raise FileUnreadableError("PDF is truncated/corrupt: no %%EOF marker, no valid xref table")

    if PdfReader is None:
        raise FileUnreadableError("pypdf not installed and PDF could not be validated structurally")

    try:
        import io

        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:  # pypdf raises a family of errors on bad files
        raise FileUnreadableError(f"PDF parse failed: {exc}") from exc
