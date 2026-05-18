"""
Summarizer Engine — Generates structured A/B/C format summaries from parsed papers.

Pipeline:
1. Extract all distinct problems + novel ideas from the paper
2. For each item, generate the A/B/C/ELI10/ELI-College summary
3. Find relevant links per section
4. Generate combined summary + key takeaway
"""

import logging
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from backend.summarization.llm_client import LLMClient
from backend.summarization.prompts import (
    EXTRACT_PROBLEMS_PROMPT,
    SUMMARIZE_ITEM_PROMPT,
    COMBINED_SUMMARY_PROMPT,
    FIND_LINKS_PROMPT,
)
from backend.summarization.director import DirectorAgent
from backend.parsing.pdf_parser import ParsedPaper

logger = logging.getLogger(__name__)


@dataclass
class SummaryItem:
    """A single problem/novel-idea summary in A/B/C format."""
    item_type: str  # "problem" or "novel_idea"
    title: str
    issue_text: str  # Section A
    solution_text: str  # Section B
    eli10_text: str  # Section C
    eli_college_text: str  # Section C2
    relevant_links: List[str] = field(default_factory=list)
    source_references: Dict[str, Any] = field(default_factory=dict)
    raw_markdown: str = ""  # Full formatted markdown for this item


@dataclass
class PaperSummary:
    """Complete summary of a research paper."""
    paper_title: str
    authors: List[str]
    paper_url: str
    items: List[SummaryItem] = field(default_factory=list)
    combined_summary: str = ""
    key_takeaway: str = ""
    useful_links: str = ""
    full_markdown: str = ""  # Complete formatted output


