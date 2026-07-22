"""
scraper.py — Indian Kanoon web scraping logic
Handles: search, pagination, HTML fetching, PDF conversion
"""

import os
import re
import time
import calendar
import logging
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Configure logging (NEVER use print — it corrupts MCP stdio)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

BASE_URL = "https://indiankanoon.org"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Map month names to numbers
MONTH_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}

# Available court types (doctype values)
COURT_TYPES = {
    "All Courts": "",
    "Supreme Court": "supremecourt",
    "Delhi High Court": "delhi",
    "Bombay High Court": "bombay",
    "Calcutta High Court": "kolkata_app",
    "Madras High Court": "madras",
    "Allahabad High Court": "allahabad",
    "Kerala High Court": "kerala",
    "Karnataka High Court": "karnataka",
    "Gujarat High Court": "gujarat",
    "Andhra Pradesh High Court": "amravati",
    "Telangana High Court": "telangana",
    "Himachal Pradesh High Court": "himachal_pradesh",
}


def get_month_date_range(year: int, month_name: str) -> tuple[str, str]:
    """Return (from_date, to_date) strings like '1-1-2025' and '31-1-2025'."""
    month_num = MONTH_MAP[month_name]
    last_day = calendar.monthrange(year, month_num)[1]
    from_date = f"1-{month_num}-{year}"
    to_date = f"{last_day}-{month_num}-{year}"
    return from_date, to_date


def build_search_url(year: int, month_name: str, court: str = "", page: int = 0) -> str:
    """Build the indiankanoon.org search URL for a given year/month."""
    from_date, to_date = get_month_date_range(year, month_name)
    court_filter = MONTH_MAP.get(month_name, "")

    # Build the formInput query string
    court_code = COURT_TYPES.get(court, "")
    if court_code:
        form_input = f"doctypes:{court_code} fromdate:{from_date} todate: {to_date}"
    else:
        form_input = f"fromdate:{from_date} todate: {to_date}"

    import urllib.parse
    encoded = urllib.parse.quote(form_input)
    return f"{BASE_URL}/search/?formInput={encoded}&pagenum={page}"


def fetch_judgement_list(year: int, month_name: str, court: str = "", page: int = 0) -> dict:
    """
    Fetch one page of search results.

    Returns:
        {
            "total": int,
            "page": int,
            "judgements": [{"id": str, "title": str, "court": str, "date": str}, ...]
        }
    """
    url = build_search_url(year, month_name, court, page)
    logger.info(f"Fetching search page {page}: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch search page: {e}")
        return {"total": 0, "page": page, "judgements": [], "error": str(e)}

    soup = BeautifulSoup(response.text, "lxml")

    # Extract total result count
    total = 0
    count_span = soup.find("span", class_="results-count")
    if count_span:
        match = re.search(r"of\s+([\d,]+)", count_span.get_text())
        if match:
            total = int(match.group(1).replace(",", ""))

    # Extract judgement articles
    judgements = []
    articles = soup.find_all("article", class_="result")
    for article in articles:
        # Get the title link — can be in h4.result_title > a
        title_tag = article.find("h4", class_="result_title")
        link_tag = title_tag.find("a") if title_tag else None

        if not link_tag:
            continue

        href = link_tag.get("href", "")
        title = link_tag.get_text(strip=True)

        # Extract doc_id from href like /docfragment/117249167/ or /doc/117249167/
        doc_id_match = re.search(r"/(?:doc|docfragment)/(\d+)/", href)
        doc_id = doc_id_match.group(1) if doc_id_match else None

        if not doc_id:
            continue

        # Extract court name
        court_span = article.find("span", class_="docsource")
        court_name = court_span.get_text(strip=True) if court_span else "Unknown"

        # Extract date from title (usually "on DD Month, YYYY")
        date_match = re.search(r"on\s+(.+)$", title)
        date_str = date_match.group(1) if date_match else ""

        judgements.append({
            "id": doc_id,
            "title": title,
            "court": court_name,
            "date": date_str,
            "url": f"{BASE_URL}/doc/{doc_id}/",
        })

    logger.info(f"Found {len(judgements)} judgements on page {page} (total: {total})")
    return {"total": total, "page": page, "judgements": judgements}


