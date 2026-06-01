"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import tempfile


@pytest.fixture
def temp_data_dir():
    """Temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_legal_text():
    """Sample legal text for testing."""
    return """
Section 42. Private Placements

A private placement means the issue of securities.

(1) The company shall not issue fresh offers within 60 days of a prior placement.

(2) This restriction applies to all companies registered under this Act.

(3) Provided that the restriction shall not apply if the company was dissolved.

Explanation — For the purposes of this section, a private placement means any placement of securities other than a public offering.

Section 43. Rights of shareholders

(1) Every shareholder has the right to vote.

(2) The voting rights shall be exercised at a general meeting.

(a) The shareholder shall exercise rights in person.

(b) Or through a proxy appointed in writing.
    """


@pytest.fixture
def sample_pdf_path(temp_data_dir):
    """Create a dummy PDF path for testing."""
    pdf_path = temp_data_dir / "test.pdf"
    pdf_path.touch()
    return str(pdf_path)


@pytest.fixture
def sample_html_path(temp_data_dir):
    """Create a dummy HTML file for testing."""
    html_path = temp_data_dir / "test.html"
    html_path.write_text("<html><body><h1>Section 42</h1><p>Content</p></body></html>")
    return str(html_path)
