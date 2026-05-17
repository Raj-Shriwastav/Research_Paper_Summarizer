"""
Topic Manager — Maps user topics to API query parameters with synonym expansion.

Expands user-entered topics like "AI Safety" into related arXiv categories
and Semantic Scholar keywords to cast a wider net for relevant papers.
"""

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class TopicQuery:
    """Expanded topic with all search parameters."""
    name: str
    keywords: List[str] = field(default_factory=list)
    arxiv_categories: List[str] = field(default_factory=list)


# ── Curated topic → expansion map ──────────────────────────────────────────
# Each topic maps to related keywords and arXiv categories.
# This is the "synonym expansion" the user requested.

TOPIC_EXPANSIONS: Dict[str, dict] = {
    # ── Computer Science / AI ──
    "artificial intelligence": {
        "keywords": [
            "artificial intelligence", "machine learning", "deep learning",
            "neural network", "transformer", "large language model", "LLM",
            "reinforcement learning", "natural language processing",
            "computer vision", "generative AI",
        ],
        "arxiv": ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.NE"],
    },
    "machine learning": {
        "keywords": [
            "machine learning", "deep learning", "neural network",
            "supervised learning", "unsupervised learning", "transfer learning",
            "model training", "gradient descent", "optimization",
            "feature engineering", "ensemble methods",
        ],
        "arxiv": ["cs.LG", "cs.AI", "stat.ML"],
    },
    "natural language processing": {
        "keywords": [
            "natural language processing", "NLP", "text mining",
            "sentiment analysis", "language model", "tokenization",
            "named entity recognition", "machine translation",
            "question answering", "text generation",
        ],
        "arxiv": ["cs.CL", "cs.AI", "cs.IR"],
    },
    "computer vision": {
        "keywords": [
            "computer vision", "image recognition", "object detection",
            "image segmentation", "convolutional neural network", "CNN",
            "visual transformer", "ViT", "image generation",
            "video understanding", "3D vision",
        ],
        "arxiv": ["cs.CV", "cs.AI", "cs.LG"],
    },
    "ai safety": {
        "keywords": [
            "AI safety", "AI alignment", "RLHF",
            "reward hacking", "AI ethics", "responsible AI",
            "interpretability", "explainable AI", "robustness",
            "adversarial attacks", "AI governance",
        ],
        "arxiv": ["cs.AI", "cs.CL", "cs.LG", "cs.CY"],
    },
    "robotics": {
        "keywords": [
            "robotics", "robot learning", "manipulation",
            "autonomous navigation", "robot control", "sim-to-real",
            "motion planning", "SLAM", "human-robot interaction",
            "embodied AI", "legged locomotion",
        ],
        "arxiv": ["cs.RO", "cs.AI", "cs.SY"],
    },
    # ── Electrical Engineering ──
    "electrical engineering": {
        "keywords": [
            "electrical engineering", "circuit design", "VLSI",
            "signal processing", "power systems", "embedded systems",
            "semiconductor", "FPGA", "analog design",
            "digital systems", "IoT",
        ],
        "arxiv": ["eess.SP", "eess.SY", "cs.AR"],
    },
    # ── Mechanical Engineering ──
    "mechanical engineering": {
        "keywords": [
            "mechanical engineering", "fluid dynamics", "thermodynamics",
            "finite element analysis", "FEA", "computational mechanics",
            "materials science", "manufacturing", "CAD/CAM",
            "structural analysis", "heat transfer",
        ],
        "arxiv": ["physics.flu-dyn", "cond-mat.mtrl-sci", "physics.app-ph"],
    },
    # ── Civil Engineering ──
    "civil engineering": {
        "keywords": [
            "civil engineering", "structural engineering", "geotechnical",
            "construction management", "transportation engineering",
            "earthquake engineering", "concrete", "steel structures",
            "bridge design", "environmental engineering",
        ],
        "arxiv": ["physics.app-ph", "physics.geo-ph"],
    },
    # ── Biomedical Engineering ──
    "biomedical engineering": {
        "keywords": [
            "biomedical engineering", "medical imaging", "biomechanics",
            "tissue engineering", "prosthetics", "biosensors",
            "drug delivery", "neural engineering", "bioinformatics",
            "clinical trials", "wearable health",
        ],
        "arxiv": ["q-bio.QM", "physics.med-ph", "cs.AI"],
    },
    # ── Data Science ──
    "data science": {
        "keywords": [
            "data science", "big data", "data mining",
            "statistical analysis", "data visualization", "predictive modeling",
            "recommendation systems", "anomaly detection",
            "time series", "graph analytics",
        ],
        "arxiv": ["cs.LG", "stat.ML", "cs.DB", "cs.IR"],
    },
    # ── Cybersecurity ──
    "cybersecurity": {
        "keywords": [
            "cybersecurity", "network security", "cryptography",
            "intrusion detection", "malware analysis", "vulnerability",
            "zero trust", "blockchain security", "privacy",
            "penetration testing", "threat intelligence",
        ],
        "arxiv": ["cs.CR", "cs.NI"],
    },
    # ── Software Engineering ──
    "software engineering": {
        "keywords": [
            "software engineering", "code generation", "software testing",
            "DevOps", "microservices", "API design",
            "software architecture", "CI/CD", "refactoring",
            "technical debt", "code review",
        ],
        "arxiv": ["cs.SE", "cs.PL"],
    },
}


def expand_topic(topic: str) -> TopicQuery:
    """
    Expand a user-entered topic into full search parameters.
    
    Performs fuzzy matching against known topics. If no exact match,
    tries substring matching. Falls back to using the raw topic as keywords.
    """
    topic_lower = topic.lower().strip()

    # Exact match
    if topic_lower in TOPIC_EXPANSIONS:
        exp = TOPIC_EXPANSIONS[topic_lower]
        return TopicQuery(
            name=topic,
            keywords=exp["keywords"],
            arxiv_categories=exp.get("arxiv", []),
        )

    # Substring match — find topics that contain the user's query or vice versa
    for key, exp in TOPIC_EXPANSIONS.items():
        if topic_lower in key or key in topic_lower:
            return TopicQuery(
                name=topic,
                keywords=exp["keywords"],
                arxiv_categories=exp.get("arxiv", []),
            )

    # Check if the topic matches any keyword in any expansion
    for key, exp in TOPIC_EXPANSIONS.items():
        keywords_lower = [k.lower() for k in exp["keywords"]]
        if topic_lower in keywords_lower:
            return TopicQuery(
                name=topic,
                keywords=exp["keywords"],
                arxiv_categories=exp.get("arxiv", []),
            )

    # Fallback — use the raw topic as-is
    return TopicQuery(
        name=topic,
        keywords=[topic],
        arxiv_categories=[],
    )


def get_all_available_topics() -> List[str]:
    """Return all available topic names for the user to choose from."""
    return [key.title() for key in TOPIC_EXPANSIONS.keys()]
