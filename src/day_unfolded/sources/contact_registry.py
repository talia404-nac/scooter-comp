"""The contact-source registry — mirrors sources.registry.SourceRegistry.

Reuses the same SourceConfig documentation questionnaire (identity, meaning,
scooter-matching, time, limitations): a call/message source still needs all
of that answered by its owner before it's wired in, exactly like a location
source. Kept as a separate registry (not a shared dict) so the location
pipeline can never accidentally iterate a contact adapter, or vice versa.
Ships empty; populated once a real source is documented.
"""

from __future__ import annotations

from day_unfolded.sources.contact_base import ContactSourceAdapter
from day_unfolded.sources.registry import SourceConfig


class ContactSourceRegistry:
    def __init__(self) -> None:
        self._configs: dict[str, SourceConfig] = {}
        self._adapters: dict[str, ContactSourceAdapter] = {}

    def register(self, config: SourceConfig, adapter: ContactSourceAdapter) -> None:
        if config.id != adapter.source_id:
            raise ValueError(
                f"SourceConfig.id ({config.id!r}) must match "
                f"ContactSourceAdapter.source_id ({adapter.source_id!r})"
            )
        if config.id in self._configs:
            raise ValueError(f"contact source {config.id!r} is already registered")
        self._configs[config.id] = config
        self._adapters[config.id] = adapter

    def source_ids(self) -> list[str]:
        return list(self._configs.keys())

    def get_config(self, source_id: str) -> SourceConfig:
        return self._configs[source_id]

    def get_adapter(self, source_id: str) -> ContactSourceAdapter:
        return self._adapters[source_id]

    def all_configs(self) -> list[SourceConfig]:
        return list(self._configs.values())

    def all_adapters(self) -> list[ContactSourceAdapter]:
        return list(self._adapters.values())

    def adapters_for(self, source_ids: list[str]) -> list[ContactSourceAdapter]:
        """Adapters for the requested ids that are actually registered, in
        registry order. Ids with no matching registration are silently
        dropped — callers that need to reject unknown ids should check
        `source_ids()` first."""
        wanted = set(source_ids)
        return [adapter for sid, adapter in self._adapters.items() if sid in wanted]