def fetch_judgement_count(year: int, month_name: str, court: str = "") -> int:
    """Fetch only the total result count for a given year/month/court."""
    url = build_search_url(year, month_name, court, 0)
    logger.info(f"Fetching count: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch count: {e}")
        return 0

    soup = BeautifulSoup(response.text, "lxml")
    count_span = soup.find("span", class_="results-count")
    if count_span:
        match = re.search(r"of\s+([\d,]+)", count_span.get_text())
        if match:
            return int(match.group(1).replace(",", ""))
    return 0


def fetch_all_judgements(
    year: int,
    month_name: str,
    court: str = "",
    max_count: int = 50,
    delay_seconds: float = 1.5,
    progress_callback=None,
) -> list[dict]:
    """
    Fetch ALL judgements for a given month, paginating through results.

    Args:
        year: e.g. 2025
        month_name: e.g. "January"
        court: court name string (see COURT_TYPES)
        max_count: maximum number of judgements to return
        delay_seconds: seconds to wait between requests (to avoid rate limiting)
        progress_callback: optional callable(fetched, total) for progress updates

    Returns:
        List of judgement dicts
    """
    all_judgements = []
    page = 0

    while len(all_judgements) < max_count:
        result = fetch_judgement_list(year, month_name, court, page)

        if result.get("error"):
            logger.error(f"Error on page {page}: {result['error']}")
            break

        judgements = result["judgements"]
        if not judgements:
            logger.info("No more results, done paginating.")
            break

        total = result["total"]
        all_judgements.extend(judgements)

        if progress_callback:
            progress_callback(len(all_judgements), min(total, max_count))

        logger.info(f"Accumulated {len(all_judgements)} / {min(total, max_count)} judgements")

        if len(all_judgements) >= max_count:
            break

        page += 1
        time.sleep(delay_seconds)

    return all_judgements[:max_count]


def fetch_judgement_html(doc_id: str) -> Optional[str]:
    """
    Fetch the full HTML content of a judgement page.

    Returns:
        Cleaned HTML string, or None on failure.
    """
    url = f"{BASE_URL}/doc/{doc_id}/"
    logger.info(f"Fetching document {doc_id}: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch document {doc_id}: {e}")
        return None

    return response.text


def extract_judgement_text(html: str) -> str:
    """Extract clean text content from judgement HTML."""
    soup = BeautifulSoup(html, "lxml")

    # Remove script and style tags
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    # Try to find the main judgement content div
    content_div = (
        soup.find("div", class_="judgments")
        or soup.find("div", id="main-content")
        or soup.find("main")
        or soup.find("body")
    )

    if content_div:
        return content_div.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)


# Explicit path to wkhtmltopdf on Windows (handles cases where it's not in PATH)
WKHTMLTOPDF_PATHS = [
    r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
    r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
]


def _get_pdfkit_config():
    """Return a pdfkit configuration with the correct wkhtmltopdf path."""
    import pdfkit
    import shutil

    # First try system PATH
    if shutil.which("wkhtmltopdf"):
        return pdfkit.configuration()

    # Then try known Windows install locations
    for path in WKHTMLTOPDF_PATHS:
        if os.path.isfile(path):
            logger.info(f"Found wkhtmltopdf at: {path}")
            return pdfkit.configuration(wkhtmltopdf=path)

    return None  # Not found


