"""PDF text extraction with OCR fallback."""

from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image


def read_pdfs(folder_path: str) -> dict[str, str]:
    """Read all PDFs in a folder, returning {filename: text_content}.

    Tries pymupdf text extraction first. If the result is empty or too short
    (< 50 chars), falls back to pytesseract OCR with Arabic + English.
    """
    folder = Path(folder_path)
    results: dict[str, str] = {}

    for pdf_path in sorted(folder.glob("*.pdf")):
        text = _extract_text(pdf_path)
        if len(text.strip()) < 50:
            text = _ocr_pdf(pdf_path)
        results[pdf_path.name] = text

    return results


def _extract_text(pdf_path: Path) -> str:
    """Extract text from a PDF using pymupdf."""
    text_parts: list[str] = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def _ocr_pdf(pdf_path: Path) -> str:
    """OCR a PDF by converting each page to an image and running pytesseract."""
    text_parts: list[str] = []
    with pymupdf.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_text = pytesseract.image_to_string(img, lang="ara+eng")
            text_parts.append(page_text)
    return "\n".join(text_parts)
