"""Table extraction from PDFs using camelot (lattice mode for bordered legal tables)."""

import logging
from pathlib import Path

try:
    import camelot  # type: ignore[import-untyped]
except ImportError as _e:  # noqa: F841
    raise ImportError(
        "camelot-py is required for table extraction. "
        "Install with: pip install 'camelot-py[cv]'"
    ) from _e

logger = logging.getLogger(__name__)


def get_table_pages(filepath: str) -> list[int]:
    """
    Pre-screen a PDF for pages that likely contain tables using pdfplumber (fast).

    This avoids running camelot's slow Ghostscript conversion on every page.
    pdfplumber.find_tables() uses PDF geometry (lines/rects) to detect table regions
    in milliseconds — much faster than camelot's full parse.

    Args:
        filepath: Path to PDF file

    Returns:
        List of 1-indexed page numbers that contain tables
    """
    import pdfplumber

    pages_with_tables = []
    try:
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                # find_tables() uses line detection — fast, no OCR
                if page.find_tables():
                    pages_with_tables.append(i)
    except Exception as e:
        logger.warning(f"Could not pre-screen tables in {filepath}: {e}")

    return pages_with_tables


def extract_tables(filepath: str) -> list[dict]:
    """
    Extract structured tables from PDFs (penalty schedules, fee tables).

    Why camelot: pdfplumber.extract_table() misses many legal tables.
    camelot's lattice mode handles bordered tables reliably.

    Optimization: pre-screens with pdfplumber to find which pages have tables,
    then runs camelot only on those pages — avoids Ghostscript on every page.
    Skips entirely for image-based PDFs (camelot requires text-based PDFs).

    Args:
        filepath: Path to PDF file

    Returns:
        List of dicts with page, dataframe, and raw text for each table
    """
    import pdfplumber

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"PDF file not found: {filepath}")

    logger.info(f"Extracting tables from: {filepath.name}")

    # Step 1: Check if PDF is text-based — camelot only works on text PDFs
    try:
        with pdfplumber.open(str(filepath)) as pdf:
            sample_text = ""
            for page in pdf.pages[:3]:
                text = page.extract_text()
                if text:
                    sample_text += text
        if not sample_text.strip():
            logger.info(f"Skipping camelot for {filepath.name} — image-based PDF (no extractable text)")
            return []
    except Exception as e:
        logger.warning(f"Could not check PDF type for {filepath.name}: {e}")
        return []

    # Step 2: Pre-screen pages — only run camelot where tables exist
    table_pages = get_table_pages(str(filepath))
    if not table_pages:
        logger.info(f"No table pages detected in {filepath.name} — skipping camelot")
        return []

    pages_str = ",".join(map(str, table_pages))
    logger.info(f"Running camelot on {len(table_pages)} table page(s) in {filepath.name}: [{pages_str}]")

    # Step 3: Run camelot only on pre-screened pages
    try:
        tables = camelot.read_pdf(str(filepath), pages=pages_str, flavor="lattice")
    except Exception as e:
        logger.error(f"Error extracting tables from {filepath}: {e}")
        return []

    result = []
    for table in tables:
        result.append({
            "page": table.page,
            "df": table.df,
            "raw": table.df.to_string(),
            "structured": table.df.to_dict(orient="records"),
        })
        logger.info(
            f"Extracted table from page {table.page}: "
            f"{table.df.shape[0]} rows, {table.df.shape[1]} cols"
        )

    logger.info(f"Found {len(result)} tables in {filepath.name}")
    return result
