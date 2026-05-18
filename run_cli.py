"""
CLI Runner — Entry point for the Research Paper Summarizer pipeline.

Supports three modes:
  - daily:   Full discovery → summarize → verify → email (default)
  - weekly:  Aggregates the week's daily digests → email
  - monthly: Aggregates the month's daily digests → email

Usage:
  python run_cli.py                     # Interactive daily mode
  python run_cli.py --mode daily        # Automated daily mode (uses default topics)
  python run_cli.py --mode weekly       # Weekly aggregation
  python run_cli.py --mode monthly      # Monthly aggregation
  python run_cli.py --topics "AI,Robotics"  # Custom topics
"""

import sys
import os
import argparse
import logging

from backend.config import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    # Reconfigure stdout to UTF-8 for Windows emoji support
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="Research Paper Summarizer Pipeline")
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly", "monthly"],
        default=None,
        help="Pipeline mode: daily (discover+summarize), weekly (aggregate), monthly (aggregate)"
    )
    parser.add_argument(
        "--topics",
        type=str,
        default=None,
        help="Comma-separated list of topics (e.g., 'AI,Robotics')"
    )
    parser.add_argument(
        "--target-email",
        type=str,
        default=None,
        help="Specific email address to dispatch a newly generated digest to (overrides subscriber list)."
    )
    parser.add_argument(
        "--log-id",
        type=str,
        default=None,
        help="Optional UUID of the email_delivery_log record to update upon completion."
    )
    args = parser.parse_args()

    config = load_config()

    # If no --mode flag, run interactive mode (legacy Day 1 behavior)
    if args.mode is None:
        _run_interactive(config)
        return

    # Automated mode via orchestrator
    from backend.orchestrator import PipelineOrchestrator

    print("==================================================")
    print(f"🧠 Research Paper Summarizer — {args.mode.capitalize()} Mode")
    print("==================================================")

    try:
        orchestrator = PipelineOrchestrator(config)
    except Exception as e:
        print(f"\n[!] Failed to initialize pipeline: {e}")
        return

    # Determine topics
    topics = None
    if args.topics:
        topics = [t.strip() for t in args.topics.split(",") if t.strip()]

    # Run the appropriate mode
    if args.mode == "daily":
        results = orchestrator.run_daily(topics=topics, target_email=args.target_email, log_id=args.log_id)
        _print_results(results, "Daily")

    elif args.mode == "weekly":
        results = orchestrator.run_weekly(topics=topics, target_email=args.target_email, log_id=args.log_id)
        _print_results(results, "Weekly")

    elif args.mode == "monthly":
        results = orchestrator.run_monthly(topics=topics, target_email=args.target_email, log_id=args.log_id)
        _print_results(results, "Monthly")

    print("\n[✓] Pipeline complete.")


