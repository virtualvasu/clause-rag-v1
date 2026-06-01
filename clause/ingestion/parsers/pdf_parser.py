"""PDF parsing using unstructured with auto-detection of text vs image-based PDFs."""

import logging
from pathlib import Path

try:
    from unstructured.partition.pdf import partition_pdf  # type: ignore[import-untyped]
    from unstructured.documents.elements import (  # type: ignore[import-untyped]
        Title,
        NarrativeText,
        Table,
        ListItem,
    )
except ImportError as _e:  # noqa: F841
    raise ImportError(
        "unstructured is required for PDF parsing. "
        "Install with: pip install 'unstructured[pdf]'"
    ) from _e

logger = logging.getLogger(__name__)


def is_text_based(filepath: str, sample_pages: int = 3) -> bool:
    """
    Detect whether a PDF has extractable text (text-based) or is a scanned image.

    Checks the first N pages for any extractable text using pdfplumber.
    Image-based (scanned) PDFs return empty text from pdfplumber.

    Args:
        filepath: Path to PDF file
        sample_pages: Number of pages to sample (default: 3)

    Returns:
        True if PDF is text-based, False if image-based (scanned)
    """
    import pdfplumber

    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages[:sample_pages]:
                text = page.extract_text()
                if text and text.strip():
                    return True
    except Exception as e:
        logger.warning(f"Could not detect PDF type for {filepath}: {e}")

    return False


def parse_pdf(filepath: str) -> str:
    """
    Parse a legal PDF into clean text preserving section structure.

    Strategy (auto-detected per file):
    - Text-based PDFs: strategy="fast" — pdfminer extraction, no ML models
    - Image-based PDFs: strategy="hi_res" — YOLO layout detection + OCR

    Both strategies produce Title, NarrativeText, Table, ListItem elements.
    Title elements get extra newline padding so the section splitter regex fires.

    Args:
        filepath: Path to PDF file

    Returns:
        Clean text with section boundaries preserved
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"PDF file not found: {filepath}")

    # Auto-detect: use fast pdfminer for text PDFs, hi_res+OCR for scanned images
    text_based = is_text_based(str(filepath))
    strategy = "fast" if text_based else "hi_res"
    logger.info(f"Parsing PDF: {filepath.name} [{'text-based' if text_based else 'image-based'} → strategy={strategy}]")

    kwargs: dict = {
        "filename": str(filepath),
        "strategy": strategy,
        "include_page_breaks": False,
    }
    if not text_based:
        # hi_res: also run table structure detection via ML
        kwargs["infer_table_structure"] = True

    elements = partition_pdf(**kwargs)

    text_parts = []
    for el in elements:
        if isinstance(el, Title):
            # Add extra newline before titles so section splitter regex fires
            text_parts.append(f"\n\n{el.text}\n")
        elif isinstance(el, (NarrativeText, ListItem)):
            text_parts.append(el.text)
        elif isinstance(el, Table):
            # Preserve table as pipe-delimited for table_extractor to detect
            text_parts.append(el.text)

    result = "\n".join(text_parts)
    logger.info(f"Extracted {len(result)} characters from {filepath.name}")
    return result
