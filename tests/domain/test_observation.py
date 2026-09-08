from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from day_unfolded.domain.observation import LocationObservation, OriginType

NOW = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)


def _base(**overrides):
    fields = dict(
        scooter_id="p1",
        start_time=NOW,
        end_time=NOW,
        latitude=32.08,
        longitude=34.78,
        origin_type=OriginType.DIRECT,
        source_id="DB_X",
        source_record_ref="rec-1",
    )
    fields.update(overrides)
    return LocationObservation(**fields)


def test_direct_observation_is_valid():
    obs = _base()
    assert obs.origin_type is OriginType.DIRECT
    assert obs.derivation is None


def test_derived_observation_requires_derivation_rule():
    with pytest.raises(ValidationError):
        _base(origin_type=OriginType.DERIVED, derivation=None)


def test_derived_observation_with_rule_is_valid():
    obs = _base(origin_type=OriginType.DERIVED, derivation="cell_tower_lookup")
    assert obs.derivation == "cell_tower_lookup"


def test_direct_observation_must_not_carry_derivation():
    with pytest.raises(ValidationError):
        _base(origin_type=OriginType.DIRECT, derivation="cell_tower_lookup")


def test_lat_without_lon_rejected():
    with pytest.raises(ValidationError):
        _base(latitude=32.08, longitude=None)


def test_out_of_range_latitude_rejected():
    with pytest.raises(ValidationError):
        _base(latitude=200.0)


def test_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        _base(start_time=datetime(2026, 9, 8, 10, 0), end_time=datetime(2026, 9, 8, 10, 0))


def test_end_before_start_rejected():
    with pytest.raises(ValidationError):
        _base(start_time=NOW, end_time=NOW.replace(hour=9))


def test_provenance_fields_survive_round_trip():
    obs = _base(source_id="DB_X", source_record_ref="rec-42")
    dumped = obs.model_dump()
    assert dumped["source_id"] == "DB_X"
    assert dumped["source_record_ref"] == "rec-42"
    assert dumped["origin_type"] == "direct"
