from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LlmConfig:
    gateway_url: str
    model: str
    temperature: float
    timeout_seconds: float


def load_llm_config() -> LlmConfig:
    return LlmConfig(
        gateway_url=os.getenv("AGENT_GATEWAY_URL", "http://agent-gateway:8090").rstrip("/"),
        model=os.getenv("LLM_MODEL", "local"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
    )