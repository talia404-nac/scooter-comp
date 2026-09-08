from datetime import datetime, timedelta, timezone

from day_unfolded.analysis.segmentation import segment_timeline
from day_unfolded.domain.timeline import MovementState

T0 = datetime(2026, 9, 8, 9, 0, tzinfo=timezone.utc)
TEL_AVIV = (32.0853, 34.7818)
NETANYA = (32.3215, 34.8532)
EILAT = (29.5577, 34.9519)


def test_close_observations_form_one_stationary_segment(make_observation, config):
    obs1 = make_observation(time=T0, lat=TEL_AVIV[0], lon=TEL_AVIV[1])
    obs2 = make_observation(time=T0 + timedelta(minutes=10), lat=TEL_AVIV[0] + 0.0001, lon=TEL_AVIV[1] + 0.0001)
    obs3 = make_observation(time=T0 + timedelta(minutes=20), lat=TEL_AVIV[0] + 0.0002, lon=TEL_AVIV[1] + 0.0002)

    segments, anomalies = segment_timeline([obs1, obs2, obs3], config)

    assert anomalies == []
    assert len(segments) == 1
    assert segments[0].state == MovementState.STATIONARY
    assert set(segments[0].supporting_observation_ids) == {obs1.id, obs2.id, obs3.id}


def test_gps_noise_does_not_trigger_movement(make_observation, config):
    obs1 = make_observation(time=T0, lat=TEL_AVIV[0], lon=TEL_AVIV[1])
    obs2 = make_observation(time=T0 + timedelta(minutes=5), lat=TEL_AVIV[0] + 0.00001, lon=TEL_AVIV[1] + 0.00001)

    segments, _ = segment_timeline([obs1, obs2], config)

    assert len(segments) == 1
    assert segments[0].state == MovementState.STATIONARY


def test_real_movement_produces_moving_segment_with_direction(make_observation, config):
    obs1 = make_observation(time=T0, lat=TEL_AVIV[0], lon=TEL_AVIV[1])
    obs2 = make_observation(time=T0 + timedelta(minutes=30), lat=NETANYA[0], lon=NETANYA[1])

    segments, anomalies = segment_timeline([obs1, obs2], config)

    assert anomalies == []
    moving = [s for s in segments if s.state == MovementState.MOVING]
    assert len(moving) == 1
    assert moving[0].direction is not None
    assert moving[0].distance_meters > 20_000
    assert moving[0].speed_mps > 0


def test_impossible_jump_is_anomaly_not_a_moving_segment(make_observation, config):
    obs1 = make_observation(time=T0, lat=TEL_AVIV[0], lon=TEL_AVIV[1])
    obs2 = make_observation(time=T0 + timedelta(seconds=5), lat=EILAT[0], lon=EILAT[1])

    segments, anomalies = segment_timeline([obs1, obs2], config)

    assert len(anomalies) == 1
    assert anomalies[0].from_observation_id == obs1.id
    assert anomalies[0].to_observation_id == obs2.id

    moving = [s for s in segments if s.state == MovementState.MOVING]
    assert moving == [], "an implausible jump must never be reported as ordinary movement"
    # both observations still show up as their own segments — nothing is dropped
    assert len(segments) == 2


def test_segments_are_chronologically_ordered(make_observation, config):
    obs1 = make_observation(time=T0, lat=TEL_AVIV[0], lon=TEL_AVIV[1])
    obs2 = make_observation(time=T0 + timedelta(minutes=30), lat=NETANYA[0], lon=NETANYA[1])
    obs3 = make_observation(time=T0 + timedelta(minutes=60), lat=NETANYA[0] + 0.0001, lon=NETANYA[1] + 0.0001)

    segments, _ = segment_timeline([obs3, obs1, obs2], config)  # deliberately shuffled input

    starts = [s.start_time for s in segments]
    assert starts == sorted(starts)


def test_no_observations_returns_empty(config):
    segments, anomalies = segment_timeline([], config)
    assert segments == []
    assert anomalies == []


def test_unlocated_observations_are_ignored(make_observation, config):
    obs1 = make_observation(time=T0, lat=None, lon=None)
    segments, anomalies = segment_timeline([obs1], config)
    assert segments == []
    assert anomalies == []