def _build_clean_pdf_html(page_html: str) -> str:
    """
    Given the full page HTML of an indiankanoon.org judgement, return a clean,
    self-contained HTML document suitable for wkhtmltopdf conversion.

    What this does:
      1. Extracts only <div class="judgments"> — excludes AI widgets, nav, banners.
      2. Removes <div class="covers"> (the "[Cites X, Cited by Y]" bar at the top).
      3. Removes any other sibling elements before <h3 class="docsource_main">
         (the court name heading like "Supreme Court of India").
      4. Strips all remaining external <script>, <link>, <style> tags.
      5. Injects clean typographic CSS so the PDF looks professional.

    Result: PDF starts cleanly from the court name with no top clutter.
    """
    soup = BeautifulSoup(page_html, "lxml")

    # ── 1. Extract the main judgement container ──────────────────────────
    container = (
        soup.find("div", class_="judgments") or
        soup.find("div", id="judgments") or
        soup.find("div", id="main-content") or
        soup.find("main") or
        soup.find("body")
    )
    if container is None:
        container = soup

    # ── 2. Find where the actual judgement content starts ────────────────
    # indiankanoon uses <h3 class="docsource_main"> for court name.
    # Fallback: first element whose text matches a known court pattern.
    start_el = container.find("h3", class_="docsource_main")

    if start_el is None:
        # Generic fallback: find first short line containing a court name
        _court_re = re.compile(
            r"\b(Supreme Court|High Court|District Court|Sessions Court|"
            r"Tribunal|National Commission|Consumer Forum|Civil Court|"
            r"Family Court|Lok Adalat|Magistrate|Motor Accident Claims)\b",
            re.IGNORECASE,
        )
        for tag in container.find_all(["h1", "h2", "h3", "h4", "center", "p", "b"]):
            txt = tag.get_text(strip=True)
            if _court_re.search(txt) and len(txt) < 150:
                start_el = tag
                break

    # ── 3. Remove everything before the court name heading ───────────────
    if start_el is not None:
        # Walk up to the direct child of `container`
        target = start_el
        while target.parent is not container and target.parent is not None:
            target = target.parent

        # Remove all preceding siblings (covers div, any other pre-content)
        for sib in list(target.previous_siblings):
            if hasattr(sib, "decompose"):
                sib.decompose()

    # ── 4. Strip ALL external resource references ─────────────────────────
    # Removes <script>, <link>, <style>, <iframe> so wkhtmltopdf has nothing
    # external to fetch — eliminates ProtocolUnknownError completely.
    for tag in container.find_all(["script", "link", "style", "iframe"]):
        tag.decompose()

    # Remove external src attributes from any remaining tags
    for tag in container.find_all(True):
        for attr in ["onclick", "onload", "onmouseover", "onchange", "onfocus"]:
            if tag.has_attr(attr):
                del tag[attr]

    # ── 5. Build clean standalone HTML with embedded CSS ─────────────────
    content_html = container.decode_contents()  # inner HTML, no outer wrapper tag

    clean_css = """
        /* ── Page setup ────────────────────────────────────────────────── */
        @page {
            size: A4;
            margin: 72pt 72pt 72pt 72pt;   /* 1 inch on all sides */

            /* Subtle page number in footer */
            @bottom-center {
                content: counter(page) " / " counter(pages);
                font-family: "Times New Roman", Times, serif;
                font-size: 9pt;
                color: #888;
            }
        }

        * { box-sizing: border-box; }

        /* ── Body: matches site's .judgments font ───────────────────────── */
        body {
            font-family: "Times New Roman", "PT Serif", Georgia, Times, serif;
            font-size: 11pt;
            line-height: 1.7;
            color: #111;
            margin: 0;
            padding: 0;
        }

        /* ── Header section: court, title, author, bench ───────────────── */
        h3.docsource_main {
            font-size: 13pt;
            font-weight: bold;
            text-align: center;
            margin: 0 0 6pt 0;
            padding-bottom: 4pt;
        }
        h2.doc_title {
            font-size: 12pt;
            font-weight: bold;
            text-align: center;
            margin: 0 0 4pt 0;
        }
        h3.doc_citations {
            font-size: 10pt;
            font-weight: normal;
            text-align: left;
            margin: 6pt 0 2pt 0;
            color: #333;
        }
        h3.doc_author, h3.doc_bench {
            font-size: 10.5pt;
            font-weight: normal;
            text-align: left;
            margin: 2pt 0;
        }

        /* Horizontal rule between header and body */
        h3.doc_bench + * {
            margin-top: 10pt;
        }

        /* ── PRE BLOCKS: MUST be monospace ─────────────────────────────────
           Judgment body uses spaces for column alignment (party names,
           case nos, indented quotes). Proportional fonts break this.
        */
        pre {
            font-family: "Courier New", Courier, monospace;
            font-size: 10pt;
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.6;   /* a little more breathing room between lines */
            margin: 8pt 0;
            padding: 0;
        }

        /* ── Flowing text ───────────────────────────────────────────────── */
        p {
            margin: 6pt 0;
            text-align: justify;
            line-height: 1.7;
        }

        blockquote {
            margin: 8pt 0 8pt 22pt;
            padding: 4pt 0 4pt 10pt;
            border-left: 2px solid #aaa;
            color: #333;
        }

        /* ── Misc ───────────────────────────────────────────────────────── */
        a  { color: #111; text-decoration: none; }
        hr { border: none; border-top: 1px solid #ddd; margin: 12pt 0; }

        table { border-collapse: collapse; width: 100%; margin: 8pt 0; }
        td, th {
            padding: 5pt 8pt;
            border: 1px solid #ccc;
            font-size: 10pt;
            line-height: 1.5;
        }

        /* ── Hide site UI widgets that may slip through ─────────────────── */
        .hidden_text, .ad_main, #divinstall,
        [class*="widget"], [class*="upgrade"], [class*="premium"],
        [class*="banner"], [class*="tooltip"] {
            display: none !important;
        }
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>{clean_css}</style>
</head>
<body>
{content_html}
</body>
</html>"""


