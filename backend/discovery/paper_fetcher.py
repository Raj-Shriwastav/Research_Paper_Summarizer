"""
Paper Fetcher — Discovers trending research papers from arXiv.

Queries arXiv API, deduplicates results, and ranks papers by
citation velocity + recency to find the top 3-5 papers of the day.
"""

import re
import time
import logging
import hashlib
import requests
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from dateutil import parser as dateparser

from backend.config import PaperAPIConfig
from backend.discovery.topic_manager import TopicQuery

logger = logging.getLogger(__name__)


@dataclass
class Paper:
    """Represents a discovered research paper."""
    title: str
    authors: List[str]
    abstract: str
    published_date: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pdf_url: Optional[str] = None
    source: str = ""  # "arxiv"
    citation_count: int = 0
    url: Optional[str] = None  # Link to the paper page
    # Computed relevance score for ranking
    relevance_score: float = 0.0

    @property
    def unique_id(self) -> str:
        """Generate a unique identifier for deduplication."""
        if self.doi:
            return f"doi:{self.doi}"
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id}"
        # Fallback: hash of normalized title
        normalized = re.sub(r"\s+", " ", self.title.lower().strip())
        return f"title:{hashlib.md5(normalized.encode()).hexdigest()}"


class ArxivFetcher:
    """Fetch papers from arXiv API (no API key needed!)."""

    ARXIV_ENDPOINTS = [
        "https://export.arxiv.org/api/query",
        "https://arxiv.org/api/query"
    ]
    # OAI-PMH bulk metadata endpoint — rate-limit proof, no WAF blocking
    OAI_ENDPOINT = "https://export.arxiv.org/oai2"
    # arXiv rate limit: 1 request per 3 seconds
    MIN_REQUEST_INTERVAL = 3.0

    def __init__(self, config: PaperAPIConfig):
        self.config = config
        self._last_request_time = 0.0

    def _wait_for_rate_limit(self):
        """Respect arXiv's rate limit of 1 request per 3 seconds."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def search(self, topic: TopicQuery, lookback_days: int = 7,
               max_results: int = 20) -> List[Paper]:
        """
        Search arXiv for recent papers in topic categories.

        Strategy:
          1. Try OAI-PMH bulk harvest (rate-limit proof, served from static XML).
          2. Fall back to the standard Atom API only if OAI returns nothing.
        """
        # ── 1. OAI-PMH Primary Path ──────────────────────────────────────
        try:
            logger.info(f"Attempting OAI-PMH harvest for topic '{topic.name}'...")
            oai_papers = self._harvest_via_oai(topic, lookback_days)
            if oai_papers:
                logger.info(
                    f"OAI-PMH harvest successful: {len(oai_papers)} matching papers."
                )
                return oai_papers[:max_results]
            logger.info(
                "OAI-PMH returned 0 matching papers (arXiv may not have published "
                "new papers yet today). Falling back to standard API..."
            )
        except Exception as e:
            logger.warning(
                f"OAI-PMH harvest failed ({e}). Falling back to standard API..."
            )

        # ── 2. Standard API Fallback ─────────────────────────────────────
        papers = []

        # Build arXiv search query
        query_parts = []

        # Add category filters
        if topic.arxiv_categories:
            cat_query = " OR ".join(
                f"cat:{cat}" for cat in topic.arxiv_categories
            )
            query_parts.append(f"({cat_query})")

        # Add keyword search (use top 2 keywords for focused results)
        if topic.keywords:
            kw_query = " OR ".join(
                f'all:"{kw}"' for kw in topic.keywords[:2]
            )
            query_parts.append(f"({kw_query})")

        search_query = " AND ".join(query_parts) if query_parts else topic.name

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        endpoints = self.ARXIV_ENDPOINTS
        
        for attempt in range(4):
            endpoint = endpoints[attempt % len(endpoints)]
            try:
                self._wait_for_rate_limit()
                logger.info(f"Querying arXiv ({endpoint}): {search_query[:100]}... (Attempt {attempt+1}/4)")
                resp = requests.get(
                    endpoint,
                    params=params,
                    timeout=30,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    },
                )
                
                if resp.status_code == 429:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"arXiv rate limit (429) hit at {endpoint}. Trying alternative in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                    
                resp.raise_for_status()

                # Parse Atom XML response
                papers = self._parse_atom_response(resp.text, lookback_days)
                logger.info(f"arXiv returned {len(papers)} papers")
                break

            except requests.RequestException as e:
                if attempt == 3:
                    logger.error(f"arXiv API error after 4 attempts: {e}")
                    from backend.utils import log_failure
                    log_failure(
                        error_type="arXiv API Query Error",
                        message=f"RequestException occurred while querying arXiv for search query: '{search_query[:100]}...'",
                        details=str(e)
                    )
                else:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"arXiv connection/request error at {endpoint}: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)

        return papers

    def _harvest_via_oai(
        self, topic: TopicQuery, lookback_days: int
    ) -> List[Paper]:
        """
        Harvest recent arXiv metadata via OAI-PMH and filter locally by topic.
        OAI-PMH serves pre-generated static XML — it is never rate-limited by
        Cloudflare/WAF and consistently returns 200 OK from any IP address.
        """
        from_date = (
            datetime.now() - timedelta(days=lookback_days)
        ).strftime("%Y-%m-%d")

        # arXiv categories: map topic cats to OAI set names.
        # For simplicity we harvest the whole 'cs' set and filter locally.
        params = {
            "verb": "ListRecords",
            "metadataPrefix": "arXiv",
            "set": "cs",
            "from": from_date,
        }

        ns = {
            "oai": "http://www.openarchives.org/OAI/2.0/",
            "arxiv": "http://arxiv.org/OAI/arXiv/",
        }

        keywords_lower = [kw.lower() for kw in topic.keywords]
        topic_cats = set(topic.arxiv_categories)
        papers: List[Paper] = []

        self._wait_for_rate_limit()
        try:
            resp = requests.get(
                self.OAI_ENDPOINT,
                params=params,
                timeout=30,
                headers={
                    "User-Agent": (
                        "ResearchPaperSummarizer/1.0 "
                        "(OAI-PMH harvester; contact: alokprasadshriwastava@gmail.com)"
                    )
                },
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
        except Exception as e:
            logger.error(f"OAI-PMH XML parse or request error: {e}")
            return []

        records = root.findall(".//oai:record", ns)
        logger.info(f"OAI-PMH: received {len(records)} raw records from arXiv.")

        for record in records:
            if len(papers) >= 100:
                break  # Stop when we reach 100 papers as requested by user

            metadata = record.find(".//arxiv:arXiv", ns)
            if metadata is None:
                continue

            title_el = metadata.find("arxiv:title", ns)
            abstract_el = metadata.find("arxiv:abstract", ns)
            id_el = metadata.find("arxiv:id", ns)
            created_el = metadata.find("arxiv:created", ns)
            categories_el = metadata.find("arxiv:categories", ns)

            title = (
                title_el.text.strip().replace("\n", " ")
                if title_el is not None else ""
            )
            abstract = (
                abstract_el.text.strip().replace("\n", " ")
                if abstract_el is not None else ""
            )
            arxiv_id = id_el.text.strip() if id_el is not None else ""

            if not arxiv_id or not title:
                continue

            # Local relevance filtering — keyword match OR category match
            text_blob = f"{title} {abstract}".lower()
            keyword_hit = any(kw in text_blob for kw in keywords_lower)

            cat_hit = False
            if topic_cats and categories_el is not None:
                record_cats = set(categories_el.text.strip().split())
                cat_hit = bool(topic_cats & record_cats)

            if not (keyword_hit or cat_hit):
                continue

            # Parse authors
            authors: List[str] = []
            authors_el = metadata.find("arxiv:authors", ns)
            if authors_el is not None:
                for author_el in authors_el.findall("arxiv:author", ns):
                    kn_el = author_el.find("arxiv:keyname", ns)
                    fn_el = author_el.find("arxiv:forenames", ns)
                    fn = fn_el.text.strip() if fn_el is not None else ""
                    kn = kn_el.text.strip() if kn_el is not None else ""
                    authors.append(f"{fn} {kn}".strip())

            published_str = (
                created_el.text.strip() if created_el is not None else None
            )

            papers.append(Paper(
                title=title,
                authors=authors[:10],
                abstract=abstract,
                published_date=published_str,
                arxiv_id=arxiv_id,
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                source="arxiv_oai",
                citation_count=0,
                url=f"https://arxiv.org/abs/{arxiv_id}",
            ))

        return papers

    def _parse_atom_response(self, xml_text: str,
                              lookback_days: int) -> List[Paper]:
        """Parse arXiv Atom XML response into Paper objects."""
        papers = []
        ns = {"atom": "http://www.w3.org/2005/Atom",
              "arxiv": "http://arxiv.org/schemas/atom"}

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv XML: {e}")
            return []

        cutoff_date = datetime.now() - timedelta(days=lookback_days)

        for entry in root.findall("atom:entry", ns):
            try:
                paper = self._parse_entry(entry, ns, cutoff_date)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.warning(f"Failed to parse arXiv entry: {e}")
                continue

        return papers

    def _parse_entry(self, entry, ns: dict,
                      cutoff_date: datetime) -> Optional[Paper]:
        """Parse a single arXiv Atom entry."""
        # Title
        title_el = entry.find("atom:title", ns)
        title = title_el.text.strip().replace("\n", " ") if title_el is not None else ""
        if not title:
            return None

        # Published date — filter old papers
        published_el = entry.find("atom:published", ns)
        if published_el is not None:
            pub_date = dateparser.parse(published_el.text)
            if pub_date and pub_date.replace(tzinfo=None) < cutoff_date:
                return None
            published_str = pub_date.strftime("%Y-%m-%d") if pub_date else None
        else:
            published_str = None

        # Authors
        authors = []
        for author_el in entry.findall("atom:author", ns):
            name_el = author_el.find("atom:name", ns)
            if name_el is not None:
                authors.append(name_el.text.strip())

        # Abstract
        summary_el = entry.find("atom:summary", ns)
        abstract = summary_el.text.strip().replace("\n", " ") if summary_el is not None else ""

        # arXiv ID and PDF URL
        arxiv_id = None
        pdf_url = None
        paper_url = None
        for link_el in entry.findall("atom:link", ns):
            href = link_el.get("href", "")
            link_type = link_el.get("type", "")
            link_title = link_el.get("title", "")

            if link_title == "pdf" or link_type == "application/pdf":
                pdf_url = href
            elif link_el.get("rel") == "alternate":
                paper_url = href

        # Extract arXiv ID from the entry ID
        id_el = entry.find("atom:id", ns)
        if id_el is not None:
            # ID format: http://arxiv.org/abs/2401.12345v1
            match = re.search(r"arxiv\.org/abs/([\d.]+)", id_el.text)
            if match:
                arxiv_id = match.group(1)
                if not pdf_url:
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                if not paper_url:
                    paper_url = f"https://arxiv.org/abs/{arxiv_id}"

        # DOI
        doi_el = entry.find("arxiv:doi", ns)
        doi = doi_el.text.strip() if doi_el is not None else None

        return Paper(
            title=title,
            authors=authors[:10],
            abstract=abstract,
            published_date=published_str,
            doi=doi,
            arxiv_id=arxiv_id,
            pdf_url=pdf_url,
            source="arxiv",
            citation_count=0,  # arXiv doesn't provide citation counts
            url=paper_url,
        )


def deduplicate_papers(papers: List[Paper]) -> List[Paper]:
    """Remove duplicate papers across sources using unique IDs."""
    seen = {}
    for paper in papers:
        uid = paper.unique_id
        if uid not in seen:
            seen[uid] = paper
        else:
            # Keep the one with more metadata (higher citation count, has PDF, etc.)
            existing = seen[uid]
            if paper.citation_count > existing.citation_count:
                seen[uid] = paper
            elif paper.pdf_url and not existing.pdf_url:
                seen[uid] = paper
    return list(seen.values())


def rank_papers(papers: List[Paper], lookback_days: int = 7) -> List[Paper]:
    """
    Rank papers by a combined score of citation velocity and recency.
    Papers with high citations gained recently rank highest.
    """
    now = datetime.now()

    for paper in papers:
        score = 0.0

        # Citation score (log scale to avoid mega-cited papers dominating)
        if paper.citation_count > 0:
            import math
            score += math.log1p(paper.citation_count) * 10

        # Recency score — newer papers get a boost
        if paper.published_date:
            try:
                pub = dateparser.parse(paper.published_date)
                if pub:
                    days_old = (now - pub.replace(tzinfo=None)).days
                    recency_boost = max(0, lookback_days - days_old) / lookback_days
                    score += recency_boost * 20
            except (ValueError, TypeError):
                pass

        # Bonus: has PDF available (more useful)
        if paper.pdf_url:
            score += 5

        # Bonus: has abstract (needed for summarization)
        if paper.abstract and len(paper.abstract) > 100:
            score += 5

        paper.relevance_score = score

    # Sort by score descending
    papers.sort(key=lambda p: p.relevance_score, reverse=True)
    return papers


def fetch_papers(config: PaperAPIConfig, topic: TopicQuery,
                 max_papers: int = 5) -> List[Paper]:
    """
    Main entry point: fetch, deduplicate, and rank papers from arXiv.
    Returns the top N papers ready for processing.
    """
    # Fetch from arXiv
    arxiv_fetcher = ArxivFetcher(config)
    arxiv_papers = arxiv_fetcher.search(
        topic, lookback_days=config.lookback_days, max_results=20
    )

    # Deduplicate across sources
    unique_papers = deduplicate_papers(arxiv_papers)
    logger.info(
        f"Total: {len(arxiv_papers)} papers, "
        f"After dedup: {len(unique_papers)} papers"
    )

    # Rank and return top N
    ranked = rank_papers(unique_papers, lookback_days=config.lookback_days)

    # Filter to papers that have a PDF URL (required for summarization)
    with_pdf = [p for p in ranked if p.pdf_url]
    logger.info(f"Papers with PDF available: {len(with_pdf)}")

    return with_pdf[:max_papers]
