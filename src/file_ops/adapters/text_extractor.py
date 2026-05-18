import io
import os
import re
import unicodedata
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

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    import openpyxl
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False


_TEXT_EXTENSIONS = {
    # Documentation / markup
    ".txt", ".md", ".rst", ".rtf", ".tex", ".org", ".adoc", ".wiki",
    ".log", ".csv", ".tsv",
    # Web
    ".html", ".htm", ".xhtml", ".css", ".scss", ".less", ".sass",
    ".xml", ".json", ".yaml", ".yml", ".toml",
    # Config / infra
    ".ini", ".cfg", ".conf", ".env", ".gitignore", ".editorconfig",
    ".dockerfile", ".makefile", ".cmake", ".gradle",
    # Source code
    ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx",
    ".java", ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx",
    ".rs", ".go", ".rb", ".php", ".phtml", ".swift", ".kt", ".kts", ".scala",
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
    ".pl", ".pm", ".lua", ".r", ".m", ".mm",
    ".sql", ".graphql", ".gql", ".proto",
    ".svelte", ".vue",
}

_DOC_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}

SUPPORTED_EXTENSIONS = _TEXT_EXTENSIONS | _DOC_EXTENSIONS


def extract_text_from_bytes(content: bytes, ext: str) -> str:
    """Extract text from file content bytes, bypassing the filesystem.

    Returns an empty string for unsupported or binary file types.
    """
    ext = _normalise_ext(ext)
    if ext not in SUPPORTED_EXTENSIONS:
        return ""

    if ext == ".pdf":
        if not PYMUPDF_AVAILABLE:
            raise RuntimeError("PyMuPDF required for PDF: pip install pymupdf")
        doc = pymupdf.open(stream=content, filetype="pdf")
        text = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(text)

    if ext == ".docx":
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx required for DOCX: pip install python-docx")
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)

    if ext == ".pptx":
        if not PPTX_AVAILABLE:
            raise RuntimeError("python-pptx required for PPTX: pip install python-pptx")
        prs = Presentation(io.BytesIO(content))
        texts: list[str] = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    texts.append(shape.text)
        return "\n".join(texts)

    if ext == ".xlsx":
        if not XLSX_AVAILABLE:
            raise RuntimeError("openpyxl required for XLSX: pip install openpyxl")
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        rows: list[str] = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) for c in row if c is not None]
                if cells:
                    rows.append("\t".join(cells))
        wb.close()
        return "\n".join(rows)

    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def extract_text_from_file(file_path: str) -> str:
    """Extract text from a local file path.

    Returns an empty string for unsupported or binary file types.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = _normalise_ext(Path(file_path).suffix)
    if ext not in SUPPORTED_EXTENSIONS:
        return ""

    if ext == ".pdf":
        if not PYMUPDF_AVAILABLE:
            raise RuntimeError("PyMuPDF required for PDF: pip install pymupdf")
        return _extract_pdf(file_path)

    if ext == ".docx":
        if not DOCX_AVAILABLE:
            raise RuntimeError("python-docx required for DOCX: pip install python-docx")
        return _extract_docx(file_path)

    return _read_text(file_path)


def _normalise_ext(ext: str) -> str:
    ext = ext.strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    return ext


def _extract_pdf(file_path: str) -> str:
    doc = pymupdf.open(file_path)
    text = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(text)


def _extract_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def _read_text(file_path: str) -> str:
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return ""


_RE_RUNS = re.compile(r"[^\S\t\n\r]+")


def clean_text(text: str) -> str:
    """Strip null bytes and control characters, normalise whitespace."""
    cleaned: list[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        if ch in ("\t", "\n", "\r"):
            cleaned.append(ch)
        elif cat[0] == "C":
            cleaned.append(" ")
        else:
            cleaned.append(ch)
    return _RE_RUNS.sub(" ", "".join(cleaned)).strip()


_MIN_READABLE_RATIO = 0.3


def is_readable(
    text: str, min_chars: int = 10, threshold: float = _MIN_READABLE_RATIO
) -> bool:
    """Return True when *text* has enough meaningful content to be worth indexing."""
    if not text or len(text) < min_chars:
        return False
    readable = sum(1 for ch in text if ch.isalnum() or ch in (" ", "\t", "\n"))
    return readable / len(text) >= threshold
