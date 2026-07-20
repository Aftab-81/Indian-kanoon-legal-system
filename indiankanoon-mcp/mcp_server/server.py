"""
server.py — Indian Kanoon MCP Server
Exposes tools that can be called by AI models or MCP clients.

Run: python server.py
Transport: stdio (default for local use)
"""

import sys
import os
import json
import logging

# Add parent directory to path so scraper.py is importable
sys.path.insert(0, os.path.dirname(__file__))

from fastmcp import FastMCP
from scraper import (
    fetch_judgement_list,
    fetch_all_judgements,
    fetch_judgement_html,
    download_judgement,
    COURT_TYPES,
    MONTH_MAP,
)

# IMPORTANT: Use stderr for logging — stdout is reserved for MCP protocol
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP(
    name="IndianKanoon Scraper",
    instructions=(
        "This server can search and download court judgements from indiankanoon.org. "
        "Use search_judgements to find judgements, download_judgement_pdf to save one, "
        "or batch_download_month to download all judgements for a month. "
        "Always be mindful of rate limits — add delays between requests."
    ),
)


# ─────────────────────────────────────────────
# Tool 1: List available courts
# ─────────────────────────────────────────────
@mcp.tool()
def list_courts() -> str:
    """
    List all available court types that can be used for filtering judgement searches.

    Returns:
        JSON string with a list of court names.
    """
    logger.info("Tool called: list_courts")
    courts = list(COURT_TYPES.keys())
    return json.dumps({"courts": courts})


# ─────────────────────────────────────────────
# Tool 2: Search judgements for a month
# ─────────────────────────────────────────────
@mcp.tool()
def search_judgements(
    year: int,
    month: str,
    court: str = "All Courts",
    page: int = 0,
) -> str:
    """
    Search for court judgements on indiankanoon.org for a specific year and month.

    Args:
        year: The year (e.g. 2025)
        month: Full month name (e.g. "January", "February", ..., "December")
        court: Court name from list_courts() — defaults to "All Courts"
        page: Page number (0-indexed, 10 results per page)

    Returns:
        JSON string with total count and list of judgements (id, title, court, date, url).
    """
    logger.info(f"Tool called: search_judgements(year={year}, month={month}, court={court}, page={page})")

    if month not in MONTH_MAP:
        return json.dumps({"error": f"Invalid month '{month}'. Use full month name like 'January'."})

    if court not in COURT_TYPES:
        court = "All Courts"

    result = fetch_judgement_list(year, month, court, page)
    return json.dumps(result, ensure_ascii=False)


# ─────────────────────────────────────────────
# Tool 3: Download a single judgement PDF
# ─────────────────────────────────────────────
@mcp.tool()
def download_judgement_pdf(
    doc_id: str,
    title: str,
    output_dir: str,
    use_pdf: bool = True,
) -> str:
    """
    Download a single court judgement and save it as a PDF (or HTML fallback).

    Args:
        doc_id: The document ID (e.g. "117249167")
        title: The judgement title (used for the filename)
        output_dir: Absolute path to the folder where the file should be saved
        use_pdf: If True, try to save as PDF (requires wkhtmltopdf). If False, save as HTML.

    Returns:
        JSON string with {"success": bool, "path": str, "error": str}
    """
    logger.info(f"Tool called: download_judgement_pdf(doc_id={doc_id}, output_dir={output_dir})")

    result = download_judgement(doc_id, title, output_dir, use_pdf=use_pdf, delay_seconds=1.0)
    return json.dumps(result, ensure_ascii=False)


# ─────────────────────────────────────────────
# Tool 4: Batch download all judgements for a month
# ─────────────────────────────────────────────
@mcp.tool()
def batch_download_month(
    year: int,
    month: str,
    output_dir: str,
    court: str = "All Courts",
    max_count: int = 50,
    use_pdf: bool = True,
    delay_seconds: float = 1.5,
) -> str:
    """
    Download all (or up to max_count) court judgements for a specific year and month.

    This tool handles the full pipeline:
    1. Searches for all judgements in the given month
    2. Downloads each one as PDF (or HTML fallback)
    3. Returns a summary of what was downloaded

    Args:
        year: The year (e.g. 2025)
        month: Full month name (e.g. "January")
        output_dir: Absolute path to the folder where files should be saved
        court: Court name from list_courts() — defaults to "All Courts"
        max_count: Maximum number of judgements to download (default: 50)
        use_pdf: If True, try to save as PDF. If False, save as HTML.
        delay_seconds: Seconds to wait between requests (default: 1.5)

    Returns:
        JSON string with summary: {"downloaded": int, "failed": int, "files": [...]}
    """
    logger.info(
        f"Tool called: batch_download_month(year={year}, month={month}, "
        f"court={court}, max_count={max_count}, output_dir={output_dir})"
    )

    if month not in MONTH_MAP:
        return json.dumps({"error": f"Invalid month '{month}'."})

    # Create output subfolder: output_dir/year/month/
    save_dir = os.path.join(output_dir, str(year), month)
    os.makedirs(save_dir, exist_ok=True)
    logger.info(f"Saving to: {save_dir}")

    # Step 1: Fetch all judgement metadata
    logger.info("Fetching judgement list...")
    judgements = fetch_all_judgements(
        year=year,
        month_name=month,
        court=court,
        max_count=max_count,
        delay_seconds=delay_seconds,
    )

    logger.info(f"Found {len(judgements)} judgements to download")

    # Step 2: Download each one
    downloaded = []
    failed = []

    for i, j in enumerate(judgements):
        logger.info(f"Downloading {i+1}/{len(judgements)}: {j['title'][:60]}...")

        result = download_judgement(
            doc_id=j["id"],
            title=j["title"],
            output_dir=save_dir,
            use_pdf=use_pdf,
            delay_seconds=delay_seconds,
        )

        if result["success"]:
            downloaded.append({
                "id": j["id"],
                "title": j["title"],
                "path": result["path"],
                "skipped": result.get("skipped", False),
            })
        else:
            failed.append({
                "id": j["id"],
                "title": j["title"],
                "error": result.get("error", "Unknown error"),
            })

    summary = {
        "downloaded": len(downloaded),
        "failed": len(failed),
        "save_dir": save_dir,
        "files": downloaded,
        "errors": failed,
    }

    logger.info(f"Batch complete: {len(downloaded)} downloaded, {len(failed)} failed")
    return json.dumps(summary, ensure_ascii=False)


# ─────────────────────────────────────────────
# Tool 5: Get full judgement text
# ─────────────────────────────────────────────
@mcp.tool()
def get_judgement_text(doc_id: str) -> str:
    """
    Fetch and return the full text of a specific court judgement.

    Args:
        doc_id: The document ID (e.g. "117249167")

    Returns:
        JSON string with {"doc_id": str, "url": str, "text": str}
        or {"error": str} on failure.
    """
    logger.info(f"Tool called: get_judgement_text(doc_id={doc_id})")

    html = fetch_judgement_html(doc_id)
    if not html:
        return json.dumps({"error": f"Could not fetch document {doc_id}"})

    from scraper import extract_judgement_text
    text = extract_judgement_text(html)

    return json.dumps({
        "doc_id": doc_id,
        "url": f"https://indiankanoon.org/doc/{doc_id}/",
        "text": text[:10000],  # Limit to 10k chars to avoid overwhelming context
        "truncated": len(text) > 10000,
        "full_length": len(text),
    }, ensure_ascii=False)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting IndianKanoon MCP Server...")
    mcp.run()  # Uses stdio transport by default
