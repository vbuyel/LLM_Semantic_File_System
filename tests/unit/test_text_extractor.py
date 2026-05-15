"""
Unit tests for src.file_ops.adapters.text_extractor.
"""
import os
import pytest
from src.file_ops.adapters.text_extractor import (
    SUPPORTED_EXTENSIONS,
    _read_text,
    clean_text,
    extract_text_from_bytes,
    extract_text_from_file,
    is_readable,
)


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

    def test_extract_unknown_extension_returns_empty(self, tmp_path):
        unknown_file = tmp_path / "file.xyz"
        unknown_file.write_text("fallback text content", encoding="utf-8")
        result = extract_text_from_file(str(unknown_file))
        assert result == ""

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


class TestExtractTextFromBytes:
    """Tests for the extract_text_from_bytes function."""

    def test_rejects_png(self):
        result = extract_text_from_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, ".png")
        assert result == ""

    def test_rejects_unknown_ext(self):
        result = extract_text_from_bytes(b"some content", ".bogus")
        assert result == ""

    def test_rejects_empty_ext(self):
        result = extract_text_from_bytes(b"hello", "")
        assert result == ""

    def test_accepts_txt_bytes(self):
        result = extract_text_from_bytes(b"hello world utf-8", ".txt")
        assert result == "hello world utf-8"

    def test_ext_handles_missing_dot(self):
        result = extract_text_from_bytes(b"hello", "txt")
        assert result == "hello"


class TestWhitelist:
    """Verify that common text extensions are recognised and binary ones rejected."""

    def test_txt_is_supported(self):
        assert ".txt" in SUPPORTED_EXTENSIONS

    def test_md_is_supported(self):
        assert ".md" in SUPPORTED_EXTENSIONS

    def test_py_is_supported(self):
        assert ".py" in SUPPORTED_EXTENSIONS

    def test_png_is_not_supported(self):
        assert ".png" not in SUPPORTED_EXTENSIONS

    def test_jpg_is_not_supported(self):
        assert ".jpg" not in SUPPORTED_EXTENSIONS

    def test_zip_is_not_supported(self):
        assert ".zip" not in SUPPORTED_EXTENSIONS

    def test_exe_is_not_supported(self):
        assert ".exe" not in SUPPORTED_EXTENSIONS

    def test_mp3_is_not_supported(self):
        assert ".mp3" not in SUPPORTED_EXTENSIONS

    def test_pdf_is_supported(self):
        assert ".pdf" in SUPPORTED_EXTENSIONS

    def test_docx_is_supported(self):
        assert ".docx" in SUPPORTED_EXTENSIONS

    def test_pptx_is_supported(self):
        assert ".pptx" in SUPPORTED_EXTENSIONS

    def test_xlsx_is_supported(self):
        assert ".xlsx" in SUPPORTED_EXTENSIONS

    def test_html_is_supported(self):
        assert ".html" in SUPPORTED_EXTENSIONS

    def test_json_is_supported(self):
        assert ".json" in SUPPORTED_EXTENSIONS

    def test_yaml_is_supported(self):
        assert ".yaml" in SUPPORTED_EXTENSIONS

    def test_toml_is_supported(self):
        assert ".toml" in SUPPORTED_EXTENSIONS

    def test_rust_is_supported(self):
        assert ".rs" in SUPPORTED_EXTENSIONS

    def test_go_is_supported(self):
        assert ".go" in SUPPORTED_EXTENSIONS

    def test_sql_is_supported(self):
        assert ".sql" in SUPPORTED_EXTENSIONS

    def test_svelte_is_supported(self):
        assert ".svelte" in SUPPORTED_EXTENSIONS


class TestCleanText:
    """Tests for the clean_text helper."""

    def test_clean_normal_text(self):
        assert clean_text("Hello world test") == "Hello world test"

    def test_clean_strips_null_bytes(self):
        assert clean_text("Hello\x00World test") == "Hello World test"

    def test_clean_replaces_controls_with_space(self):
        assert clean_text("Hello\x01\x02World test") == "Hello World test"

    def test_clean_collapses_runs(self):
        assert clean_text("a\x00\x01\x02b") == "a b"

    def test_clean_preserves_tab(self):
        assert "Hello\tWorld" in clean_text("Hello\tWorld test")

    def test_clean_preserves_newline(self):
        assert "Hello\nWorld" in clean_text("Hello\nWorld test")


class TestIsReadable:
    """Tests for the is_readable helper."""

    def test_readable_normal_text(self):
        assert is_readable("This is a normal English sentence") is True

    def test_readable_unicode(self):
        assert is_readable("Привет мир как дела") is True

    def test_empty_false(self):
        assert is_readable("") is False

    def test_binary_garbage_false(self):
        assert is_readable("\x00\x01\x02\x03\x04\x05\x06\x07" * 5) is False

    def test_mostly_emoji_false(self):
        assert is_readable("🎉🎊💥🔥🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟") is False

    def test_short_text_below_min_chars(self):
        assert is_readable("hi", min_chars=10) is False
