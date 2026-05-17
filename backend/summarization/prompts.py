"""
Prompts — All LLM prompt templates for the summarization pipeline.

Separated into their own module so they're easy to iterate on
without touching the summarization logic.
"""

# ── Step 1: Extract problems and novel ideas from the paper ──────────────

EXTRACT_PROBLEMS_PROMPT = """You are an expert research paper analyst. Your job is to carefully read the following research paper and extract ALL distinct problems addressed and novel ideas/contributions proposed by the authors.

**PAPER CONTENT:**
{paper_content}

**INSTRUCTIONS:**
1. Identify every distinct problem the authors identify or address.
2. Identify every novel idea, method, contribution, or solution they propose.
3. A paper may have 1 problem and 1 solution, or it may have multiple problems and multiple novel contributions. Extract ALL of them.
4. For each item, provide a short descriptive title.
5. Classify each as either "problem" or "novel_idea".

**RESPOND IN JSON FORMAT:**
{{
    "paper_title": "The title of the paper",
    "items": [
        {{
            "type": "problem",
            "title": "Short descriptive title of the problem",
            "key_details": "2-4 sentences describing the core problem with specific details from the paper"
        }},
        {{
            "type": "novel_idea", 
            "title": "Short descriptive title of the idea/solution",
            "key_details": "2-4 sentences describing what they did with specific technical details"
        }}
    ]
}}

Be thorough — do not miss any problems or novel contributions. Extract every distinct idea."""


# ── Step 2: Generate A/B/C format summary for each item ─────────────────

SUMMARIZE_ITEM_PROMPT = """You are a research paper summarizer who explains complex academic content clearly. 

**PAPER TITLE:** {paper_title}

**ITEM TO SUMMARIZE:**
Type: {item_type}
Title: {item_title}
Key Details: {item_details}

**RELEVANT PAPER SECTIONS:**
{relevant_sections}

**YOUR TASK:**
Generate a summary of this {item_type} in the following exact format.
{length_instruction}

Include relevant links where appropriate (to concepts, tools, datasets, methods mentioned).

**FORMAT:**

### {item_type_label}: {item_title}

**A. What the author found (The Issue)**
[Comprehensive explanation in plain, everyday language. Cover all the key aspects of what was discovered/identified. Include why this matters and what the current state of affairs was before this work.]

**B. How they tackled it (The Solution)**
[Full summary of the methodology, approach, techniques, and tools used. Cover the key steps and any innovative aspects of their approach. Be specific about the methods.]

**C. Explain Like I'm 10 (ELI10)**
[Simple explanation using everyday analogies that a 10-year-old would understand. Make it fun and relatable.]

**C2. Explain for a College Student**
[Explanation with appropriate technical terminology but still accessible. Assume knowledge of basic engineering/science concepts. Include technical details that would help a student understand the actual mechanism.]

Write naturally — be as thorough as needed while staying concise. Every detail that matters should be included."""


# ── Step 3: Generate combined summary and key takeaway ──────────────────

COMBINED_SUMMARY_PROMPT = """You are a research paper summarizer creating a final synthesis.

**PAPER TITLE:** {paper_title}
**AUTHORS:** {authors}
**PAPER URL:** {paper_url}

**ALL PROBLEMS AND IDEAS SUMMARIZED:**
{all_summaries}

**YOUR TASK:**
Generate two final sections:

### 📝 Combined Summary
Write a single cohesive paragraph that synthesizes ALL the problems and solutions from this paper into a unified overview. Connect the dots between different contributions. This should give someone a complete picture of the paper in one paragraph.

### ⭐ Key Takeaway — MAKE NOTE OF THIS
Write one punchy paragraph highlighting the MOST impactful idea, solution, or finding from this paper. Explain why the reader should care about this specific contribution and what it means for the field. Write this like a quick note — something someone would want to highlight and remember.

### 🔗 Useful Links
- 📄 **Original Paper**: {paper_url}
{extra_links}

Make both sections informative and engaging. The Key Takeaway should feel like an expert's quick recommendation."""


# ── Step 4: Find relevant links for a topic ─────────────────────────────

FIND_LINKS_PROMPT = """Based on this research paper summary, suggest 2-4 relevant links that would help readers learn more. Only suggest real, well-known resources (don't make up URLs).

**Paper Title:** {paper_title}
**Summary:** {summary_text}

Suggest links in this format:
- 📝 **Blog/Article**: [Description](likely URL or "search for: query")
- 💻 **Code/Tool**: [Description](likely URL or "search for: query")  
- 📊 **Related Paper**: [Description](likely URL or "search for: query")
- 📚 **Tutorial**: [Description](likely URL or "search for: query")

Only include links you're confident about. It's better to suggest search queries than fake URLs."""