class Summarizer:
    """Main summarization engine."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.director = DirectorAgent()

    def summarize_paper(
        self,
        parsed_paper: ParsedPaper,
        authors: List[str] = None,
        paper_url: str = "",
        num_papers: int = 1,
        paper_index: int = 0,
    ) -> Optional[PaperSummary]:
        """
        Full summarization pipeline for a single paper.
        
        Steps:
        1. Extract problems and novel ideas
        2. Generate A/B/C summary for each
        3. Generate combined summary + key takeaway
        """
        if not parsed_paper.full_markdown.strip():
            logger.warning("Empty paper content, skipping summarization")
            return None

        authors = authors or []
        
        # Truncate paper content if it's very long (LLM context limits)
        paper_content = parsed_paper.full_markdown
        if len(paper_content) > 80000:
            # Keep first and last sections, truncate middle
            paper_content = paper_content[:40000] + "\n\n[...middle sections truncated...]\n\n" + paper_content[-40000:]
            logger.info("Paper content truncated for LLM context limits")

        # ── Step 1: Extract problems and novel ideas ─────────────────
        logger.info(f"Step 1: Extracting problems/ideas from '{parsed_paper.title}'")
        extracted = self._extract_items(paper_content)
        
        if not extracted:
            logger.warning("Failed to extract structured items via JSON. Falling back to treating the whole paper as a single item.")
            extracted = {
                "paper_title": parsed_paper.title,
                "items": [{
                    "type": "novel_idea",
                    "title": "Main Contribution",
                    "key_details": parsed_paper.sections[0].content[:1500] if parsed_paper.sections else paper_content[:1500]
                }]
            }

        paper_title = extracted.get("paper_title", parsed_paper.title)
        raw_items = extracted.get("items", [])
        logger.info(f"Extracted {len(raw_items)} items from paper")

        if not raw_items:
            # Fallback: treat the whole paper as a single item
            raw_items = [{
                "type": "novel_idea",
                "title": paper_title,
                "key_details": parsed_paper.sections[0].content[:500] if parsed_paper.sections else paper_content[:500],
            }]

        # ── Step 2: Get length constraints from Director Agent ───────
        constraints = self.director.calculate_paper_constraints(
            num_papers=num_papers,
            paper_index=paper_index,
        )
        logger.info(
            f"Director: paper {paper_index+1}/{num_papers} — "
            f"target {constraints.target_words} words"
        )

        # ── Step 3: Generate A/B/C summary for each item ─────────────
        summary_items = []
        
        # Divide target words across the extracted items so the TOTAL per paper matches the budget!
        num_items = max(1, len(raw_items))
        item_target_words = max(150, constraints.target_words // num_items)
        
        for i, item in enumerate(raw_items):
            logger.info(
                f"Step 3: Summarizing item {i+1}/{len(raw_items)}: "
                f"{item.get('title', 'Unknown')}"
            )
            
            item_instruction = f"IMPORTANT: Your summary for this specific item MUST be around {item_target_words} words."
            
            summary_item = self._summarize_item(
                item, paper_title, paper_content, parsed_paper,
                length_instruction=item_instruction,
                target_words=item_target_words,
            )
            if summary_item:
                summary_items.append(summary_item)

        if not summary_items:
            logger.error("Failed to generate any summaries")
            return None

        # ── Step 4: Generate combined summary + key takeaway ─────────
        logger.info("Step 4: Generating combined summary and key takeaway")
        all_summaries_text = "\n\n---\n\n".join(
            item.raw_markdown for item in summary_items
        )

        combined_result = self._generate_combined_summary(
            paper_title=paper_title,
            authors=", ".join(authors[:5]),
            paper_url=paper_url,
            all_summaries=all_summaries_text,
        )

        # ── Build final result ───────────────────────────────────────
        summary = PaperSummary(
            paper_title=paper_title,
            authors=authors,
            paper_url=paper_url,
            items=summary_items,
            combined_summary=combined_result.get("combined", ""),
            key_takeaway=combined_result.get("takeaway", ""),
            useful_links=combined_result.get("links", ""),
        )

        # Build the full markdown output
        summary.full_markdown = self._build_full_markdown(summary)

        logger.info(
            f"✅ Summary complete: {len(summary_items)} items, "
            f"{len(summary.full_markdown)} chars"
        )
        return summary

    def _extract_items(self, paper_content: str) -> Optional[Dict[str, Any]]:
        """Step 1: Extract all problems and novel ideas from the paper."""
        prompt = EXTRACT_PROBLEMS_PROMPT.format(
            paper_content=paper_content[:60000]  # Safety truncation
        )

        result = self.llm.chat_json([
            {"role": "system", "content": "You are a research paper analyst. Respond only in valid JSON."},
            {"role": "user", "content": prompt},
        ], temperature=0.2, max_tokens=4096)

        return result

    def _summarize_item(
        self,
        item: Dict[str, Any],
        paper_title: str,
        paper_content: str,
        parsed_paper: ParsedPaper,
        length_instruction: str = "",
        target_words: int = 800,
    ) -> Optional[SummaryItem]:
        """Step 3: Generate A/B/C format summary for a single item."""
        item_type = item.get("type", "novel_idea")
        item_title = item.get("title", "Unknown")
        item_details = item.get("key_details", "")

        # Find relevant sections from the parsed paper
        relevant_sections = self._find_relevant_sections(
            item_details, parsed_paper
        )

        type_label = "Problem" if item_type == "problem" else "Novel Idea/Solution"

        # Use Director-assigned length instruction, fall back to generic instruction
        instruction = length_instruction or (
            f"Write a comprehensive, thorough summary of around {target_words} words."
        )

        prompt = SUMMARIZE_ITEM_PROMPT.format(
            paper_title=paper_title,
            item_type=item_type,
            item_title=item_title,
            item_details=item_details,
            relevant_sections=relevant_sections[:15000],  # Cap context
            item_type_label=type_label,
            length_instruction=instruction,
        )

        # Scale max_tokens proportionally to target_words (roughly 1.4 tokens per word)
        max_tokens = max(1000, min(4000, int(target_words * 1.4)))

        response = self.llm.chat([
            {
                "role": "system",
                "content": (
                    "You are an expert research paper summarizer. "
                    "Produce clear, comprehensive summaries that cover "
                    "every important detail while remaining concise and readable. "
                    "Include relevant links where helpful. "
                    "Strictly follow any word count instructions you are given."
                ),
            },
            {"role": "user", "content": prompt},
        ], temperature=0.3, max_tokens=max_tokens)

        if not response:
            return None

        # Parse the response into structured fields
        return self._parse_summary_response(response, item_type, item_title)

    def _find_relevant_sections(
        self, query: str, parsed_paper: ParsedPaper
    ) -> str:
        """Find the most relevant sections of the paper for a given query."""
        if not parsed_paper.sections:
            return parsed_paper.full_markdown[:10000]

        # Simple keyword overlap scoring
        query_words = set(query.lower().split())
        scored_sections = []

        for section in parsed_paper.sections:
            section_words = set(section.content.lower().split())
            overlap = len(query_words & section_words)
            scored_sections.append((overlap, section))

        # Sort by relevance and take top sections
        scored_sections.sort(key=lambda x: x[0], reverse=True)
        top_sections = scored_sections[:5]

        result_parts = []
        for _, section in top_sections:
            result_parts.append(
                f"### {section.title} (Pages {section.page_start}-{section.page_end})\n"
                f"{section.content[:3000]}"
            )

        return "\n\n".join(result_parts)

    def _parse_summary_response(
        self, response: str, item_type: str, item_title: str
    ) -> SummaryItem:
        """Parse the LLM's markdown response into structured SummaryItem fields."""
        # Extract sections using markers
        issue_text = self._extract_section(response, "What the author found", "How they tackled")
        solution_text = self._extract_section(response, "How they tackled", "Explain Like I'm 10")
        eli10_text = self._extract_section(response, "Explain Like I'm 10", "Explain for a College")
        eli_college_text = self._extract_section(response, "Explain for a College", None)

        return SummaryItem(
            item_type=item_type,
            title=item_title,
            issue_text=issue_text,
            solution_text=solution_text,
            eli10_text=eli10_text,
            eli_college_text=eli_college_text,
            raw_markdown=response,
        )

    def _extract_section(
        self, text: str, start_marker: str, end_marker: Optional[str]
    ) -> str:
        """Extract text between two section markers."""
        try:
            # Find start
            start_idx = text.lower().find(start_marker.lower())
            if start_idx == -1:
                return ""

            # Move past the header line
            newline_idx = text.find("\n", start_idx)
            if newline_idx == -1:
                return ""
            content_start = newline_idx + 1

            # Find end
            if end_marker:
                end_idx = text.lower().find(end_marker.lower(), content_start)
                if end_idx == -1:
                    content = text[content_start:]
                else:
                    # Go back to find the ** or ### before the end marker
                    search_area = text[max(0, end_idx - 50):end_idx]
                    marker_pos = search_area.rfind("**")
                    if marker_pos != -1:
                        end_idx = max(0, end_idx - 50) + marker_pos
                    content = text[content_start:end_idx]
            else:
                content = text[content_start:]

            return content.strip()
        except Exception:
            return ""

    def _generate_combined_summary(
        self, paper_title: str, authors: str,
        paper_url: str, all_summaries: str
    ) -> Dict[str, str]:
        """Step 3: Generate the combined summary and key takeaway."""
        extra_links = ""  # Will be populated by verification step later

        prompt = COMBINED_SUMMARY_PROMPT.format(
            paper_title=paper_title,
            authors=authors,
            paper_url=paper_url or "Not available",
            all_summaries=all_summaries[:20000],
            extra_links=extra_links,
        )

        response = self.llm.chat([
            {
                "role": "system",
                "content": (
                    "You are an expert research summarizer creating "
                    "a final synthesis. Be insightful and engaging."
                ),
            },
            {"role": "user", "content": prompt},
        ], temperature=0.4, max_tokens=2000)

        if not response:
            return {"combined": "", "takeaway": "", "links": ""}

        # Parse out the sections
        combined = self._extract_section(response, "Combined Summary", "Key Takeaway")
        takeaway = self._extract_section(response, "Key Takeaway", "Useful Links")
        links = self._extract_section(response, "Useful Links", None)

        return {
            "combined": combined,
            "takeaway": takeaway,
            "links": links,
        }

    def _build_full_markdown(self, summary: PaperSummary) -> str:
        """Build the complete formatted markdown output."""
        parts = []

        # Header
        parts.append(f"# 📄 {summary.paper_title}")
        if summary.authors:
            parts.append(f"**Authors:** {', '.join(summary.authors[:5])}")
        if summary.paper_url:
            parts.append(f"**Paper:** [{summary.paper_url}]({summary.paper_url})")
        parts.append("")
        parts.append("---")
        parts.append("")

        # Individual item summaries
        for i, item in enumerate(summary.items, 1):
            parts.append(item.raw_markdown)
            parts.append("")
            parts.append("---")
            parts.append("")

        # Combined summary
        if summary.combined_summary:
            parts.append("### 📝 Combined Summary")
            parts.append(summary.combined_summary)
            parts.append("")

        # Key takeaway
        if summary.key_takeaway:
            parts.append("### ⭐ Key Takeaway — MAKE NOTE OF THIS")
            parts.append(summary.key_takeaway)
            parts.append("")

        # Links
        if summary.useful_links:
            parts.append("### 🔗 Useful Links")
            parts.append(summary.useful_links)
            parts.append("")

        return "\n".join(parts)
