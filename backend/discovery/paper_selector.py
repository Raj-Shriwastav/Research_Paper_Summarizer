"""
Paper Selector Agent — Uses an LLM to evaluate a pool of candidates and select the best 3-5 papers.
"""
import json
import logging
from typing import List

from backend.summarization.llm_client import LLMClient
from backend.discovery.paper_fetcher import Paper

logger = logging.getLogger(__name__)

class PaperSelectorAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.prompt_template = """You are an expert academic curator. Your job is to select the 2 most impactful, novel, and highly relevant research papers from the following list of candidates.

Evaluate each paper based on:
1. Novelty & Contribution (does it propose something new or solve a major problem?)
2. Broad Impact (is it relevant to many practitioners or researchers?)
3. General Quality (is the abstract clear and authoritative?)

CANDIDATE PAPERS:
{candidates}

INSTRUCTIONS:
1. Select exactly 2 papers.
2. Return your selection as a pure JSON list of the numerical IDs of the papers you chose.
3. OUTPUT ONLY THE JSON ARRAY. NO text before. NO text after. NO markdown formatting.

Example output:
[0, 2]
"""

    def select_best_papers(self, candidates: List[Paper], min_papers: int = 2, max_papers: int = 2) -> List[Paper]:
        """Evaluate candidates and return the selected 2 best papers."""
        if len(candidates) <= max_papers:
            logger.info(f"Only {len(candidates)} candidates available. Selecting all.")
            return candidates

        logger.info(f"Evaluating {len(candidates)} candidate papers to select the best 3-5...")
        
        # Build candidate string
        candidate_text = ""
        for i, paper in enumerate(candidates):
            candidate_text += f"ID: {i}\n"
            candidate_text += f"Title: {paper.title}\n"
            candidate_text += f"Abstract: {paper.abstract[:800]}...\n" # Truncate abstract to save tokens
            candidate_text += f"Citations: {paper.citation_count}\n"
            candidate_text += "-" * 40 + "\n"

        messages = [
            {"role": "system", "content": "You are a highly intelligent academic curation AI."},
            {"role": "user", "content": self.prompt_template.format(candidates=candidate_text)}
        ]

        response = self.llm.chat(
            messages=messages,
            temperature=0.1,
            max_tokens=500,
            json_mode=True
        )

        if not response:
            logger.warning("Paper selection failed. Falling back to top 3 papers.")
            return candidates[:3]

        try:
            # Clean up potential markdown formatting in case the model ignored instructions
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

            # Robust JSON extraction
            import re
            match = re.search(r'\[(.*?)\]', response, re.DOTALL)
            if match:
                try:
                    selected_ids = json.loads("[" + match.group(1) + "]")
                except json.JSONDecodeError:
                    selected_ids = json.loads(response)
            else:
                selected_ids = json.loads(response)
            
            if not isinstance(selected_ids, list):
                raise ValueError("LLM did not return a JSON list")
                
            # Filter and validate IDs
            valid_ids = [i for i in selected_ids if isinstance(i, int) and 0 <= i < len(candidates)]
            
            if len(valid_ids) < min_papers:
                # Pad with top remaining candidates if LLM chose too few
                remaining = [i for i in range(len(candidates)) if i not in valid_ids]
                valid_ids.extend(remaining[:min_papers - len(valid_ids)])
            elif len(valid_ids) > max_papers:
                valid_ids = valid_ids[:max_papers]
                
            selected_papers = [candidates[i] for i in valid_ids]
            logger.info(f"Paper Selector chose {len(selected_papers)} papers.")
            return selected_papers
            
        except Exception as e:
            logger.error(f"Failed to parse Paper Selector response: {e}. Output was: {response}")
            from backend.utils import log_failure
            log_failure(
                error_type="Paper Selection Parsing Error",
                message="Failed to parse the LLM's chosen paper IDs.",
                details=f"Error: {str(e)}\nResponse: {response}"
            )
            # Fallback to top 3
            return candidates[:3]