def url_to_pdf(doc_url: str, output_path: str) -> bool:
    """
    Download a judgement as a clean PDF.

    Pipeline:
      1. Fetch the live page HTML via requests.
      2. Extract only the judgement content (div.judgments).
      3. Remove everything before the court name heading — widgets, banners,
         the citation bar [Cites X, Cited by Y] — are all gone.
      4. Write clean self-contained HTML to a temp file.
      5. Convert to PDF with wkhtmltopdf via pdfkit.from_file().
         (No external resource references → no ProtocolUnknownError.)

    Returns:
        True if successful, False otherwise.
    """
    import tempfile

    try:
        
        import pdfkit

        config = _get_pdfkit_config()
        if config is None:
            logger.warning("wkhtmltopdf not found. Falling back to HTML.")
            return False

        # Step 1: Fetch page HTML
        logger.info(f"Fetching HTML for PDF: {doc_url}")
        response = requests.get(doc_url, headers=HEADERS, timeout=30)
        response.raise_for_status()

        # Step 2-5: Build clean HTML starting from court name
        clean_html = _build_clean_pdf_html(response.text)

        # Write to temp file (wkhtmltopdf reads file:// — no external fetches)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", encoding="utf-8", delete=False
        ) as tmp:
            tmp.write(clean_html)
            tmp_path = tmp.name

        try:
            options = {
                "page-size": "A4",
                "encoding": "UTF-8",
                "no-outline": None,
                "quiet": "",
            }
            pdfkit.from_file(tmp_path, output_path, options=options, configuration=config)
            logger.info(f"PDF saved: {output_path}")
            return True

        finally:
            # Always clean up the temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except ImportError:
        logger.warning("pdfkit not installed. Falling back to HTML.")
        return False
    except Exception as e:
        logger.error(f"PDF conversion failed for {doc_url}: {e}")
        return False


def save_as_html(html: str, output_path: str) -> bool:
    """Fallback: save HTML directly if PDF conversion fails."""
    html_path = output_path.replace(".pdf", ".html")
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML saved: {html_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save HTML: {e}")
        return False


def download_judgement(
    doc_id: str,
    title: str,
    output_dir: str,
    use_pdf: bool = True,
    delay_seconds: float = 1.0,
) -> dict:
    """
    Download a single judgement and save as PDF (or HTML fallback).

    Returns:
        {"success": bool, "path": str, "error": str}
    """
    # Sanitize filename from title
    safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)
    safe_title = safe_title[:120]  # Limit filename length
    filename = f"{doc_id}_{safe_title}"

    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.join(output_dir, f"{filename}.pdf")
    html_path = os.path.join(output_dir, f"{filename}.html")

    # Robust duplicate check by doc_id
    prefix = f"{doc_id}_"
    try:
        for existing_file in os.listdir(output_dir):
            if existing_file.startswith(prefix):
                existing_path = os.path.join(output_dir, existing_file)
                logger.info(f"Already exists (matched ID): {existing_path}")
                return {"success": True, "path": existing_path, "skipped": True}
    except Exception as e:
        logger.warning(f"Error checking duplicates: {e}")

    doc_url = f"{BASE_URL}/doc/{doc_id}/"

    # Try PDF via URL (wkhtmltopdf fetches the page itself — most reliable)
    if use_pdf:
        logger.info(f"Generating PDF from URL: {doc_url}")
        success = url_to_pdf(doc_url, pdf_path)
        if success:
            time.sleep(delay_seconds)
            return {"success": True, "path": pdf_path}
        logger.warning(f"PDF failed for {doc_id}, falling back to HTML save.")

    # Fallback: fetch HTML and save as .html file
    html = fetch_judgement_html(doc_id)
    if not html:
        return {"success": False, "path": "", "error": "Failed to fetch content"}

    time.sleep(delay_seconds)
    success = save_as_html(html, html_path)
    if success:
        return {"success": True, "path": html_path}

    return {"success": False, "path": "", "error": "All save methods failed"}
