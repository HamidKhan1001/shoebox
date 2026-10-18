"""Turn a file into plain text. Scanned images are out of scope (no OCR)."""
from __future__ import annotations

from pathlib import Path

TEXT_EXTS = {".txt", ".md", ".csv", ".eml", ".html", ".htm"}
SUPPORTED = TEXT_EXTS | {".pdf"}
MAX_CHARS = 6000  # keeps prompts small enough for a 3B model


class ExtractError(Exception):
    pass


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        try:
            reader = PdfReader(str(path))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception as e:  # corrupt/encrypted PDFs
            raise ExtractError(f"cannot read PDF: {e}") from e
    elif ext in TEXT_EXTS:
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ExtractError(f"unsupported file type {ext or '(none)'}")
    text = text.strip()
    if len(text) < 15:
        raise ExtractError("no extractable text (scanned image PDF? OCR is not included)")
    return text[:MAX_CHARS]
