import pytest

from day_unfolded.sources.registry import SourceConfig, SourceRegistry


def _config(source_id: str) -> SourceConfig:
    return SourceConfig(
        id=source_id,
        name=source_id,
        description="test source",
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

    def to_observations(self, records):
        return []


def test_register_and_retrieve():
    registry = SourceRegistry()
    registry.register(_config("DB_X"), _Adapter("DB_X"))

    assert registry.source_ids() == ["DB_X"]
    assert registry.get_config("DB_X").id == "DB_X"
    assert registry.get_adapter("DB_X").source_id == "DB_X"
    assert len(registry.all_adapters()) == 1


def test_mismatched_ids_rejected():
    registry = SourceRegistry()
    with pytest.raises(ValueError):
        registry.register(_config("DB_X"), _Adapter("DB_Y"))


def test_duplicate_registration_rejected():
    registry = SourceRegistry()
    registry.register(_config("DB_X"), _Adapter("DB_X"))
    with pytest.raises(ValueError):
        registry.register(_config("DB_X"), _Adapter("DB_X"))


def test_empty_registry():
    registry = SourceRegistry()
    assert registry.source_ids() == []
    assert registry.all_adapters() == []
