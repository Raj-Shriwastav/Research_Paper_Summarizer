"""
PDF Parser — Extracts structured content from research paper PDFs.

Uses PyMuPDF4LLM (CPU-only, no GPU needed) to convert PDFs to
structured Markdown with section headers, tables, and page numbers preserved.
"""

import os
import logging
import tempfile
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ParsedSection:
    """A section of a parsed paper."""
    title: str
    content: str
    page_start: int = 0
    page_end: int = 0


@dataclass
class ParsedPaper:
    """Complete parsed paper with structured content."""
    title: str
    full_markdown: str
    sections: List[ParsedSection] = field(default_factory=list)
    total_pages: int = 0
    # Raw chunks for verification (each chunk maps to a page)
    page_chunks: Dict[int, str] = field(default_factory=dict)


def download_pdf(pdf_url: str, cache_dir: str) -> Optional[str]:
    """
    Download a PDF from a URL to the local cache directory.
    Returns the local file path, or None on failure.
    """
    try:
        # Create a filename from the URL
        filename = pdf_url.split("/")[-1]
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        filepath = os.path.join(cache_dir, filename)

        # Skip if already cached
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            logger.info(f"Using cached PDF: {filepath}")
            return filepath

        logger.info(f"Downloading PDF: {pdf_url}")
        resp = requests.get(
            pdf_url,
            timeout=60,
            headers={
                "User-Agent": "ResearchPaperSummarizer/1.0 "
                              "(contact: raazof5@gmail.com)"
            },
        )
        resp.raise_for_status()

        # Verify it's actually a PDF
        if not resp.content[:5] == b"%PDF-":
            logger.warning(f"Downloaded file is not a valid PDF: {pdf_url}")
            from backend.utils import log_failure
            log_failure(
                error_type="Invalid PDF Header",
                message=f"The downloaded file from {pdf_url} did not start with %PDF- header.",
                details=f"First 100 bytes: {resp.content[:100]!r}"
            )
            return None

        with open(filepath, "wb") as f:
            f.write(resp.content)

        logger.info(f"Downloaded PDF: {filepath} ({len(resp.content)} bytes)")
        return filepath

    except requests.RequestException as e:
        logger.error(f"Failed to download PDF from {pdf_url}: {e}")
        from backend.utils import log_failure
        log_failure(
            error_type="PDF Download Exception",
            message=f"Requests exception occurred while downloading PDF from {pdf_url}",
            details=str(e)
        )
        return None
    except IOError as e:
        logger.error(f"Failed to save PDF: {e}")
        from backend.utils import log_failure
        log_failure(
            error_type="PDF IO Exception",
            message=f"IO exception occurred while saving PDF downloaded from {pdf_url}",
            details=str(e)
        )
        return None


def parse_pdf(pdf_path: str, paper_title: str = "") -> Optional[ParsedPaper]:
    """
    Parse a research paper PDF into structured Markdown.
    
    Uses PyMuPDF4LLM for layout-aware extraction that preserves
    section headers, tables, and reading order.
    """
    try:
        import pymupdf4llm
        import pymupdf
    except ImportError:
        logger.error(
            "pymupdf4llm not installed. Run: pip install pymupdf4llm"
        )
        return None

    try:
        logger.info(f"Parsing PDF: {pdf_path}")

        # Get total page count
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        doc.close()

        # Extract to Markdown with page-level chunking
        md_chunks = pymupdf4llm.to_markdown(
            pdf_path,
            page_chunks=True,  # Get per-page chunks
        )

        if not md_chunks:
            logger.warning(f"No content extracted from {pdf_path}")
            return None

        # Build page-level index
        page_chunks = {}
        full_parts = []
        for i, chunk in enumerate(md_chunks):
            if isinstance(chunk, dict):
                page_num = chunk.get("metadata", {}).get("page", i + 1)
                text = chunk.get("text", "")
            else:
                page_num = i + 1
                text = str(chunk)
            
            page_chunks[page_num] = text
            full_parts.append(text)

        full_markdown = "\n\n".join(full_parts)

        # Extract sections from the markdown
        sections = _extract_sections(full_markdown, page_chunks)

        paper = ParsedPaper(
            title=paper_title or _extract_title(full_markdown),
            full_markdown=full_markdown,
            sections=sections,
            total_pages=total_pages,
            page_chunks=page_chunks,
        )

        logger.info(
            f"Parsed {total_pages} pages, {len(sections)} sections, "
            f"{len(full_markdown)} chars"
        )
        return paper

    except Exception as e:
        logger.error(f"Failed to parse PDF {pdf_path}: {e}")
        from backend.utils import log_failure
        log_failure(
            error_type="PDF Parser Exception",
            message=f"An exception occurred in PyMuPDF4LLM while parsing {pdf_path}",
            details=str(e)
        )
        return None


def _extract_title(markdown: str) -> str:
    """Extract the paper title from the first heading in the markdown."""
    for line in markdown.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("## "):
            return line[3:].strip()
        # If the first non-empty line looks like a title
        if line and not line.startswith("-") and len(line) < 200:
            return line
    return "Untitled Paper"


def _extract_sections(markdown: str,
                       page_chunks: Dict[int, str]) -> List[ParsedSection]:
    """
    Split markdown into sections based on heading markers.
    Tracks which pages each section spans.
    """
    sections = []
    current_title = "Introduction"
    current_content_lines = []
    
    for line in markdown.split("\n"):
        stripped = line.strip()
        
        # Detect section headers (## or ### level)
        if stripped.startswith("## ") or stripped.startswith("# "):
            # Save previous section
            if current_content_lines:
                content = "\n".join(current_content_lines).strip()
                if content:
                    page_range = _find_page_range(content, page_chunks)
                    sections.append(ParsedSection(
                        title=current_title,
                        content=content,
                        page_start=page_range[0],
                        page_end=page_range[1],
                    ))
            
            # Start new section
            current_title = stripped.lstrip("#").strip()
            current_content_lines = []
        else:
            current_content_lines.append(line)

    # Don't forget the last section
    if current_content_lines:
        content = "\n".join(current_content_lines).strip()
        if content:
            page_range = _find_page_range(content, page_chunks)
            sections.append(ParsedSection(
                title=current_title,
                content=content,
                page_start=page_range[0],
                page_end=page_range[1],
            ))

    # If no sections were found, treat the whole document as one section
    if not sections and markdown.strip():
        sections.append(ParsedSection(
            title="Full Paper",
            content=markdown.strip(),
            page_start=1,
            page_end=max(page_chunks.keys()) if page_chunks else 1,
        ))

    return sections


def _find_page_range(content: str,
                      page_chunks: Dict[int, str]) -> tuple:
    """Find which pages a section's content spans."""
    if not page_chunks:
        return (1, 1)

    # Check first 100 chars of content against each page
    snippet = content[:100]
    start_page = 1
    end_page = 1

    for page_num, page_text in sorted(page_chunks.items()):
        if snippet[:50] in page_text:
            start_page = page_num
            break

    # Check last 100 chars for end page
    end_snippet = content[-100:]
    for page_num, page_text in sorted(page_chunks.items(), reverse=True):
        if end_snippet[-50:] in page_text:
            end_page = page_num
            break

    if end_page < start_page:
        end_page = start_page

    return (start_page, end_page)


def cleanup_cached_pdf(pdf_path: str):
    """Remove a cached PDF after processing."""
    try:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.debug(f"Cleaned up cached PDF: {pdf_path}")
    except OSError as e:
        logger.warning(f"Failed to clean up {pdf_path}: {e}")
