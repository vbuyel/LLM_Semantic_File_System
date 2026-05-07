import os
from pathlib import Path

try:
    import pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz as pymupdf
        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


def extract_text_from_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = Path(file_path).suffix.lower()

    if ext == '.pdf':
        if not PYMUPDF_AVAILABLE:
            raise RuntimeError("PyMuPDF required for PDF: pip install pymupdf")
        return _extract_pdf(file_path)

    if ext == '.docx':
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx required for DOCX: pip install python-docx")
        return _extract_docx(file_path)

    if ext in ('.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm', '.rtf'):
        return _read_text(file_path)

    return _read_text(file_path)


def _extract_pdf(file_path: str) -> str:
    doc = pymupdf.open(file_path)
    text = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(text)


def _extract_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def _read_text(file_path: str) -> str:
    for encoding in ('utf-8', 'latin-1', 'cp1252'):
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode file: {file_path}")
