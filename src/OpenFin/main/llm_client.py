"""OpenFin — Multi-Provider LLM Client Factory

Returns the appropriate LLM client based on the selected provider.
Providers are configured via environment variables set by the webapp server:

    LLM_PROVIDER  - Provider slug (openai, anthropic, gemini, openrouter, xai, deepseek, groq, together, mistral)
    LLM_API_KEY   - API key for the selected provider
    LLM_BASE_URL  - Base URL for the selected provider (auto-set by server)
    LLM_MODEL     - Model name (user's choice)

Supports both OpenAI-compatible and native (Anthropic, Gemini) APIs.
"""

import os
from typing import Optional


# ── Provider Registry ──────────────────────────────────────────────────────

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "openai_compat": True,
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "openai_compat": False,
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "openai_compat": False,
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "openai_compat": True,
    },
    "xai": {
        "name": "xAI (Grok)",
        "base_url": "https://api.x.ai/v1",
        "openai_compat": True,
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "openai_compat": True,
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "openai_compat": True,
    },
    "together": {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "openai_compat": True,
    },
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "openai_compat": True,
    },
}

# ── Default headers for OpenRouter rankings ──────────────────────────────

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/OpenFin",
    "X-Title": "OpenFin Financial Advisor",
}


def get_provider_info() -> dict:
    """Return the provider info dict for the current LLM_PROVIDER env var."""
    slug = os.environ.get("LLM_PROVIDER", "openrouter")
    return PROVIDERS.get(slug, PROVIDERS["openrouter"])


def get_llm_client():
    """Return the appropriate LLM client based on configured provider.

    Reads LLM_PROVIDER, LLM_API_KEY, LLM_BASE_URL from environment.
    For OpenAI-compatible providers, returns an OpenAI client.
    For Anthropic, returns an Anthropic client.
    For Gemini, returns a google-generativeai client.

    Raises ImportError if the required package is not installed.
    Raises ValueError if the API key is not set.
    """
    provider = get_provider_info()
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", provider["base_url"])

    if not api_key:
        raise ValueError(
            f"LLM API key is not set. Please configure your {provider['name']} "
            f"API key in the Config page."
        )

    if provider["openai_compat"]:
        return _get_openai_client(api_key, base_url, provider["name"])
    elif provider["name"] == "Anthropic":
        return _get_anthropic_client(api_key)
    elif provider["name"] == "Google Gemini":
        return _get_gemini_client(api_key)
    else:
        # Fallback to OpenAI client
        return _get_openai_client(api_key, base_url, provider["name"])


def get_model() -> str:
    """Return the configured model name."""
    return os.environ.get("LLM_MODEL", "openai/gpt-oss-120b:free")


def _get_openai_client(api_key: str, base_url: str, provider_name: str):
    """Create an OpenAI-compatible client."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai package is required. Install with: pip install openai"
        )

    headers = {}
    if "openrouter" in base_url.lower():
        headers.update(OPENROUTER_HEADERS)

    return OpenAI(api_key=api_key, base_url=base_url, default_headers=headers)


def _get_anthropic_client(api_key: str):
    """Create an Anthropic client."""
    try:
        from anthropic import Anthropic
    except ImportError:
        raise ImportError(
            "anthropic package is required. Install with: pip install anthropic"
        )
    return Anthropic(api_key=api_key)


def _get_gemini_client(api_key: str):
    """Create a Google Gemini client."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai package is required. Install with: "
            "pip install google-generativeai"
        )
    genai.configure(api_key=api_key)
    return genai
