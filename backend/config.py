"""
Configuration loader — reads all settings from .env file.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


@dataclass
class LLMConfig:
    """LLM provider configuration with fallback chain."""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"

    google_api_key: str = ""
    google_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    google_model: str = "gemini-2.5-flash"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    cloudflare_api_key: str = ""
    cloudflare_account_id: str = ""
    cloudflare_model: str = "@cf/meta/llama-3.1-8b-instruct"


@dataclass
class EmailConfig:
    """Gmail SMTP configuration."""
    gmail_address: str = ""
    gmail_app_password: str = ""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587


@dataclass
class SupabaseConfig:
    """Supabase database configuration."""
    url: str = ""
    anon_key: str = ""
    service_key: str = ""


@dataclass
class PaperAPIConfig:
    """Paper discovery API configuration."""
    arxiv_base_url: str = "https://export.arxiv.org/api/query"
    # Max papers to process per daily run
    max_papers_per_day: int = 5
    # How many days back to look for papers
    lookback_days: int = 7


@dataclass
class AppConfig:
    """Main application configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    paper_api: PaperAPIConfig = field(default_factory=PaperAPIConfig)
    admin_email: str = ""
    # Directory to store downloaded PDFs temporarily
    pdf_cache_dir: str = ""

    def __post_init__(self):
        self.pdf_cache_dir = str(
            Path(__file__).resolve().parent.parent / "data" / "pdfs"
        )
        Path(self.pdf_cache_dir).mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    config = AppConfig(
        llm=LLMConfig(
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            google_api_key=os.getenv("GOOGLE_AI_API_KEY", ""),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            cloudflare_api_key=os.getenv("CLOUDFLARE_API_KEY", ""),
            cloudflare_account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID", ""),
        ),
        email=EmailConfig(
            gmail_address=os.getenv("GMAIL_ADDRESS", ""),
            gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", ""),
        ),
        supabase=SupabaseConfig(
            url=os.getenv("SUPABASE_URL", ""),
            anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
            service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
        ),
        paper_api=PaperAPIConfig(),
        admin_email=os.getenv("ADMIN_EMAIL", ""),
    )
    return config
