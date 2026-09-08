from datetime import datetime, timedelta, timezone

from day_unfolded.analysis.gaps import find_gaps
from day_unfolded.domain.common import TimeWindow

T0 = datetime(2026, 9, 8, 9, 0, tzinfo=timezone.utc)


def test_no_gap_when_fully_covered(make_observation, config):
    window = TimeWindow(start=T0, end=T0 + timedelta(hours=2))
    obs1 = make_observation(time=T0, end_time=T0 + timedelta(hours=1), lat=32.0, lon=34.0)
    obs2 = make_observation(time=T0 + timedelta(hours=1), end_time=T0 + timedelta(hours=2), lat=32.0, lon=34.0)

    assert find_gaps(window, [obs1, obs2], config) == []


def test_gap_detected_between_observations_exceeding_threshold(make_observation, config):
    window = TimeWindow(start=T0, end=T0 + timedelta(hours=4))
    obs1 = make_observation(time=T0, lat=32.0, lon=34.0)
    obs2 = make_observation(time=T0 + timedelta(hours=4), lat=32.0, lon=34.0)

    gaps = find_gaps(window, [obs1, obs2], config)

    assert len(gaps) == 1
    assert gaps[0].start_time == obs1.end_time
    assert gaps[0].end_time == obs2.start_time


def test_small_gap_below_threshold_not_reported(make_observation, config):
    window = TimeWindow(start=T0, end=T0 + timedelta(minutes=30))
    obs1 = make_observation(time=T0, lat=32.0, lon=34.0)
    obs2 = make_observation(time=T0 + timedelta(minutes=10), lat=32.0, lon=34.0)

    assert find_gaps(window, [obs1, obs2], config) == []


def test_leading_and_trailing_gap_both_reported(make_observation, config):
    window = TimeWindow(start=T0, end=T0 + timedelta(hours=10))
    obs1 = make_observation(time=T0 + timedelta(hours=3), lat=32.0, lon=34.0)

    gaps = find_gaps(window, [obs1], config)

    assert len(gaps) == 2
    assert gaps[0].start_time == window.start
    assert gaps[0].end_time == obs1.start_time
    assert gaps[1].start_time == obs1.end_time
    assert gaps[1].end_time == window.end


def test_gap_model_carries_no_invented_location(config):
    window = TimeWindow(start=T0, end=T0 + timedelta(hours=2))
    gaps = find_gaps(window, [], config)
    assert len(gaps) == 1
    assert not hasattr(gaps[0], "latitude")
    assert not hasattr(gaps[0], "longitude")
