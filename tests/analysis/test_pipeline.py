from datetime import date, datetime, time as dt_time, timezone

import pytest

from day_unfolded.analysis.pipeline import UnknownSourceError, run_analysis
from day_unfolded.domain.contact import ContactChannel, CustomerContactEvent
from day_unfolded.domain.observation import OriginType
from day_unfolded.domain.request import AnalysisRequest
from day_unfolded.domain.result import SourceStatusCode
from day_unfolded.sources.base import SourceMalformedDataError, SourceTimeoutError, SourceUnavailableError
from day_unfolded.sources.contact_registry import ContactSourceRegistry
from day_unfolded.sources.registry import SourceConfig, SourceRegistry

T0 = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)


def _request(source_ids: list[str] | None = None) -> AnalysisRequest:
    return AnalysisRequest(
        scooter_id="p1",
        date=date(2026, 9, 8),
        start_time=dt_time(9, 0),
        end_time=dt_time(18, 0),
        timezone="UTC",
        source_ids=source_ids,
    )


def _source_config(source_id: str) -> SourceConfig:
    return SourceConfig(
        id=source_id,
        name=source_id,
        description="test fixture source",
        interpretation_rules="n/a",
        scooter_id_rules="n/a",
        timestamp_rules="n/a",
        location_rules="n/a",
        limitations="n/a",
    )


class FakeAdapter:
    """Test-only in-memory adapter. Not a stand-in for real source
    integration — it exists purely to exercise pipeline wiring."""

    def __init__(self, source_id, observations=None, fetch_error=None, malformed=False):
        self.source_id = source_id
        self._observations = observations or []
        self._fetch_error = fetch_error
        self._malformed = malformed

    def fetch(self, scooter_id, window):
        if self._fetch_error:
            raise self._fetch_error
        return list(self._observations)

    def to_observations(self, records):
        if self._malformed:
            raise SourceMalformedDataError("fixture-forced malformed data")
        return records


class FakeContactAdapter:
    """Test-only in-memory contact adapter, mirroring FakeAdapter."""

    def __init__(self, source_id, events=None, fetch_error=None, malformed=False):
        self.source_id = source_id
        self._events = events or []
        self._fetch_error = fetch_error
        self._malformed = malformed

    def fetch(self, scooter_id, window):
        if self._fetch_error:
            raise self._fetch_error
        return list(self._events)

    def to_events(self, records):
        if self._malformed:
            raise SourceMalformedDataError("fixture-forced malformed data")
        return records


def test_partial_source_failure_still_produces_result(make_observation, config):
    good_obs = make_observation(time=T0, lat=32.0, lon=34.0, source_id="DB_GOOD")
    registry = SourceRegistry()
    registry.register(_source_config("DB_GOOD"), FakeAdapter("DB_GOOD", observations=[good_obs]))
    registry.register(_source_config("DB_BAD"), FakeAdapter("DB_BAD", fetch_error=SourceUnavailableError("down")))

    result = run_analysis(_request(), registry, config)

    statuses = {s.source_id: s.status for s in result.source_statuses}
    assert statuses["DB_GOOD"] == SourceStatusCode.OK
    assert statuses["DB_BAD"] == SourceStatusCode.FAILED
    assert len(result.observations) == 1
    assert result.observations[0].source_id == "DB_GOOD"


def test_empty_source_result_is_no_data_not_failure(config):
    registry = SourceRegistry()
    registry.register(_source_config("DB_EMPTY"), FakeAdapter("DB_EMPTY", observations=[]))

    result = run_analysis(_request(), registry, config)

    assert result.source_statuses[0].status == SourceStatusCode.NO_DATA


def test_malformed_source_data_does_not_crash_pipeline(config):
    registry = SourceRegistry()
    registry.register(_source_config("DB_MALFORMED"), FakeAdapter("DB_MALFORMED", observations=[{"odd": "shape"}], malformed=True))

    result = run_analysis(_request(), registry, config)

    assert result.source_statuses[0].status == SourceStatusCode.MALFORMED_DATA
    assert result.observations == []


def test_timeout_is_recorded_distinctly_from_failure(config):
    registry = SourceRegistry()
    registry.register(_source_config("DB_SLOW"), FakeAdapter("DB_SLOW", fetch_error=SourceTimeoutError("too slow")))

    result = run_analysis(_request(), registry, config)

    assert result.source_statuses[0].status == SourceStatusCode.TIMEOUT


def test_empty_registry_returns_empty_result(config):
    result = run_analysis(_request(), SourceRegistry(), config)

    assert result.observations == []
    assert result.segments == []
    assert result.source_statuses == []


def test_provenance_survives_full_pipeline_run(make_observation, config):
    obs = make_observation(
        time=T0,
        lat=32.0,
        lon=34.0,
        source_id="DB_X",
        source_record_ref="rec-99",
        origin_type=OriginType.DERIVED,
        derivation="cell_tower_lookup",
    )
    registry = SourceRegistry()
    registry.register(_source_config("DB_X"), FakeAdapter("DB_X", observations=[obs]))

    result = run_analysis(_request(), registry, config)

    assert result.observations[0].source_id == "DB_X"
    assert result.observations[0].source_record_ref == "rec-99"
    assert result.observations[0].origin_type == OriginType.DERIVED
    assert result.observations[0].derivation == "cell_tower_lookup"
    assert result.segments[0].source_ids == ["DB_X"]