def _print_results(results, mode: str):
    """Print a summary of the pipeline results."""
    if not results:
        print(f"\n[!] No {mode.lower()} digests were generated.")
        return

    print(f"\n{'='*50}")
    print(f"🎉 {mode} DIGEST{'S' if len(results) > 1 else ''} COMPLETE!")
    print(f"{'='*50}")

    for r in results:
        word_count = r.get("word_count", 0)
        reading_time = max(1, word_count // 220)
        print(f"\n  📚 {r['topic']} — {r['date']}")
        print(f"     Papers: {r.get('paper_count', 0)} | Words: {word_count} | ~{reading_time} min read")


def _run_interactive(config):
    """Legacy interactive mode for manual topic selection."""
    from backend.discovery.topic_manager import expand_topic, get_all_available_topics
    from backend.discovery.paper_fetcher import fetch_papers
    from backend.discovery.paper_selector import PaperSelectorAgent
    from backend.parsing.pdf_parser import parse_pdf, cleanup_cached_pdf, download_pdf
    from backend.summarization.llm_client import LLMClient
    from backend.summarization.summarizer import Summarizer
    from backend.verification.link_verifier import LinkVerifier
    import re
    from datetime import datetime

    print("==================================================")
    print("🧠 Research Paper Summarizer — Interactive Mode")
    print("==================================================")

    print("\n[✓] Config loaded.")

    # Show available topics
    print("\nAvailable pre-configured topics:")
    for t in get_all_available_topics():
        print(f"  - {t}")

    topic_input = input("\nEnter a topic to search for (e.g., 'AI Safety'): ").strip()
    if not topic_input:
        topic_input = "AI Safety"

    # Expand topic
    topic = expand_topic(topic_input)
    print(f"\n[✓] Expanded Topic '{topic.name}':")
    print(f"    Keywords: {', '.join(topic.keywords)}")
    print(f"    arXiv Categories: {', '.join(topic.arxiv_categories)}")

    # Discover papers
    print(f"\n[⏳] Searching arXiv for '{topic.name}'...")
    candidates = fetch_papers(config.paper_api, topic, max_papers=10)

    if not candidates:
        print("\n[!] No papers found with accessible PDFs. Try another topic.")
        return

    print(f"\n[✓] Discovered {len(candidates)} candidate papers.")

    # Initialize LLM
    print("\n[⏳] Initializing LLM Client...")
    try:
        llm = LLMClient(config.llm)
    except ValueError as e:
        print(f"\n[!] LLM Init Error: {e}")
        return

    print(f"    Active providers: {[p.name for p in llm.providers]}")

    # Select best papers
    print("\n[⏳] Paper Selector Agent is evaluating candidates...")
    selector = PaperSelectorAgent(llm)
    selected_papers = selector.select_best_papers(candidates, min_papers=2, max_papers=2)

    print(f"\n[✓] Paper Selector chose {len(selected_papers)} papers:")
    for i, p in enumerate(selected_papers):
        print(f"  {i+1}. {p.title}")
        print(f"     Citations: {p.citation_count} | Score: {p.relevance_score:.2f}")

    # Process papers
    summarizer = Summarizer(llm)
    link_verifier = LinkVerifier()
    num_papers = len(selected_papers)
    all_paper_markdowns = []
    pdf_paths_to_cleanup = []

    for paper_idx, paper in enumerate(selected_papers):
        print(f"\n{'='*55}")
        print(f"[⏳] Processing paper {paper_idx+1}/{num_papers}: {paper.title}")
        print(f"{'='*55}")

        pdf_path = download_pdf(paper.pdf_url, config.pdf_cache_dir)
        if not pdf_path:
            print(f"\n[!] Failed to download PDF for: {paper.title}. Skipping.")
            continue
        pdf_paths_to_cleanup.append(pdf_path)

        print(f"    Parsing PDF with PyMuPDF4LLM...")
        parsed_paper = parse_pdf(pdf_path, paper_title=paper.title)
        if not parsed_paper:
            print(f"\n[!] Failed to parse PDF for: {paper.title}. Skipping.")
            continue

        print(f"    [✓] Parsed: {parsed_paper.total_pages} pages, {len(parsed_paper.sections)} sections")

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
            continue

        print(f"    Running Link Verifier...")
        verified_markdown = link_verifier.verify_and_clean(summary.full_markdown)
        all_paper_markdowns.append(verified_markdown)
        print(f"    [✓] Paper {paper_idx+1} complete.")

    # Build digest
    if not all_paper_markdowns:
        print("\n[!] All papers failed to summarize. Nothing to save.")
    else:
        topic_slug = re.sub(r'[^a-zA-Z0-9]', '_', topic.name)[:30]
        date_str = datetime.now().strftime("%Y-%m-%d")

        os.makedirs("digests", exist_ok=True)
        output_filename = os.path.join("digests", f"digest_{topic_slug}_{date_str}.md")

        digest_header = (
            f"# 📚 Research Digest: {topic.name}\n"
            f"**Date:** {date_str}  |  **Papers summarized:** {len(all_paper_markdowns)}\n\n"
            f"---\n\n"
        )
        full_digest = digest_header + "\n\n---\n\n".join(all_paper_markdowns)
        word_count = len(full_digest.split())
        reading_time_min = word_count // 220

        print(f"\n[✓] Digest stats: {word_count} words ≈ {reading_time_min} min read")
        print("\n==================================================")
        print("🎉 DIGEST COMPLETE! 🎉")
        print("==================================================")

        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(full_digest)
            print(f"\n[✓] Digest saved to: {output_filename}")
        except Exception as e:
            print(f"\n[!] Failed to save digest to file: {e}")

    # Cleanup
    for path in pdf_paths_to_cleanup:
        cleanup_cached_pdf(path)
    print("\n[✓] Pipeline complete. Temporary PDFs cleaned up.")


if __name__ == "__main__":
    main()
