"""
Grounding Verifier — Uses a Cross-Encoder model to check whether summary
sentences are factually supported by the original paper text.

Runs entirely on CPU. No API key required.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Tuple

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

# Sliding window parameters for chunking source text
_CHUNK_SIZE = 512  # words per chunk
_CHUNK_OVERLAP = 64  # word overlap between chunks


@dataclass
class FlaggedSentence:
    """A sentence that failed grounding verification."""
    sentence: str
    best_score: float
    best_source_chunk: str
    flag: str  # 'low_confidence', 'likely_hallucinated', 'unverifiable'
    index: int  # position in the summary


@dataclass
class VerificationResult:
    """Result of verifying a full summary against source text."""
    total_sentences: int
    flagged_sentences: List[FlaggedSentence] = field(default_factory=list)
    average_score: float = 0.0

    @property
    def pass_rate(self) -> float:
        if self.total_sentences == 0:
            return 1.0
        return 1.0 - (len(self.flagged_sentences) / self.total_sentences)


class GroundingVerifier:
    """
    Verifies that summary content is grounded in the source paper text
    using a Cross-Encoder semantic similarity model.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        threshold: float = 0.35,
    ):
        """
        Args:
            model_name: HuggingFace Cross-Encoder model to use.
            threshold: Minimum score for a sentence to be considered grounded.
                       Sentences below this are flagged.
        """
        logger.info(f"Loading Cross-Encoder model: {model_name}...")
        self.model = CrossEncoder(model_name)
        self.threshold = threshold
        logger.info("Cross-Encoder model loaded successfully.")

    def verify(self, summary_markdown: str, source_text: str) -> VerificationResult:
        """
        Verify each sentence in the summary against the source paper text.

        Args:
            summary_markdown: The generated summary in markdown format.
            source_text: The full text of the original paper.

        Returns:
            VerificationResult with flagged sentences, if any.
        """
        # Strip markdown formatting for clean sentence splitting
        clean_summary = self._strip_markdown(summary_markdown)
        sentences = self._split_sentences(clean_summary)

        if not sentences:
            return VerificationResult(total_sentences=0)

        # Chunk the source text for efficient comparison
        source_chunks = self._chunk_text(source_text)

        if not source_chunks:
            logger.warning("Source text is empty. Skipping verification.")
            return VerificationResult(total_sentences=len(sentences))

        logger.info(
            f"Verifying {len(sentences)} sentences against "
            f"{len(source_chunks)} source chunks..."
        )

        flagged = []
        all_scores = []

        for idx, sentence in enumerate(sentences):
            # Skip very short sentences (headings, labels, etc.)
            if len(sentence.split()) < 5:
                continue

            # Score this sentence against all source chunks
            pairs = [(sentence, chunk) for chunk in source_chunks]
            scores = self.model.predict(pairs)
            best_score = float(max(scores))
            best_chunk_idx = int(scores.argmax())
            all_scores.append(best_score)

            if best_score < self.threshold:
                # Determine the flag severity
                if best_score < 0.1:
                    flag = "likely_hallucinated"
                elif best_score < 0.2:
                    flag = "unverifiable"
                else:
                    flag = "low_confidence"

                flagged.append(FlaggedSentence(
                    sentence=sentence,
                    best_score=best_score,
                    best_source_chunk=source_chunks[best_chunk_idx][:200],
                    flag=flag,
                    index=idx,
                ))

        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

        result = VerificationResult(
            total_sentences=len(sentences),
            flagged_sentences=flagged,
            average_score=avg_score,
        )

        logger.info(
            f"Verification complete: {result.pass_rate:.0%} pass rate, "
            f"{len(flagged)} flagged out of {len(sentences)} sentences. "
            f"Average grounding score: {avg_score:.3f}"
        )

        return result

    def _strip_markdown(self, text: str) -> str:
        """Remove markdown formatting to get clean text for sentence splitting."""
        # Remove headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Remove bold/italic
        text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
        # Remove links but keep text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Remove images
        text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
        # Remove horizontal rules
        text = re.sub(r'^---+\s*$', '', text, flags=re.MULTILINE)
        # Remove code blocks
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        # Remove inline code
        text = re.sub(r'`[^`]+`', '', text)
        # Remove bullet points
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        # Collapse whitespace
        text = re.sub(r'\n{2,}', '\n', text)
        return text.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using a simple regex-based splitter."""
        # Split on period, question mark, or exclamation followed by space or newline
        raw = re.split(r'(?<=[.!?])\s+', text)
        # Filter out very short fragments
        return [s.strip() for s in raw if len(s.strip()) > 10]

    def _chunk_text(self, text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> List[str]:
        """Split source text into overlapping chunks for efficient comparison."""
        words = text.split()
        if len(words) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start += chunk_size - overlap

        return chunks
