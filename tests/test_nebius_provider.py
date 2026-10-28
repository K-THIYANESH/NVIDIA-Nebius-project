"""
Unit & Integration Tests for Nebius Token Factory Provider Client
==================================================================
Tests:
- Client configuration status
- Authenticated request structure
- Graceful handling of missing or invalid credentials
- Graceful handling of network timeouts / HTTP errors
- Response parsing & usage metrics extraction
"""

import pytest
from unittest.mock import patch, MagicMock
import urllib.error
import io
import json

from guardian_swarm.providers.nebius_client import NebiusClient
from guardian_swarm.providers.model_config import SUPPORTED_NVIDIA_MODELS, get_model_info


def test_nebius_client_unconfigured_by_default():
    client = NebiusClient(api_key=None)
    assert not client.is_configured
    status = client.get_status()
    assert status["configured"] is False
    assert status["provider"] == "Nebius Token Factory"


def test_nebius_client_configured_with_valid_key():
    client = NebiusClient(api_key="neb-test-token-key-1234567890", model="nvidia/nemotron-3-super-120b-a12b")
    assert client.is_configured
    status = client.get_status()
    assert status["configured"] is True
    assert status["model"] == "nvidia/nemotron-3-super-120b-a12b"
    assert "neb-te...7890" in status["masked_key"]


def test_nebius_client_raises_when_unconfigured_call_attempted():
    client = NebiusClient(api_key=None)
    with pytest.raises(ValueError) as exc:
        client.chat_completion(messages=[{"role": "user", "content": "hello"}])
    assert "NEBIUS_API_KEY is not configured" in str(exc.value)


@patch("urllib.request.urlopen")
def test_nebius_chat_completion_success(mock_urlopen):
    # Mock successful response from Nebius Token Factory endpoint
    mock_response = MagicMock()
    mock_payload = {
        "id": "chatcmpl-test-123",
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"action": "search_web", "query": "NVIDIA Nemotron"}'
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 42,
            "completion_tokens": 18,
            "total_tokens": 60
        }
    }
    mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    client = NebiusClient(api_key="valid-key-1234567890")
    res = client.chat_completion(messages=[{"role": "user", "content": "plan task"}])

    assert res["success"] is True
    assert "search_web" in res["content"]
    assert res["usage"]["total_tokens"] == 60
    assert res["model"] == "nvidia/nemotron-3-super-120b-a12b"


@patch("urllib.request.urlopen")
def test_nebius_chat_completion_auth_error(mock_urlopen):
    # Mock HTTP 401 Unauthorized
    err_body = io.BytesIO(b'{"error": {"message": "Invalid API key provided", "type": "auth_error"}}')
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://api.tokenfactory.nebius.com/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=err_body
    )

    client = NebiusClient(api_key="invalid-key-12345")
    res = client.chat_completion(messages=[{"role": "user", "content": "test"}])

    assert res["success"] is False
    assert "401" in res["error"]
    assert "Unauthorized" in res["error"]


@patch("urllib.request.urlopen")
def test_nebius_chat_completion_timeout(mock_urlopen):
    # Mock TimeoutError
    mock_urlopen.side_effect = TimeoutError("Connection timed out after 25 seconds")

    client = NebiusClient(api_key="valid-key-12345", max_retries=1)
    res = client.chat_completion(messages=[{"role": "user", "content": "test"}])

    assert res["success"] is False
    assert "Connection error" in res["error"]


def test_supported_nvidia_models_catalog():
    assert len(SUPPORTED_NVIDIA_MODELS) >= 3
    nemotron = get_model_info("nvidia/nemotron-3-super-120b-a12b")
    assert nemotron["name"] == "NVIDIA Nemotron 3 Super (120B MoE)"
    assert "planning" in nemotron["recommended_for"]
