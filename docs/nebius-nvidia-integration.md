# Nebius Token Factory × NVIDIA Model Integration Guide

### Overview
Guardian Swarm integrates **Nebius Token Factory** as the high-throughput inference backbone, executing open-source **NVIDIA Nemotron** models for autonomous reasoning, planning, tool selection, and evidence verification.

### Supported NVIDIA Models
| Model Identifier | Architecture | Context Window | Recommended Role |
| :--- | :--- | :--- | :--- |
| `nvidia/nemotron-3-super-120b-a12b` | Hybrid MoE (12B active) | 131,072 | Multi-agent reasoning, structured planning & tool selection |
| `nvidia/Nemotron-3_5-Lightning` | Dense Accelerated | 65,536 | Low-latency verification, rapid telemetry checks |
| `nvidia/Nemotron-3.5-Super-VL` | Multimodal Vision-Language | 131,072 | Document analysis, structured charts & code reasoning |
| `nvidia/Llama-3_1-Nemotron-Ultra-253B-v1` | Ultra-Capacity MoE | 131,072 | Complex enterprise arbitration & policy debate |

### Configuration
1. Obtain an API key from the [Nebius Token Factory Console](https://tokenfactory.nebius.com/).
2. Set the environment variable in your local `.env`:
```bash
NEBIUS_API_KEY=your_actual_nebius_api_key
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
NEBIUS_MODEL=nvidia/nemotron-3-super-120b-a12b
```

### Authentication & Provider Architecture
- **Client Implementation:** Located at `guardian_swarm.providers.nebius_client.NebiusClient`.
- **Fault-Tolerance:** Includes automated linear retry backoff for rate limits (HTTP 429) and upstream server errors (HTTP 502/503/504), configurable request timeouts (25s default), and structured exception handling.
- **Diagnostics & Status:** Runtime connection state is reported by `GET /api/provider/status`, reflecting actual connection parameters without exposing raw credentials.
