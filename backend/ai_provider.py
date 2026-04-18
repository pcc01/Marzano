"""
AI Provider abstraction layer.
Currently wired to Anthropic. Swap to Ollama by changing AI_PROVIDER env var.
"""

import os
import json
import base64
import httpx
from typing import Optional
from enum import Enum


class ProviderType(str, Enum):
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


PROVIDER = ProviderType(os.getenv("AI_PROVIDER", "anthropic"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


async def call_ai(
    system_prompt: str,
    user_prompt: str,
    image_b64: Optional[str] = None,
    image_media_type: str = "image/jpeg",
    max_tokens: int = 2000,
) -> str:
    """
    Route to the configured AI provider and return the response text.
    Both providers receive identical prompts; only the wire format differs.
    """
    if PROVIDER == ProviderType.ANTHROPIC:
        return await _call_anthropic(system_prompt, user_prompt, image_b64, image_media_type, max_tokens)
    elif PROVIDER == ProviderType.OLLAMA:
        return await _call_ollama(system_prompt, user_prompt, image_b64, max_tokens)
    else:
        raise ValueError(f"Unknown AI provider: {PROVIDER}")


async def _call_anthropic(
    system_prompt: str,
    user_prompt: str,
    image_b64: Optional[str],
    image_media_type: str,
    max_tokens: int,
) -> str:
    content = []

    if image_b64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_media_type,
                "data": image_b64,
            }
        })

    content.append({"type": "text", "text": user_prompt})

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": content}],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def _call_ollama(
    system_prompt: str,
    user_prompt: str,
    image_b64: Optional[str],
    max_tokens: int,
) -> str:
    """
    Ollama /api/chat endpoint.
    Vision-capable models (llava, bakllava) accept images directly.
    """
    message = {"role": "user", "content": user_prompt}

    if image_b64:
        message["images"] = [image_b64]

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            message,
        ],
        "stream": False,
        "options": {"num_predict": max_tokens},
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]


def get_provider_info() -> dict:
    return {
        "provider": PROVIDER,
        "model": ANTHROPIC_MODEL if PROVIDER == ProviderType.ANTHROPIC else OLLAMA_MODEL,
        "vision_capable": True,
    }
