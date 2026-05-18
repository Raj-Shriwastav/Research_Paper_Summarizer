"""
Fixer Agent — Uses the LLM to rewrite flagged sentences so they are
factually grounded in the original source text.
"""

import logging
from typing import List

from backend.summarization.llm_client import LLMClient
from backend.verification.verifier import FlaggedSentence

logger = logging.getLogger(__name__)

_FIX_PROMPT = """You are a scientific editor. A verification system has flagged the following sentence(s) from a research paper summary as potentially inaccurate or not grounded in the source text.

Your task: Rewrite EACH flagged sentence so it is factually accurate based ONLY on the source text provided. If a claim cannot be verified from the source, remove it entirely.

FLAGGED SENTENCES:
{flagged_block}

RELEVANT SOURCE TEXT:
{source_text}

INSTRUCTIONS:
1. For each flagged sentence, provide a corrected version.
2. The corrected sentence must be supported by the source text.
3. Keep the same tone and style as the original.
4. If the sentence is completely fabricated with no basis in the source, replace it with "[REMOVED — unverifiable claim]".
5. Return your corrections in this exact format (one per line):

ORIGINAL: <original sentence>
FIXED: <corrected sentence>

Do NOT add any other text or explanations."""


class FixerAgent:
    """Uses the LLM to rewrite flagged sentences grounded in source text."""

    def __init__(self, llm_client: LLMClient, batch_size: int = 5):
        self.llm = llm_client
        self.batch_size = batch_size

    def fix_flagged_sentences(
        self,
        flagged: List[FlaggedSentence],
        source_text: str,
        full_markdown: str,
    ) -> str:
        """
        Fix all flagged sentences in the markdown using LLM rewrites.

        Args:
            flagged: List of FlaggedSentence objects from the Verifier.
            source_text: The original paper text for grounding.
            full_markdown: The full summary markdown to be corrected.

        Returns:
            The corrected markdown string.
        """
        if not flagged:
            return full_markdown

        logger.info(f"Fixer Agent: processing {len(flagged)} flagged sentences in batches of {self.batch_size}...")

        corrected_markdown = full_markdown

        # Process in batches to minimize API calls
        for batch_start in range(0, len(flagged), self.batch_size):
            batch = flagged[batch_start:batch_start + self.batch_size]
            corrections = self._fix_batch(batch, source_text)

            # Apply corrections to the markdown
            for original, fixed in corrections:
                if fixed and fixed != original:
                    corrected_markdown = corrected_markdown.replace(original, fixed)
                    logger.debug(f"Fixed: '{original[:60]}...' → '{fixed[:60]}...'")

        # Remove any "[REMOVED — unverifiable claim]" markers
        lines = corrected_markdown.split("\n")
        cleaned_lines = [
            line for line in lines
            if "[REMOVED" not in line
        ]
        corrected_markdown = "\n".join(cleaned_lines)

        logger.info(f"Fixer Agent: completed. Applied corrections to {len(flagged)} sentences.")
        return corrected_markdown

    def _fix_batch(
        self,
        batch: List[FlaggedSentence],
        source_text: str,
    ) -> List[tuple]:
        """
        Send a batch of flagged sentences to the LLM for correction.
        Returns list of (original, fixed) tuples.
        """
        # Build the flagged block
        flagged_block = "\n".join(
            f"{i+1}. [{f.flag}] (score: {f.best_score:.3f}) \"{f.sentence}\""
            for i, f in enumerate(batch)
        )

        # Truncate source text to avoid hitting token limits
        source_truncated = source_text[:8000]

        prompt = _FIX_PROMPT.format(
            flagged_block=flagged_block,
            source_text=source_truncated,
        )

        response = self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
        )

        if not response:
            logger.warning("Fixer Agent: LLM returned no response. Keeping original sentences.")
            return [(f.sentence, f.sentence) for f in batch]

        # Parse the ORIGINAL/FIXED pairs from the response
        corrections = []
        lines = response.strip().split("\n")
        current_original = None

        for line in lines:
            line = line.strip()
            if line.startswith("ORIGINAL:"):
                current_original = line[len("ORIGINAL:"):].strip().strip('"')
            elif line.startswith("FIXED:") and current_original:
                fixed = line[len("FIXED:"):].strip().strip('"')
                corrections.append((current_original, fixed))
                current_original = None

        # If parsing failed, try to match by index
        if not corrections:
            logger.warning("Fixer Agent: could not parse LLM corrections. Keeping originals.")
            return [(f.sentence, f.sentence) for f in batch]

        return corrections
