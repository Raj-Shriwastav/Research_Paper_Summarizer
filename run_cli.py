"""
CLI Runner — End-to-end test of the Day 1 Backend Core pipeline.

Tests: Topic Expansion → Paper Discovery → PDF Parsing → LLM Summarization.
"""

import sys
import logging
from pprint import pprint

from backend.config import load_config
from backend.discovery.topic_manager import expand_topic, get_all_available_topics
from backend.discovery.paper_fetcher import fetch_papers
from backend.discovery.paper_selector import PaperSelectorAgent
from backend.parsing.pdf_parser import parse_pdf, cleanup_cached_pdf, download_pdf
from backend.summarization.llm_client import LLMClient
from backend.summarization.summarizer import Summarizer
from backend.verification.link_verifier import LinkVerifier

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    # Reconfigure stdout to UTF-8 to prevent UnicodeEncodeError in Windows terminals when printing emojis
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("==================================================")
    print("🧠 Research Paper Summarizer — Day 1 Core Test")
    print("==================================================")

    # 1. Load config
    config = load_config()
    print("\n[✓] Config loaded.")

    # Show available topics
    print("\nAvailable pre-configured topics:")
    for t in get_all_available_topics():
        print(f"  - {t}")
    
    topic_input = input("\nEnter a topic to search for (e.g., 'AI Safety'): ").strip()
    if not topic_input:
        topic_input = "AI Safety"

    # 2. Expand topic
    topic = expand_topic(topic_input)
    print(f"\n[✓] Expanded Topic '{topic.name}':")
    print(f"    Keywords: {', '.join(topic.keywords)}")
    print(f"    arXiv Categories: {', '.join(topic.arxiv_categories)}")

    # 3. Discover candidate papers (fetch top 10 so selector has room to choose best 3-5)
    print(f"\n[⏳] Searching arXiv for '{topic.name}'...")
    candidates = fetch_papers(config.paper_api, topic, max_papers=10)

    if not candidates:
        print("\n[!] No papers found with accessible PDFs. Try another topic.")
        from backend.utils import log_failure
        log_failure(
            error_type="Pipeline Discovery Failure",
            message=f"No papers were discovered with accessible PDFs for expanded topic '{topic.name}'"
        )
        return

    print(f"\n[✓] Discovered {len(candidates)} candidate papers.")

    # 4. Initialize LLM early (needed for Paper Selector)
    print("\n[⏳] Initializing LLM Client...")
    try:
        llm = LLMClient(config.llm)
    except ValueError as e:
        print(f"\n[!] LLM Init Error: {e}")
        print("Please make sure you have added API keys to your .env file.")
        return

    print(f"    Active providers in fallback chain: {[p.name for p in llm.providers]}")

    # 5. Paper Selector Agent — choose best 3-5 from candidates
    print("\n[⏳] Paper Selector Agent is evaluating candidates...")
    selector = PaperSelectorAgent(llm)
    selected_papers = selector.select_best_papers(candidates, min_papers=2, max_papers=2)

    print(f"\n[✓] Paper Selector chose {len(selected_papers)} papers:")
    for i, p in enumerate(selected_papers):
        print(f"  {i+1}. {p.title}")
        print(f"     Citations: {p.citation_count} | Score: {p.relevance_score:.2f}")

    # 6. Initialize remaining pipeline components
    summarizer = Summarizer(llm)
    link_verifier = LinkVerifier()
    num_papers = len(selected_papers)

    # 7. Process each selected paper
    all_paper_markdowns = []
    pdf_paths_to_cleanup = []

    for paper_idx, paper in enumerate(selected_papers):
        print(f"\n{'='*55}")
        print(f"[⏳] Processing paper {paper_idx+1}/{num_papers}: {paper.title}")
        print(f"{'='*55}")

        # Download PDF
        print(f"    Downloading PDF: {paper.pdf_url}")
        pdf_path = download_pdf(paper.pdf_url, config.pdf_cache_dir)
        if not pdf_path:
            print(f"\n[!] Failed to download PDF for: {paper.title}. Skipping.")
            from backend.utils import log_failure
            log_failure(
                error_type="Pipeline PDF Download Failure",
                message=f"Skipping paper — could not download PDF for '{paper.title}'",
                details=f"PDF URL: {paper.pdf_url}"
            )
            continue
        pdf_paths_to_cleanup.append(pdf_path)

        # Parse PDF
        print(f"    Parsing PDF with PyMuPDF4LLM...")
        parsed_paper = parse_pdf(pdf_path, paper_title=paper.title)
        if not parsed_paper:
            print(f"\n[!] Failed to parse PDF for: {paper.title}. Skipping.")
            from backend.utils import log_failure
            log_failure(
                error_type="Pipeline PDF Parse Failure",
                message=f"Skipping paper — could not parse PDF for '{paper.title}'",
                details=f"PDF path: {pdf_path}"
            )
            continue

        print(f"    [✓] Parsed: {parsed_paper.total_pages} pages, {len(parsed_paper.sections)} sections")

        # Summarize (Director allocates word budget based on total paper count)
        print(f"    Generating summary (Director: {num_papers} papers total)...")
        summary = summarizer.summarize_paper(
            parsed_paper,
            authors=paper.authors,
            paper_url=paper.url or paper.pdf_url,
            num_papers=num_papers,
            paper_index=paper_idx,
        )

        if not summary:
            print(f"\n[!] Summarization failed for: {paper.title}. Skipping.")
            from backend.utils import log_failure
            log_failure(
                error_type="Pipeline Summarization Failure",
                message=f"Summarization returned None for paper '{paper.title}'"
            )
            continue

        # Run Link Verifier on this paper's markdown
        print(f"    Running Link Verifier...")
        verified_markdown = link_verifier.verify_and_clean(summary.full_markdown)

        all_paper_markdowns.append(verified_markdown)
        print(f"    [✓] Paper {paper_idx+1} complete.")

    # 8. Build and save the combined digest
    if not all_paper_markdowns:
        print("\n[!] All papers failed to summarize. Nothing to save.")
    else:
        import re
        from datetime import datetime

        # Combine all papers into one digest file
        topic_slug = re.sub(r'[^a-zA-Z0-9]', '_', topic.name)[:30]
        date_str = datetime.now().strftime("%Y-%m-%d")
        output_filename = f"digest_{topic_slug}_{date_str}.md"

        digest_header = (
            f"# 📚 Research Digest: {topic.name}\n"
            f"**Date:** {date_str}  |  **Papers summarized:** {len(all_paper_markdowns)}\n\n"
            f"---\n\n"
        )

        full_digest = digest_header + "\n\n---\n\n".join(all_paper_markdowns)

        # Estimate reading time
        word_count = len(full_digest.split())
        reading_time_min = word_count // 220
        print(f"\n[✓] Digest stats: {word_count} words ≈ {reading_time_min} min read")

        print("\n==================================================")
        print("🎉 DIGEST COMPLETE! 🎉")
        print("==================================================")

        # TODO: Remove this file saving logic later once the email system is fully integrated.
        # For now, we save the combined digest to a .md file for review before emailing.
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(full_digest)
            print(f"\n[✓] Digest saved to: {output_filename} (temporary feature)")
        except Exception as e:
            print(f"\n[!] Failed to save digest to file: {e}")

    # 9. Cleanup cached PDFs
    for path in pdf_paths_to_cleanup:
        cleanup_cached_pdf(path)
    print("\n[✓] Pipeline complete. Temporary PDFs cleaned up.")

if __name__ == "__main__":
    main()

