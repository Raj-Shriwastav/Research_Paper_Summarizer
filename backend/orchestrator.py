"""
Pipeline Orchestrator — Full end-to-end pipeline for daily, weekly, and monthly digests.

Ties together: Discovery → Selection → Parsing → Summarization → Verification → Fix → Save → Email.
"""

import os
import re
import logging
import markdown
from datetime import datetime, timedelta
from typing import List, Optional

from backend.config import AppConfig
from backend.discovery.topic_manager import expand_topic, get_all_available_topics
from backend.discovery.paper_fetcher import fetch_papers
from backend.discovery.paper_selector import PaperSelectorAgent
from backend.parsing.pdf_parser import parse_pdf, download_pdf, cleanup_cached_pdf
from backend.summarization.llm_client import LLMClient
from backend.summarization.summarizer import Summarizer
from backend.verification.link_verifier import LinkVerifier
from backend.verification.verifier import GroundingVerifier
from backend.verification.fixer import FixerAgent
from backend.email_service.sender import EmailSender
from backend.email_service import templates as email_templates

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrates the full research digest pipeline.

    Supports three cadences:
    - daily: Full discovery → summarize → verify → email
    - weekly: Aggregates the week's daily digests → email
    - monthly: Aggregates the month's daily digests → email
    """

    def __init__(self, config: AppConfig):
        self.config = config

        # Core components
        self.llm = LLMClient(config.llm)
        self.summarizer = Summarizer(self.llm)
        self.selector = PaperSelectorAgent(self.llm)
        self.link_verifier = LinkVerifier()
        self.email_sender = EmailSender(config.email)

        # Verification components (lazy-loaded to avoid slow model load if not needed)
        self._grounding_verifier = None
        self._fixer = None

        # Database (optional — works without it for local runs)
        self._db = None
        try:
            from backend.database import DatabaseClient
            self._db = DatabaseClient(config.supabase)
        except Exception as e:
            logger.warning(f"Supabase not configured. Running in local-only mode. ({e})")

    @property
    def grounding_verifier(self) -> GroundingVerifier:
        """Lazy-load the Cross-Encoder model to save memory when not needed."""
        if self._grounding_verifier is None:
            self._grounding_verifier = GroundingVerifier()
        return self._grounding_verifier

    @property
    def fixer(self) -> FixerAgent:
        """Lazy-load the Fixer Agent."""
        if self._fixer is None:
            self._fixer = FixerAgent(self.llm)
        return self._fixer

    # ──────────────────────────────────────────────
    # Daily Pipeline
    # ──────────────────────────────────────────────

    def run_daily(self, topics: Optional[List[str]] = None, target_email: Optional[str] = None, log_id: Optional[str] = None) -> List[dict]:
        """
        Run the full daily pipeline for the given topics.

        Args:
            topics: List of topic names. If None, uses default topics from user prefs.
            target_email: If provided, bypasses normal subscribers and sends only to this email.
            log_id: UUID of the email_delivery_log record to update.

        Returns:
            List of digest result dicts with keys: topic, date, markdown, html, word_count.
        """
        if not topics:
            topics = ["Artificial Intelligence"]

        date_str = datetime.now().strftime("%Y-%m-%d")
        results = []

        for topic_name in topics:
            logger.info(f"{'='*60}")
            logger.info(f"Daily pipeline: Processing topic '{topic_name}'")
            logger.info(f"{'='*60}")

            try:
                result = self._process_topic(topic_name, date_str, skip_db=bool(target_email))
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"Failed to process topic '{topic_name}': {e}")
                continue

        # Send daily emails
        if results:
            self._send_daily_emails(results, target_email=target_email)
            if self._db and log_id:
                self._db.update_delivery_log(log_id, "success")
        else:
            if self._db and log_id:
                self._db.update_delivery_log(log_id, "error", "No results generated")

        # Cleanup old digests
        if self._db and not target_email:
            self._db.cleanup_old_digests(days=45)

        return results

    def _process_topic(self, topic_name: str, date_str: str, skip_db: bool = False) -> Optional[dict]:
        """Process a single topic through the full pipeline."""
        # 1. Expand topic
        topic = expand_topic(topic_name)
        logger.info(f"Expanded topic '{topic.name}': {len(topic.keywords)} keywords")

        # 2. Discover papers
        candidates = fetch_papers(self.config.paper_api, topic, max_papers=10)
        if not candidates:
            logger.warning(f"No papers found for '{topic_name}'. Skipping.")
            return None

        logger.info(f"Discovered {len(candidates)} candidate papers.")

        # 3. Select best papers
        selected = self.selector.select_best_papers(candidates, min_papers=2, max_papers=2)
        logger.info(f"Selected {len(selected)} papers for summarization.")

        # 4. Process each paper
        all_markdowns = []
        paper_data = []
        pdf_paths = []
        num_papers = len(selected)

        for idx, paper in enumerate(selected):
            logger.info(f"Processing paper {idx+1}/{num_papers}: {paper.title}")

            # Download PDF
            pdf_path = download_pdf(paper.pdf_url, self.config.pdf_cache_dir)
            if not pdf_path:
                logger.warning(f"Failed to download PDF for '{paper.title}'. Skipping.")
                continue
            pdf_paths.append(pdf_path)

            # Parse PDF
            parsed = parse_pdf(pdf_path, paper_title=paper.title)
            if not parsed:
                logger.warning(f"Failed to parse PDF for '{paper.title}'. Skipping.")
                continue

            # Summarize
            summary = self.summarizer.summarize_paper(
                parsed,
                authors=paper.authors,
                paper_url=paper.url or paper.pdf_url,
                num_papers=num_papers,
                paper_index=idx,
            )
            if not summary:
                logger.warning(f"Summarization failed for '{paper.title}'. Skipping.")
                continue

            # 5. Verify grounding
            try:
                source_text = parsed.full_text if hasattr(parsed, 'full_text') else ""
                if source_text:
                    verification = self.grounding_verifier.verify(
                        summary.full_markdown, source_text
                    )

                    # 6. Fix flagged sentences
                    if verification.flagged_sentences:
                        logger.info(
                            f"Verifier flagged {len(verification.flagged_sentences)} sentences. "
                            f"Running Fixer Agent..."
                        )
                        summary.full_markdown = self.fixer.fix_flagged_sentences(
                            verification.flagged_sentences,
                            source_text,
                            summary.full_markdown,
                        )
            except Exception as e:
                logger.warning(f"Verification/fix step failed (non-critical): {e}")

            # 7. Verify links
            verified_md = self.link_verifier.verify_and_clean(summary.full_markdown)
            all_markdowns.append(verified_md)

            # Collect paper data for email template
            paper_data.append({
                "title": paper.title,
                "authors": ", ".join(paper.authors) if paper.authors else "Unknown",
                "summary_html": self._md_to_html(verified_md),
                "url": paper.url or paper.pdf_url,
            })

        # Cleanup PDFs
        for path in pdf_paths:
            cleanup_cached_pdf(path)

        if not all_markdowns:
            logger.warning(f"All papers failed for topic '{topic_name}'. No digest generated.")
            return None

        # 8. Build combined digest
        topic_slug = re.sub(r'[^a-zA-Z0-9]', '_', topic.name)[:30]
        digest_header = (
            f"# 📚 Research Digest: {topic.name}\n"
            f"**Date:** {date_str}  |  **Papers summarized:** {len(all_markdowns)}\n\n"
            f"---\n\n"
        )
        full_markdown = digest_header + "\n\n---\n\n".join(all_markdowns)
        word_count = len(full_markdown.split())

        # Save to local file
        os.makedirs("digests", exist_ok=True)
        output_path = os.path.join("digests", f"digest_{topic_slug}_{date_str}.md")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_markdown)
            logger.info(f"Digest saved to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save digest file: {e}")

        # Render HTML for email
        html_content = email_templates.render_daily(
            topic=topic.name,
            date=date_str,
            papers=paper_data,
            word_count=word_count,
        )

        # 9. Save to database
        if self._db and not skip_db:
            self._db.save_digest(
                topic=topic.name,
                digest_date=date_str,
                cadence="daily",
                markdown_content=full_markdown,
                html_content=html_content,
                paper_count=len(all_markdowns),
                word_count=word_count,
            )

        result = {
            "topic": topic.name,
            "date": date_str,
            "markdown": full_markdown,
            "html": html_content,
            "word_count": word_count,
            "paper_count": len(all_markdowns),
        }

        logger.info(
            f"✅ Daily digest complete for '{topic.name}': "
            f"{word_count} words, {len(all_markdowns)} papers"
        )
        return result

    # ──────────────────────────────────────────────
    # Weekly Pipeline
    # ──────────────────────────────────────────────

    def run_weekly(self, topics: Optional[List[str]] = None, target_email: Optional[str] = None, log_id: Optional[str] = None) -> List[dict]:
        """Aggregate the week's daily digests and send a weekly email."""
        if not self._db:
            logger.error("Weekly pipeline requires Supabase. Skipping.")
            return []

        if not topics:
            topics = ["Artificial Intelligence"]

        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        week_end = today.strftime("%Y-%m-%d")

        results = []
        for topic_name in topics:
            daily_digests = self._db.get_weekly_digests(topic_name)
            if not daily_digests:
                logger.warning(f"No daily digests found for '{topic_name}' this week.")
                continue

            # Build weekly data
            days = []
            total_papers = 0
            total_words = 0
            for digest in daily_digests:
                days.append({
                    "date": digest["digest_date"],
                    "paper_count": digest.get("paper_count", 0),
                    "paper_titles": [f"Paper {i+1}" for i in range(digest.get("paper_count", 0))],
                    "content_html": self._md_to_html(digest["markdown_content"]),
                })
                total_papers += digest.get("paper_count", 0)
                total_words += digest.get("word_count", 0)

            html = email_templates.render_weekly(
                topic=topic_name,
                week_start=week_start,
                week_end=week_end,
                days=days,
                total_papers=total_papers,
                total_words=total_words,
            )

            # Save weekly digest
            if not target_email:
                self._db.save_digest(
                    topic=topic_name,
                    digest_date=week_end,
                    cadence="weekly",
                    markdown_content="",  # Weekly is HTML-only aggregation
                    html_content=html,
                    paper_count=total_papers,
                    word_count=total_words,
                )

            results.append({
                "topic": topic_name,
                "date": week_end,
                "html": html,
                "word_count": total_words,
                "paper_count": total_papers,
            })

        # Send weekly emails
        if results:
            self._send_cadence_emails(results, "weekly", "📅 Weekly Research Roundup", target_email=target_email)
            if log_id:
                self._db.update_delivery_log(log_id, "success")
        else:
            if log_id:
                self._db.update_delivery_log(log_id, "error", "No results generated")

        return results

    # ──────────────────────────────────────────────
    # Monthly Pipeline
    # ──────────────────────────────────────────────

    def run_monthly(self, topics: Optional[List[str]] = None, target_email: Optional[str] = None, log_id: Optional[str] = None) -> List[dict]:
        """Aggregate the month's daily digests and send a monthly email."""
        if not self._db:
            logger.error("Monthly pipeline requires Supabase. Skipping.")
            return []

        if not topics:
            topics = ["Artificial Intelligence"]

        today = datetime.now()
        month_name = today.strftime("%B")
        year = today.year

        results = []
        for topic_name in topics:
            daily_digests = self._db.get_monthly_digests(topic_name)
            if not daily_digests:
                logger.warning(f"No daily digests found for '{topic_name}' this month.")
                continue

            # Group by week
            weeks = []
            current_week = []
            total_papers = 0
            total_words = 0
            top_papers = []

            for digest in daily_digests:
                total_papers += digest.get("paper_count", 0)
                total_words += digest.get("word_count", 0)
                current_week.append(digest)

                # Simple top papers extraction
                if digest.get("paper_count", 0) > 0:
                    top_papers.append({
                        "title": f"{topic_name} digest",
                        "date": digest["digest_date"],
                    })

            # Add all as one "week" for simplicity
            if current_week:
                weeks.append({
                    "start": current_week[0]["digest_date"],
                    "end": current_week[-1]["digest_date"],
                    "content_html": "<br>".join(
                        self._md_to_html(d["markdown_content"]) for d in current_week
                    ),
                })

            html = email_templates.render_monthly(
                topic=topic_name,
                month_name=month_name,
                year=year,
                weeks=weeks,
                top_papers=top_papers[:5],
                total_papers=total_papers,
                total_words=total_words,
            )

            # Save monthly digest
            if not target_email:
                self._db.save_digest(
                    topic=topic_name,
                    digest_date=today.strftime("%Y-%m-%d"),
                    cadence="monthly",
                    markdown_content="",
                    html_content=html,
                    paper_count=total_papers,
                    word_count=total_words,
                )

            results.append({
                "topic": topic_name,
                "date": today.strftime("%Y-%m-%d"),
                "html": html,
                "word_count": total_words,
                "paper_count": total_papers,
            })

        # Send monthly emails
        if results:
            self._send_cadence_emails(results, "monthly", "📊 Monthly Research Report", target_email=target_email)
            if log_id:
                self._db.update_delivery_log(log_id, "success")
        else:
            if log_id:
                self._db.update_delivery_log(log_id, "error", "No results generated")

        return results

    # ──────────────────────────────────────────────
    # Email Helpers
    # ──────────────────────────────────────────────

    def _send_daily_emails(self, results: List[dict], target_email: Optional[str] = None):
        """Send daily digest emails to subscribers."""
        if target_email:
            # Bypass DB, send directly to target_email
            for result in results:
                html_body = result["html"]
                greeting = f'<div style="padding: 20px 0 12px 0; font-size: 16px; color: #e0e0e0;">👋 Hi <strong style="color: #ffffff;">Admin ({target_email})</strong>,<br><span style="color: #a0c4ff;">Here\'s your daily research digest — freshly curated just for you.</span></div>'
                html_body = html_body.replace('<div class="content">', f'<div class="content">\n        {greeting}')
                
                subject = f"📚 [Test] Daily Digest: {result['topic']} — {result['date']}"
                self.email_sender.send_digest(
                    to_emails=[target_email],
                    subject=subject,
                    html_body=html_body,
                    plain_text=result.get("markdown", ""),
                )
            return

        if not self._db:
            # Fallback for local testing without DB
            recipients = self.config.email.recipient_emails
            if not recipients:
                logger.warning("No email recipients configured. Skipping email delivery.")
                return
            for result in results:
                subject = f"📚 Daily Digest: {result['topic']} — {result['date']}"
                self.email_sender.send_digest(
                    to_emails=recipients,
                    subject=subject,
                    html_body=result["html"],
                    plain_text=result.get("markdown", ""),
                )
            return

        subscribers = self._db.get_subscribers("daily")
        
        # Add fallback recipients if not in subscribers
        recipients = self.config.email.recipient_emails
        subscriber_emails = set()
        
        for sub in subscribers:
            user_info = sub.get("users", {})
            delivery_email = user_info.get("delivery_email") or user_info.get("email")
            display_name = user_info.get("display_name", "")
            
            if not delivery_email:
                continue
                
            subscriber_emails.add(delivery_email)
            
            for result in results:
                # Need to re-render for this user to get the personalized greeting
                # Note: This is an approximation since we don't store paper_data in the result dict currently.
                # If paper_data isn't available, we'll inject the greeting via simple string replacement.
                html_body = result["html"]
                if display_name:
                    greeting = f'<div style="padding: 20px 0 12px 0; font-size: 16px; color: #e0e0e0;">👋 Hi <strong style="color: #ffffff;">{display_name}</strong>,<br><span style="color: #a0c4ff;">Here\'s your daily research digest — freshly curated just for you.</span></div>'
                    html_body = html_body.replace('<div class="content">', f'<div class="content">\n        {greeting}')
                
                subject = f"📚 Daily Digest: {result['topic']} — {result['date']}"
                self.email_sender.send_digest(
                    to_emails=[delivery_email],
                    subject=subject,
                    html_body=html_body,
                    plain_text=result.get("markdown", ""),
                )

        # Send to config recipients who are not in DB
        for email in recipients:
            if email not in subscriber_emails:
                for result in results:
                    subject = f"📚 Daily Digest: {result['topic']} — {result['date']}"
                    self.email_sender.send_digest(
                        to_emails=[email],
                        subject=subject,
                        html_body=result["html"],
                        plain_text=result.get("markdown", ""),
                    )

    def _send_cadence_emails(self, results: List[dict], cadence: str, subject_prefix: str, target_email: Optional[str] = None):
        """Send weekly/monthly emails to subscribers of that cadence."""
        if target_email:
            for result in results:
                html_body = result["html"]
                message_type = "weekly research roundup — the best papers from this week" if cadence == "weekly" else "monthly research report — a deep dive into this month's highlights"
                greeting = f'<div style="padding: 20px 0 12px 0; font-size: 16px; color: #e0e0e0;">👋 Hi <strong style="color: #ffffff;">Admin ({target_email})</strong>,<br><span style="color: #a0c4ff;">Here\'s your {message_type}.</span></div>'
                html_body = html_body.replace('<div class="content">', f'<div class="content">\n        {greeting}')

                subject = f"[Test] {subject_prefix}: {result['topic']} — {result['date']}"
                self.email_sender.send_digest(
                    to_emails=[target_email],
                    subject=subject,
                    html_body=html_body,
                )
            return

        if not self._db:
            recipients = self.config.email.recipient_emails
            if not recipients:
                logger.warning(f"No {cadence} email recipients. Skipping.")
                return
            for result in results:
                subject = f"{subject_prefix}: {result['topic']} — {result['date']}"
                self.email_sender.send_digest(
                    to_emails=recipients,
                    subject=subject,
                    html_body=result["html"],
                )
            return

        subscribers = self._db.get_subscribers(cadence)
        recipients = self.config.email.recipient_emails
        subscriber_emails = set()

        for sub in subscribers:
            user_info = sub.get("users", {})
            delivery_email = user_info.get("delivery_email") or user_info.get("email")
            display_name = user_info.get("display_name", "")
            
            if not delivery_email:
                continue
                
            subscriber_emails.add(delivery_email)
            
            for result in results:
                html_body = result["html"]
                if display_name:
                    message_type = "weekly research roundup — the best papers from this week" if cadence == "weekly" else "monthly research report — a deep dive into this month's highlights"
                    greeting = f'<div style="padding: 20px 0 12px 0; font-size: 16px; color: #e0e0e0;">👋 Hi <strong style="color: #ffffff;">{display_name}</strong>,<br><span style="color: #a0c4ff;">Here\'s your {message_type}.</span></div>'
                    html_body = html_body.replace('<div class="content">', f'<div class="content">\n        {greeting}')

                subject = f"{subject_prefix}: {result['topic']} — {result['date']}"
                self.email_sender.send_digest(
                    to_emails=[delivery_email],
                    subject=subject,
                    html_body=html_body,
                )
        
        # Send to config recipients who are not in DB
        for email in recipients:
            if email not in subscriber_emails:
                for result in results:
                    subject = f"{subject_prefix}: {result['topic']} — {result['date']}"
                    self.email_sender.send_digest(
                        to_emails=[email],
                        subject=subject,
                        html_body=result["html"],
                    )

    @staticmethod
    def _md_to_html(md_text: str) -> str:
        """Convert markdown to HTML for email embedding."""
        try:
            return markdown.markdown(md_text, extensions=["tables", "fenced_code"])
        except Exception:
            # Fallback: wrap in <pre> tags
            return f"<pre>{md_text}</pre>"
