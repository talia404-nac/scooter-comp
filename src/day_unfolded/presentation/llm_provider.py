"""The presentation layer's only dependency on an LLM: a minimal, provider-
agnostic interface. No concrete implementation is wired here — the caller
supplies one (Claude, another vendor, or a test double)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return the model's text completion for a single prompt exchange.
        Implementations should not stream, retry silently, or mutate the
        prompts — the presenter is responsible for prompt construction."""
        ...
