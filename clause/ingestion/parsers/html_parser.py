"""HTML parsing for India Code documents."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_html(filepath: str) -> str:
    """
    Parse India Code HTML into clean text.

    India Code HTML versions are cleaner than PDFs.
    Sections are wrapped in semantic HTML tags.
    Preserve section numbers exactly as they appear.

    Args:
        filepath: Path to HTML file

    Returns:
        Clean text with structure preserved
    """
    from bs4 import BeautifulSoup

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"HTML file not found: {filepath}")

    logger.info(f"Parsing HTML: {filepath.name}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
    except Exception as e:
        logger.error(f"Error parsing HTML {filepath}: {e}")
        raise

    # Remove nav, header, footer — legal content only
    for tag in soup(["nav", "header", "footer", "script", "style"]):
        tag.decompose()

    result = soup.get_text(separator="\n", strip=True)
    logger.info(f"Extracted {len(result)} characters from {filepath.name}")
    return result
