import pytest
from unittest.mock import MagicMock, patch

from adapters.text_extractor import TextExtractorOperations


@pytest.fixture
def extractor():
    instance = TextExtractorOperations.__new__(TextExtractorOperations)
    instance.kafka = MagicMock()
    return instance


def test_clean_text(extractor):
    """Verify that clean_text removes control characters, strips null bytes, and collapses whitespace."""
    # Extra whitespace and control chars (null bytes, carriage returns)
    raw = "Hello \x00 World! \n\n This   is \r a test."
    cleaned = extractor.clean_text(raw)
    assert cleaned == "Hello World! \n\n This is \r a test."

    # Verify tab/newline preservation
    tabs_and_newlines = "\tSome text\nwith newlines\rand tabs\t"
    assert extractor.clean_text(tabs_and_newlines) == "Some text\nwith newlines\rand tabs"


def test_is_readable(extractor):
    """Verify is_readable detects sufficient alphanumeric content."""
    # Empty or too short
    assert not extractor.is_readable("")
    assert not extractor.is_readable("abc")  # < 10 chars

    # Mostly special/control chars
    assert not extractor.is_readable("$$$$$$$$$$$$$$$$$$$$")

    # Readable text
    assert extractor.is_readable("This is a perfectly readable English text with many words.")

    # Custom threshold
    assert extractor.is_readable("Short text", min_chars=5, threshold=0.1)


def test_normalise_ext(extractor):
    """Verify extension normalization."""
    assert extractor._normalise_ext("txt") == ".txt"
    assert extractor._normalise_ext(".TXT") == ".txt"
    assert extractor._normalise_ext(" .pdf ") == ".pdf"


def test_extract_text_from_bytes_unsupported(extractor):
    """Verify unsupported extensions return an empty string."""
    assert extractor.extract_text_from_bytes(b"some content", ".png") == ""


def test_extract_text_fallback_encoding(extractor):
    """Verify that text extraction falls back to different encodings."""
    # Latin-1 bytes
    latin_bytes = "Héllo".encode("latin-1")
    assert extractor.extract_text_from_bytes(latin_bytes, ".txt") == "Héllo"

    # CP1252 bytes
    cp_bytes = "Héllo".encode("cp1252")
    assert extractor.extract_text_from_bytes(cp_bytes, ".txt") == "Héllo"


@patch("adapters.text_extractor.pymupdf")
def test_extract_pdf_success(mock_pymupdf, extractor):
    """Verify successful PDF text extraction."""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Page content"
    mock_doc.__iter__.return_value = [mock_page]
    mock_pymupdf.open.return_value = mock_doc

    result = extractor.extract_text_from_bytes(b"%PDF...", ".pdf")
    assert result == "Page content"
    mock_pymupdf.open.assert_called_once()
    mock_doc.close.assert_called_once()


@patch("adapters.text_extractor.Document")
def test_extract_docx_success(mock_document_class, extractor):
    """Verify successful DOCX text extraction."""
    mock_doc = MagicMock()
    mock_paragraph = MagicMock()
    mock_paragraph.text = "Docx content"
    mock_doc.paragraphs = [mock_paragraph]
    mock_document_class.return_value = mock_doc

    result = extractor.extract_text_from_bytes(b"docx_bytes", ".docx")
    assert result == "Docx content"


@patch("adapters.text_extractor.Presentation")
def test_extract_pptx_success(mock_presentation_class, extractor):
    """Verify successful PPTX text extraction."""
    mock_prs = MagicMock()
    mock_slide = MagicMock()
    mock_shape = MagicMock()
    mock_shape.text = "Slide content"
    mock_slide.shapes = [mock_shape]
    mock_prs.slides = [mock_slide]
    mock_presentation_class.return_value = mock_prs

    result = extractor.extract_text_from_bytes(b"pptx_bytes", ".pptx")
    assert result == "Slide content"


@patch("adapters.text_extractor.openpyxl")
def test_extract_xlsx_success(mock_openpyxl, extractor):
    """Verify successful XLSX text extraction."""
    mock_wb = MagicMock()
    mock_sheet = MagicMock()
    mock_wb.worksheets = [mock_sheet]
    mock_sheet.iter_rows.return_value = [("CellA1", "CellB1", None, "CellD1")]
    mock_openpyxl.load_workbook.return_value = mock_wb

    result = extractor.extract_text_from_bytes(b"xlsx_bytes", ".xlsx")
    assert result == "CellA1\tCellB1\tCellD1"
    mock_wb.close.assert_called_once()


def test_extract_text_from_file_not_found(extractor):
    """Verify that extract_text_from_file raises FileNotFoundError for non-existent file."""
    with pytest.raises(FileNotFoundError):
        extractor.extract_text_from_file("non_existent_file_xyz.txt")


@patch("os.path.exists", return_value=True)
def test_extract_text_from_file_unsupported(mock_exists, extractor):
    """Verify that extract_text_from_file returns empty string for unsupported format."""
    assert extractor.extract_text_from_file("file.png") == ""


@patch("os.path.exists", return_value=True)
@patch.object(TextExtractorOperations, "_extract_pdf", return_value="PDF file content")
def test_extract_text_from_file_pdf(mock_extract, mock_exists, extractor):
    """Verify extract_text_from_file routes to PDF extractor."""
    assert extractor.extract_text_from_file("document.pdf") == "PDF file content"
    mock_extract.assert_called_once_with("document.pdf")


@patch("os.path.exists", return_value=True)
@patch.object(TextExtractorOperations, "_extract_docx", return_value="Docx file content")
def test_extract_text_from_file_docx(mock_extract, mock_exists, extractor):
    """Verify extract_text_from_file routes to DOCX extractor."""
    assert extractor.extract_text_from_file("document.docx") == "Docx file content"
    mock_extract.assert_called_once_with("document.docx")


@patch("os.path.exists", return_value=True)
@patch("builtins.open")
def test_extract_text_from_file_txt(mock_open, mock_exists, extractor):
    """Verify extract_text_from_file reads regular text file."""
    mock_file = MagicMock()
    mock_file.read.return_value = "File text content"
    mock_open.return_value.__enter__.return_value = mock_file

    assert extractor.extract_text_from_file("document.txt") == "File text content"
    mock_open.assert_called_once_with("document.txt", "r", encoding="utf-8")
