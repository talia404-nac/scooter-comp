import pytest

from day_unfolded.sources.contact_registry import ContactSourceRegistry
from day_unfolded.sources.registry import SourceConfig


def _config(source_id: str) -> SourceConfig:
    return SourceConfig(
        id=source_id,
        name=source_id,
        description="test contact source",
        interpretation_rules="n/a",
        scooter_id_rules="n/a",
        timestamp_rules="n/a",
        location_rules="n/a",
        limitations="n/a",
    )


class _Adapter:
    def __init__(self, source_id: str):
        self.source_id = source_id

    def fetch(self, scooter_id, window):
        return []

    def to_events(self, records):
        return []


def test_register_and_retrieve():
    registry = ContactSourceRegistry()
    registry.register(_config("DB_CALLS"), _Adapter("DB_CALLS"))

    assert registry.source_ids() == ["DB_CALLS"]
    assert registry.get_config("DB_CALLS").id == "DB_CALLS"
    assert registry.get_adapter("DB_CALLS").source_id == "DB_CALLS"
    assert len(registry.all_adapters()) == 1


def test_mismatched_ids_rejected():
    registry = ContactSourceRegistry()
    with pytest.raises(ValueError):
        registry.register(_config("DB_CALLS"), _Adapter("DB_SMS"))


def test_duplicate_registration_rejected():
    registry = ContactSourceRegistry()
    registry.register(_config("DB_CALLS"), _Adapter("DB_CALLS"))
    with pytest.raises(ValueError):
        registry.register(_config("DB_CALLS"), _Adapter("DB_CALLS"))


def test_empty_registry():
    registry = ContactSourceRegistry()
    assert registry.source_ids() == []
    assert registry.all_adapters() == []


def test_adapters_for_returns_only_requested_subset():
    registry = ContactSourceRegistry()
    registry.register(_config("DB_CALLS"), _Adapter("DB_CALLS"))
    registry.register(_config("DB_SMS"), _Adapter("DB_SMS"))

    assert [a.source_id for a in registry.adapters_for(["DB_SMS"])] == ["DB_SMS"]
