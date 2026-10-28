"""
Nebius Token Factory & NVIDIA Model Client Integration
======================================================
Provides authenticated, resilient API access to NVIDIA Nemotron models hosted
on Nebius Token Factory with graceful timeout, retry, structured action validation,
and health check capabilities.
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple


DEFAULT_NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3-super-120b-a12b"
FALLBACK_NVIDIA_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/Nemotron-3_5-Lightning",
    "nvidia/Nemotron-3.5-Super-VL",
    "nvidia/Llama-3_1-Nemotron-Ultra-253B-v1"
]


class NebiusClient:
    """
    Client for Nebius Token Factory (OpenAI-compatible chat completions API).
    Connects to NVIDIA Nemotron models with automatic retry, timeout control,
    and structured output extraction.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 25.0,
        max_retries: int = 2
    ):
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY")
        self.base_url = (base_url or os.getenv("NEBIUS_BASE_URL") or DEFAULT_NEBIUS_BASE_URL).rstrip("/")
        self.model = model or os.getenv("NEBIUS_MODEL") or DEFAULT_NVIDIA_MODEL
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    def is_configured(self) -> bool:
        """Checks if a genuine non-placeholder Nebius API key is set."""
        if not self.api_key:
            return False
        k = self.api_key.strip()
        if not k or k.startswith("placeholder") or k.startswith("your_nebius_key"):
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """Returns the client configuration state and connection metadata."""
        return {
            "provider": "Nebius Token Factory",
            "model": self.model,
            "base_url": self.base_url,
            "configured": self.is_configured,
            "api_key_set": bool(self.api_key),
            "masked_key": f"{self.api_key[:6]}...{self.api_key[-4:]}" if self.api_key and len(self.api_key) > 10 else "None"
        }

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        response_format: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Sends an authenticated chat completion request to Nebius Token Factory.
        Handles retry backoff, timeouts, and structured error responses.
        """
        if not self.is_configured:
            raise ValueError(
                "NEBIUS_API_KEY is not configured or contains a placeholder value. "
                "Set NEBIUS_API_KEY in environment or .env file."
            )

        endpoint = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_format:
            payload["response_format"] = response_format

        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "GuardianSwarm-AgentEngine/3.0"
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            start_time = time.time()
            try:
                req = urllib.request.Request(endpoint, data=data_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp_body = resp.read().decode("utf-8")
                    elapsed_ms = round((time.time() - start_time) * 1000, 2)
                    parsed = json.loads(resp_body)
                    
                    choice = parsed.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    content = message.get("content", "")
                    usage = parsed.get("usage", {})

                    return {
                        "success": True,
                        "content": content,
                        "model": parsed.get("model", self.model),
                        "usage": {
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0)
                        },
                        "latency_ms": elapsed_ms,
                        "raw": parsed
                    }

            except urllib.error.HTTPError as e:
                err_content = e.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {e.code}: {e.reason} - {err_content}"
                if e.code in [401, 403]:
                    # Authentication failure: fail immediately without retrying
                    break
                if e.code in [429, 500, 502, 503, 504] and attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                break
            except (urllib.error.URLError, TimeoutError) as e:
                last_error = f"Connection error: {str(e)}"
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                break
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                break

        return {
            "success": False,
            "error": last_error or "Unknown failure",
            "model": self.model,
            "configured": self.is_configured
        }
