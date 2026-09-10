"""The source registry: configuration/documentation for each source, paired
with its adapter implementation.

`SourceConfig` deliberately mirrors the questionnaire a source owner must
answer before a source can be integrated (identity, meaning, scooter-matching,
time, location-derivation, limitations). Nothing here is invented — every
field is populated verbatim from what the source owner provides. The
registry ships empty; it is populated once real sources are documented.
"""

from __future__ import annotations

from pydantic import BaseModel

from day_unfolded.sources.base import SourceAdapter


class SourceConfig(BaseModel):
    # Identity
    id: str
    name: str
    doc_url: str | None = None
    description: str

    # Meaning / interpretation, verbatim from the source owner — not guessed.
    interpretation_rules: str
    scooter_id_rules: str
    timestamp_rules: str
    location_rules: str
    limitations: str

    supported_event_types: list[str] = []


class SourceRegistry:
    def __init__(self) -> None:
        self._configs: dict[str, SourceConfig] = {}
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, config: SourceConfig, adapter: SourceAdapter) -> None:
        if config.id != adapter.source_id:
            raise ValueError(
                f"SourceConfig.id ({config.id!r}) must match "
                f"SourceAdapter.source_id ({adapter.source_id!r})"
            )
        if config.id in self._configs:
            raise ValueError(f"source {config.id!r} is already registered")
        self._configs[config.id] = config
        self._adapters[config.id] = adapter

    def source_ids(self) -> list[str]:
        return list(self._configs.keys())

    def get_config(self, source_id: str) -> SourceConfig:
        return self._configs[source_id]

    def get_adapter(self, source_id: str) -> SourceAdapter:
        return self._adapters[source_id]

    def all_configs(self) -> list[SourceConfig]:
        return list(self._configs.values())

    def all_adapters(self) -> list[SourceAdapter]:
        return list(self._adapters.values())

    def adapters_for(self, source_ids: list[str]) -> list[SourceAdapter]:
        """Adapters for the requested ids that are actually registered, in
        registry order. Ids with no matching registration are silently
        dropped — callers that need to reject unknown ids (e.g. to surface a
        client-facing validation error) should check `source_ids()` first.
        """
        wanted = set(source_ids)
        return [adapter for sid, adapter in self._adapters.items() if sid in wanted]
