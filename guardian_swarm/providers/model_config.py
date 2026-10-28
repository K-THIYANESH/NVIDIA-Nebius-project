"""
Provider and Model Configuration
================================
Manages runtime configuration for Nebius Token Factory and NVIDIA models.
"""

import os
from typing import Dict, Any, List

# Primary NVIDIA Model configured on Nebius Token Factory
DEFAULT_NEBIUS_MODEL = os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
DEFAULT_NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")

SUPPORTED_NVIDIA_MODELS: List[Dict[str, Any]] = [
    {
        "id": "nvidia/nemotron-3-super-120b-a12b",
        "name": "NVIDIA Nemotron 3 Super (120B MoE)",
        "context_window": 131072,
        "description": "Recommended for multi-agent reasoning, structured planning, and tool selection",
        "recommended_for": ["planning", "verification", "tool_selection"]
    },
    {
        "id": "nvidia/Nemotron-3_5-Lightning",
        "name": "NVIDIA Nemotron 3.5 Lightning",
        "context_window": 65536,
        "description": "High-throughput, low-latency reasoning engine for fast verification loops",
        "recommended_for": ["fast_verification", "telemetry"]
    },
    {
        "id": "nvidia/Nemotron-3.5-Super-VL",
        "name": "NVIDIA Nemotron 3.5 Super VL",
        "context_window": 131072,
        "description": "Multimodal vision-language model for dense document analysis and code reasoning",
        "recommended_for": ["document_analysis", "multimodal"]
    },
    {
        "id": "nvidia/Llama-3_1-Nemotron-Ultra-253B-v1",
        "name": "NVIDIA Llama 3.1 Nemotron Ultra (253B)",
        "context_window": 131072,
        "description": "Ultra-capacity model for high-complexity enterprise governance arbitration",
        "recommended_for": ["deep_reasoning", "complex_arbitration"]
    }
]

def get_model_info(model_id: str) -> Dict[str, Any]:
    for m in SUPPORTED_NVIDIA_MODELS:
        if m["id"] == model_id:
            return m
    return {
        "id": model_id,
        "name": model_id,
        "context_window": 32768,
        "description": "Custom configured NVIDIA model",
        "recommended_for": ["general"]
    }
