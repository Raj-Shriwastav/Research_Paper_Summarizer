"""
LLM Client — Unified client with provider fallback chain.

Tries Google AI Studio → Groq → Cloudflare → OpenRouter in sequence.
All use OpenAI-compatible API format, so switching is seamless.
"""

import logging
import json
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from openai import OpenAI

from backend.config import LLMConfig

logger = logging.getLogger(__name__)

# Models that do NOT support response_format=json_object.
# For these, we rely on prompt engineering to get JSON output.
_NO_JSON_MODE_MODELS = {
    "openrouter/free", # Since it routes to random models, we shouldn't force JSON format
    "poolside/laguna-xs.2:free",
}


@dataclass
class LLMProvider:
    """A single LLM provider configuration."""
    name: str
    api_key: str
    base_url: str
    model: str
    max_retries: int = 2
    timeout: int = 120


class LLMClient:
    """
    Unified LLM client with automatic provider fallback.

    Provider priority: DeepSeek → Google AI Studio → Groq → Cloudflare → OpenRouter
    All use OpenAI-compatible API, so the interface is identical.
    """

    def __init__(self, config: LLMConfig):
        self.providers: List[LLMProvider] = []
        self._clients: Dict[str, OpenAI] = {}
        self._current_provider_index = 0

        # 1. Google AI Studio (Gemini Models Priority)
        if config.google_api_key:
            google_models = [
                "gemini-3.1-flash-lite",
                "gemma-4-31b-it"                
            ]
            for model in google_models:
                self.providers.append(LLMProvider(
                    name=f"Google AI Studio ({model})",
                    api_key=config.google_api_key,
                    base_url=config.google_base_url,
                    model=model,
                ))

        # 2. Groq model hierarchy
        if config.groq_api_key:
            groq_models =[
                "openai/gpt-oss-120b",
                "qwen/qwen3-32b",
                "openai/gpt-oss-20b"
            ]
            for model in groq_models:
                self.providers.append(LLMProvider(
                    name=f"Groq ({model})",
                    api_key=config.groq_api_key,
                    base_url=config.groq_base_url,
                    model=model,
                ))
            
        # 3. OpenRouter model hierarchy
        if config.openrouter_api_key:
            openrouter_models =[
                "deepseek/deepseek-v4-flash:free",
                "openai/gpt-oss-120b:free",
                "nousresearch/hermes-3-llama-3.1-405b:free",
                "meta-llama/llama-3.3-70b-instruct:free",
                "google/gemma-4-31b-it:free",
                "qwen/qwen3-next-80b-a3b-instruct:free",
                "google/gemma-4-26b-a4b-it:free",
                "meta-llama/llama-3.2-3b-instruct:free"
            ]
            for model in openrouter_models:
                self.providers.append(LLMProvider(
                    name=f"OpenRouter ({model})",
                    api_key=config.openrouter_api_key,
                    base_url=config.openrouter_base_url,
                    model=model,
                ))


        if not self.providers:
            raise ValueError(
                "No LLM API keys configured! Please add at least one "
                "API key to your .env file."
            )

        logger.info(
            f"LLM Client initialized with {len(self.providers)} providers: "
            f"{[p.name for p in self.providers]}"
        )

    def _get_client(self, provider: LLMProvider) -> OpenAI:
        """Get or create an OpenAI client for a provider."""
        if provider.name not in self._clients:
            self._clients[provider.name] = OpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
                timeout=provider.timeout,
            )
        return self._clients[provider.name]

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> Optional[str]:
        """
        Send a chat completion request with automatic provider fallback.
        
        Args:
            messages: List of message dicts with "role" and "content" keys.
            temperature: Creativity level (0.0 = deterministic, 1.0 = creative).
            max_tokens: Maximum response length.
            json_mode: If True, request JSON output format.
            
        Returns:
            The assistant's response text, or None if all providers fail.
        """
        last_error = None
        start_index = self._current_provider_index
        num_providers = len(self.providers)

        for i in range(num_providers):
            idx = (start_index + i) % num_providers
            provider = self.providers[idx]
            
            try:
                response = self._call_provider(
                    provider, messages, temperature, max_tokens, json_mode
                )
                if response:
                    # Success! Advance the index for round-robin load balancing
                    self._current_provider_index = (idx + 1) % num_providers
                    return response
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Provider {provider.name} failed/exhausted ({e}). "
                    f"Instantly rotating to next provider..."
                )
                continue

        # Record when all providers fail
        from backend.utils import log_failure
        log_failure(
            error_type="All LLM Providers Failed",
            message="No configured LLM providers were able to return a response.",
            details=f"Last error encountered: {str(last_error)}"
        )
        logger.error(
            f"All LLM providers failed. Last error: {last_error}"
        )
        return None

    def _call_provider(
        self,
        provider: LLMProvider,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> Optional[str]:
        """Make a single API call to a specific provider."""
        client = self._get_client(provider)

        kwargs: Dict[str, Any] = {
            "model": provider.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Only set json_mode if the model supports it
        use_json_mode = json_mode and provider.model not in _NO_JSON_MODE_MODELS
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(provider.max_retries + 1):
            try:
                logger.debug(
                    f"Calling {provider.name} ({provider.model}), "
                    f"attempt {attempt + 1}"
                )
                response = client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content

                if content:
                    logger.info(
                        f"✅ {provider.name} responded "
                        f"({len(content)} chars)"
                    )
                    return content.strip()
                else:
                    logger.warning(
                        f"{provider.name} returned empty response"
                    )

            except Exception as e:
                error_str = str(e).lower()

                # 402 Insufficient Credits or 404 No Endpoint — skip immediately
                if "402" in error_str or "404" in error_str:
                    raise

                # JSON mode not supported — retry without it
                if json_mode and ("json" in error_str and "not supported" in error_str):
                    logger.warning(
                        f"{provider.name} does not support json_mode. "
                        f"Retrying without it..."
                    )
                    kwargs.pop("response_format", None)
                    continue

                # Rate limit / Quota — raise immediately to trigger instant round-robin fallback
                if any(x in error_str for x in ["rate", "429", "503", "quota"]):
                    logger.warning(
                        f"{provider.name} rate limited or out of quota. Triggering instant rotation."
                    )
                    raise e

                # Other errors — raise to trigger fallback
                raise

        return None

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> Optional[Dict[str, Any]]:
        """
        Send a chat request expecting JSON output.
        Automatically parses the response.
        """
        response = self.chat(
            messages, temperature, max_tokens, json_mode=True
        )
        if not response:
            return None

        # Try to parse JSON from the response
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Sometimes the model wraps JSON in markdown code blocks
            cleaned = response
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]

            try:
                return json.loads(cleaned.strip())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON response: {e}")
                logger.debug(f"Raw response: {response[:500]}")
                return None
