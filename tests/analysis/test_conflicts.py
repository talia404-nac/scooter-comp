from datetime import datetime, timedelta, timezone

from day_unfolded.analysis.conflicts import analyze_conflicts

T0 = datetime(2026, 9, 8, 9, 0, tzinfo=timezone.utc)
TEL_AVIV = (32.0853, 34.7818)
NETANYA = (32.3215, 34.8532)  # ~27km from Tel Aviv


def test_literal_duplicate_is_collapsed_but_traceable(make_observation, config):
    obs1 = make_observation(time=T0, lat=32.0, lon=34.0, source_id="DB_X", source_record_ref="rec-1")
    obs2 = make_observation(time=T0, lat=32.0, lon=34.0, source_id="DB_X", source_record_ref="rec-1")

    result = analyze_conflicts([obs1, obs2], config)

    assert len(result.deduped_observations) == 1
    assert len(result.duplicates) == 1
    assert result.duplicates[0].kept_observation_id == obs1.id
    assert result.duplicates[0].duplicate_observation_ids == [obs2.id]


def test_independent_sources_agreeing_are_corroboration_not_conflict(make_observation, config):
    obs1 = make_observation(time=T0, lat=TEL_AVIV[0], lon=TEL_AVIV[1], source_id="DB_X")
    obs2 = make_observation(
        time=T0 + timedelta(minutes=5), lat=TEL_AVIV[0] + 0.0005, lon=TEL_AVIV[1] + 0.0005, source_id="DB_Y"
    )

    result = analyze_conflicts([obs1, obs2], config)

    assert len(result.corroborations) == 1
    assert result.conflicts == []
    assert set(result.corroborations[0].observation_ids) == {obs1.id, obs2.id}
    assert set(result.corroborations[0].source_ids) == {"DB_X", "DB_Y"}
    # corroborating observations are NOT excluded from the normal timeline
    assert {o.id for o in result.segmentation_input} == {obs1.id, obs2.id}


def test_independent_sources_disagreeing_are_a_conflict_with_no_winner(make_observation, config):
    obs1 = make_observation(time=T0, lat=TEL_AVIV[0], lon=TEL_AVIV[1], source_id="DB_X")
    obs2 = make_observation(time=T0 + timedelta(minutes=1), lat=NETANYA[0], lon=NETANYA[1], source_id="DB_Y")

    result = analyze_conflicts([obs1, obs2], config)

    assert result.corroborations == []
    assert len(result.conflicts) == 1
    conflict_ids = {o.observation_id for o in result.conflicts[0].observations}
    assert conflict_ids == {obs1.id, obs2.id}
    # both sources are represented, neither is silently dropped
    conflict_sources = {o.source_id for o in result.conflicts[0].observations}
    assert conflict_sources == {"DB_X", "DB_Y"}
    # conflicting observations are excluded from the single-path segmentation stream
    assert result.segmentation_input == []
    # but never removed from the full observation record
    assert {o.id for o in result.deduped_observations} == {obs1.id, obs2.id}


def test_same_source_location_change_is_not_a_conflict(make_observation, config):
    # A single source reporting movement over time is ordinary movement,
    # not a cross-source disagreement.
    obs1 = make_observation(time=T0, lat=TEL_AVIV[0], lon=TEL_AVIV[1], source_id="DB_X")
    obs2 = make_observation(time=T0 + timedelta(minutes=1), lat=NETANYA[0], lon=NETANYA[1], source_id="DB_X")

    result = analyze_conflicts([obs1, obs2], config)

    assert result.conflicts == []
    assert result.corroborations == []
    assert {o.id for o in result.segmentation_input} == {obs1.id, obs2.id}


def test_observations_far_apart_in_time_are_not_clustered(make_observation, config):
    obs1 = make_observation(time=T0, lat=TEL_AVIV[0], lon=TEL_AVIV[1], source_id="DB_X")
    obs2 = make_observation(time=T0 + timedelta(hours=6), lat=NETANYA[0], lon=NETANYA[1], source_id="DB_Y")

    result = analyze_conflicts([obs1, obs2], config)

    assert result.conflicts == []
    assert result.corroborations == []
