"""
Unit tests for src.file_ops.adapters.text_extractor.
"""
import os
import pytest
from src.file_ops.adapters.text_extractor import extract_text_from_file, _read_text


pytestmark = pytest.mark.unit


class TestExtractTextFromFile:
    """Tests for the extract_text_from_file function."""

    def test_extract_txt_file(self, tmp_text_file, sample_text):
        result = extract_text_from_file(tmp_text_file)
        assert result == sample_text

    def test_extract_csv_file(self, tmp_csv_file):
        result = extract_text_from_file(tmp_csv_file)
        assert "Alice" in result
        assert "Bob" in result

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError, match="File not found"):
            extract_text_from_file("/nonexistent/path/file.txt")

    def test_extract_md_file(self, tmp_path):
        md_file = tmp_path / "readme.md"
        md_file.write_text("# Title\n\nSome content", encoding="utf-8")
        result = extract_text_from_file(str(md_file))
        assert "# Title" in result

    def test_extract_json_file(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text('{"key": "value"}', encoding="utf-8")
        result = extract_text_from_file(str(json_file))
        assert '"key"' in result

    def test_extract_html_file(self, tmp_path):
        html_file = tmp_path / "page.html"
        html_file.write_text("<html><body>Hello</body></html>", encoding="utf-8")
        result = extract_text_from_file(str(html_file))
        assert "Hello" in result

    def test_extract_xml_file(self, tmp_path):
        xml_file = tmp_path / "data.xml"
        xml_file.write_text("<root><item>Test</item></root>", encoding="utf-8")
        result = extract_text_from_file(str(xml_file))
        assert "Test" in result

    def test_extract_unknown_extension_falls_back_to_text(self, tmp_path):
        unknown_file = tmp_path / "file.xyz"
        unknown_file.write_text("fallback text content", encoding="utf-8")
        result = extract_text_from_file(str(unknown_file))
        assert result == "fallback text content"

    def test_extract_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")
        result = extract_text_from_file(str(empty_file))
        assert result == ""


class TestReadText:
    """Tests for the _read_text helper."""

    def test_read_utf8(self, tmp_path):
        f = tmp_path / "utf8.txt"
        f.write_text("Привет мир", encoding="utf-8")
        assert "Привет" in _read_text(str(f))

    def test_read_latin1(self, tmp_path):
        f = tmp_path / "latin.txt"
        f.write_bytes("café".encode("latin-1"))
        result = _read_text(str(f))
        assert "caf" in result

    def test_read_cp1252(self, tmp_path):
        f = tmp_path / "cp.txt"
        content = "Smart 'quotes'"
        f.write_bytes(content.encode("cp1252"))
        result = _read_text(str(f))
        assert "Smart" in result
