"""
Shared fixtures and configuration for the test suite.
"""
import os
import sys
import pytest

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that `src.*` imports resolve.
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, no external deps)")
    config.addinivalue_line("markers", "integration: Integration tests (may need DB/Kafka)")
    config.addinivalue_line("markers", "system: System / end-to-end tests across services")
    config.addinivalue_line("markers", "acceptance: User-facing acceptance tests")


# ---------------------------------------------------------------------------
# Reusable fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_text():
    """Sample text for testing text processing."""
    return (
        "Artificial intelligence is transforming how we manage files. "
        "Semantic search allows users to find documents by meaning rather than keywords. "
        "This project uses embeddings stored in a vector database for similarity search."
    )


@pytest.fixture
def sample_long_text():
    """A long text that will be split into multiple chunks."""
    words = ["word"] * 1200
    return " ".join(words)


@pytest.fixture
def tmp_text_file(tmp_path, sample_text):
    """Create a temporary .txt file with sample content."""
    file_path = tmp_path / "test_document.txt"
    file_path.write_text(sample_text, encoding="utf-8")
    return str(file_path)


@pytest.fixture
def tmp_csv_file(tmp_path):
    """Create a temporary .csv file."""
    file_path = tmp_path / "data.csv"
    file_path.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")
    return str(file_path)


@pytest.fixture
def tmp_binary_file(tmp_path):
    """Create a temporary file with non-UTF-8 content."""
    file_path = tmp_path / "binary.dat"
    file_path.write_bytes(b"\x80\x81\x82\x83\xff\xfe")
    return str(file_path)
