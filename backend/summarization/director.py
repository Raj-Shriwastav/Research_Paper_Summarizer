"""
Director Agent — Determines the length constraints for paper summaries to ensure 
the entire digest takes between 15 and 25 minutes to read (~3500 to 5500 words).
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SummaryConstraints:
    target_words: int
    instruction: str

class DirectorAgent:
    def __init__(self, target_min_minutes: int = 5, target_max_minutes: int = 8, words_per_minute: int = 220):
        self.min_words = target_min_minutes * words_per_minute
        self.max_words = target_max_minutes * words_per_minute
        self.target_total_words = (self.min_words + self.max_words) // 2

    def calculate_paper_constraints(self, num_papers: int, paper_index: int) -> SummaryConstraints:
        """
        Calculate the word limit and prompt constraint for a single paper 
        based on the total number of papers being summarized.
        """
        if num_papers == 0:
            return SummaryConstraints(target_words=500, instruction="Write a comprehensive 500-word summary.")
            
        # Allocate the total word budget equally among the papers
        words_per_paper = self.target_total_words // num_papers
        
        # Determine the strictness of the instruction based on the budget
        if words_per_paper < 600:
            instruction = f"IMPORTANT: Be extremely concise. Your entire summary MUST be around {words_per_paper} words. Focus only on the absolute most critical findings."
        elif words_per_paper < 1000:
            instruction = f"IMPORTANT: Your summary should be approximately {words_per_paper} words. Balance depth with brevity."
        else:
            instruction = f"IMPORTANT: You have a large word budget of approximately {words_per_paper} words. Provide a deep, highly detailed, and comprehensive breakdown."
            
        logger.info(f"Director allocated {words_per_paper} words for paper {paper_index + 1}/{num_papers}.")
        return SummaryConstraints(target_words=words_per_paper, instruction=instruction)
