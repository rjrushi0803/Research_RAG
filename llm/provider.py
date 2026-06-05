"""
Unified LLM provider interface using LiteLLM.
Supports Ollama, OpenAI, Anthropic, Google, Qwen, Mistral.
"""

import logging
import subprocess
import json
from typing import List, Dict, Optional

import litellm

from config import LLMConfig, OLLAMA_RESOURCE_GUIDE

logger = logging.getLogger(__name__)

# Disable litellm telemetry
litellm.telemetry = False


def configure_provider(llm_config: LLMConfig):
    """Configure the LLM provider credentials."""
    import os

    provider = llm_config.provider
    api_key = llm_config.api_key

    if provider == "openai":
        os.environ["OPENAI_API_KEY"] = api_key
    elif provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif provider == "google":
        os.environ["GEMINI_API_KEY"] = api_key
    elif provider == "mistral":
        os.environ["MISTRAL_API_KEY"] = api_key
    elif provider == "qwen":
        os.environ["DASHSCOPE_API_KEY"] = api_key
    elif provider == "ollama":
        base_url = llm_config.base_url or "http://localhost:11434"
        os.environ["OLLAMA_API_BASE"] = base_url


def get_model_string(llm_config: LLMConfig) -> str:
    """Get the LiteLLM model string for the given config."""
    provider = llm_config.provider
    model = llm_config.model_name

    prefix_map = {
        "openai": "",
        "anthropic": "anthropic/",
        "google": "gemini/",
        "mistral": "mistral/",
        "qwen": "openai/",
        "ollama": "ollama/",
    }

    prefix = prefix_map.get(provider, "")
    return f"{prefix}{model}"


def chat_completion(
    llm_config: LLMConfig,
    messages: List[Dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Get a chat completion from the configured LLM.
    Returns the assistant's response text.
    """
    configure_provider(llm_config)
    model = get_model_string(llm_config)

    try:
        response = litellm.completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"LLM completion error: {e}")
        raise


def get_ollama_models() -> List[str]:
    """Get list of locally installed Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return []

        models = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def get_ollama_resource_guide(model_name: str) -> Dict:
    """Get resource requirements for an Ollama model based on parameter count."""
    model_lower = model_name.lower()

    for size_range, guide in OLLAMA_RESOURCE_GUIDE.items():
        # Check if the model name contains a parameter count hint
        for size in size_range.split("-"):
            size_clean = size.strip().lower().replace("b", "")
            if size_clean in model_lower:
                return {"size_range": size_range, **guide}

    # Default: assume 7B class
    return {"size_range": "7B", **OLLAMA_RESOURCE_GUIDE["7B"]}


def validate_provider(llm_config: LLMConfig) -> Dict:
    """
    Validate the LLM provider configuration.
    Returns dict with 'valid' bool and 'message' string.
    """
    try:
        configure_provider(llm_config)
        model = get_model_string(llm_config)

        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "Say 'OK' if you can read this."}],
            max_tokens=10,
        )
        return {"valid": True, "message": "Provider configured successfully"}
    except Exception as e:
        return {"valid": False, "message": f"Validation failed: {str(e)}"}
