from __future__ import annotations

from ...config import Settings
from .base import LLMProvider


def get_provider(settings: Settings) -> LLMProvider:
    name = settings.llm_provider
    if name == "stub":
        from .stub import StubProvider

        return StubProvider()
    if name == "ollama-host":
        from .ollama import OllamaProvider

        return OllamaProvider(settings)
    if name == "hosted":
        from .hosted import HostedProvider

        return HostedProvider(settings)
    raise ValueError(
        "Unsupported LLM_PROVIDER; supported modes are stub, ollama-host and hosted"
    )