def test_source_ids_none_queries_every_registered_source(make_observation, config):
    obs_a = make_observation(time=T0, lat=32.0, lon=34.0, source_id="DB_A")
    obs_b = make_observation(time=T0, lat=32.0, lon=34.0, source_id="DB_B")
    registry = SourceRegistry()
    registry.register(_source_config("DB_A"), FakeAdapter("DB_A", observations=[obs_a]))
    registry.register(_source_config("DB_B"), FakeAdapter("DB_B", observations=[obs_b]))

    result = run_analysis(_request(source_ids=None), registry, config)

    assert {s.source_id for s in result.source_statuses} == {"DB_A", "DB_B"}


def test_source_ids_filters_to_only_the_chosen_sources(make_observation, config):
    obs_a = make_observation(time=T0, lat=32.0, lon=34.0, source_id="DB_A")
    obs_b = make_observation(time=T0, lat=32.0, lon=34.0, source_id="DB_B")
    registry = SourceRegistry()
    registry.register(_source_config("DB_A"), FakeAdapter("DB_A", observations=[obs_a]))
    registry.register(_source_config("DB_B"), FakeAdapter("DB_B", observations=[obs_b]))

    result = run_analysis(_request(source_ids=["DB_A"]), registry, config)

    assert {s.source_id for s in result.source_statuses} == {"DB_A"}
    assert result.observations[0].source_id == "DB_A"


def test_unknown_source_id_is_rejected(config):
    registry = SourceRegistry()
    registry.register(_source_config("DB_A"), FakeAdapter("DB_A"))

    with pytest.raises(UnknownSourceError):
        run_analysis(_request(source_ids=["DB_NOPE"]), registry, config)


def _contact_event(**overrides) -> CustomerContactEvent:
    fields = dict(
        scooter_id="p1",
        time=T0,
        channel=ContactChannel.CALL,
        summary="customer called",
        source_id="DB_CALLS",
        source_record_ref="call-1",
    )
    fields.update(overrides)
    return CustomerContactEvent(**fields)


def test_customer_contacts_are_queried_and_included(config):
    registry = SourceRegistry()
    contact_registry = ContactSourceRegistry()
    contact_registry.register(_source_config("DB_CALLS"), FakeContactAdapter("DB_CALLS", events=[_contact_event()]))

    result = run_analysis(_request(), registry, config, contact_registry=contact_registry)

    assert len(result.customer_contacts) == 1
    assert result.customer_contacts[0].source_id == "DB_CALLS"
    assert {s.source_id for s in result.source_statuses} == {"DB_CALLS"}


def test_customer_contacts_never_affect_segments_or_gaps(make_observation, config):
    good_obs = make_observation(time=T0, lat=32.0, lon=34.0, source_id="DB_LOC")
    registry = SourceRegistry()
    registry.register(_source_config("DB_LOC"), FakeAdapter("DB_LOC", observations=[good_obs]))
    contact_registry = ContactSourceRegistry()
    contact_registry.register(_source_config("DB_CALLS"), FakeContactAdapter("DB_CALLS", events=[_contact_event()]))

    with_contacts = run_analysis(_request(), registry, config, contact_registry=contact_registry)
    without_contacts = run_analysis(_request(), registry, config)

    assert with_contacts.segments == without_contacts.segments
    assert with_contacts.gaps == without_contacts.gaps
    assert len(with_contacts.customer_contacts) == 1
    assert without_contacts.customer_contacts == []


def test_source_ids_can_select_a_contact_source_only(make_observation, config):
    good_obs = make_observation(time=T0, lat=32.0, lon=34.0, source_id="DB_LOC")
    registry = SourceRegistry()
    registry.register(_source_config("DB_LOC"), FakeAdapter("DB_LOC", observations=[good_obs]))
    contact_registry = ContactSourceRegistry()
    contact_registry.register(_source_config("DB_CALLS"), FakeContactAdapter("DB_CALLS", events=[_contact_event()]))

    result = run_analysis(_request(source_ids=["DB_CALLS"]), registry, config, contact_registry=contact_registry)

    assert result.observations == []
    assert len(result.customer_contacts) == 1


def test_unknown_source_id_rejected_even_with_contact_registry_present(config):
    registry = SourceRegistry()
    registry.register(_source_config("DB_LOC"), FakeAdapter("DB_LOC"))
    contact_registry = ContactSourceRegistry()
    contact_registry.register(_source_config("DB_CALLS"), FakeContactAdapter("DB_CALLS"))

    with pytest.raises(UnknownSourceError):
        run_analysis(_request(source_ids=["NOPE"]), registry, config, contact_registry=contact_registry)
