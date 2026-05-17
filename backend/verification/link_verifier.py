"""
Link Verifier — Scans generated markdown for URLs and verifies their HTTP status.
Removes dead links (404, timeouts, etc) to prevent hallucinated or broken URLs.
"""

import re
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class LinkVerifier:
    def __init__(self, timeout: int = 5, max_workers: int = 10):
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Regex to find markdown links: [text](url)
        self.link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')

    def verify_and_clean(self, markdown_text: str) -> str:
        """
        Scan markdown for links, verify them concurrently, 
        and return a cleaned markdown string with broken links removed.
        """
        links = self.link_pattern.findall(markdown_text)
        if not links:
            return markdown_text
            
        # Deduplicate URLs to avoid redundant checks
        unique_urls = {url for text, url in links}
        
        logger.info(f"LinkVerifier found {len(unique_urls)} unique URLs to verify.")
        
        url_status = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self._check_url, url): url 
                for url in unique_urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    is_valid = future.result()
                    url_status[url] = is_valid
                except Exception as e:
                    logger.warning(f"Link check exception for {url}: {e}")
                    url_status[url] = False
                    
        # Replace broken links in text
        def _replace_broken_link(match):
            text = match.group(1)
            url = match.group(2)
            if not url_status.get(url, False):
                logger.info(f"Removing broken link: {url}")
                # Log to test_failed.txt
                try:
                    from backend.utils import log_failure
                    log_failure(
                        error_type="Broken Link Removed",
                        message=f"Removed dead or hallucinated link: {url}",
                        details=f"Link text: {text}"
                    )
                except Exception:
                    pass
                return text  # Return just the text, stripping the URL wrapper
            return match.group(0) # Keep intact
            
        cleaned_markdown = self.link_pattern.sub(_replace_broken_link, markdown_text)
        return cleaned_markdown

    def _check_url(self, url: str) -> bool:
        """Check if a URL is reachable and returns 200 OK."""
        try:
            # First try HEAD request (faster)
            resp = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 405: # Method Not Allowed
                # Fallback to GET
                resp = self.session.get(url, timeout=self.timeout, stream=True)
                resp.close()
                
            # Some servers return 403 for bots, we'll give them the benefit of the doubt
            # Usually 404, 500, 502, 503 are the ones we definitely want to remove.
            return resp.status_code < 400 or resp.status_code == 403
            
        except requests.RequestException:
            return False
