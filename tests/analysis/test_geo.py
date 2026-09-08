import pytest

from day_unfolded.analysis.geo import bearing_degrees, bearing_to_direction, haversine_distance_meters
from day_unfolded.domain.timeline import Direction

TEL_AVIV = (32.0853, 34.7818)
NETANYA = (32.3215, 34.8532)  # roughly north of Tel Aviv


def test_haversine_zero_distance_for_identical_points():
    assert haversine_distance_meters(*TEL_AVIV, *TEL_AVIV) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance_tel_aviv_netanya():
    # ~27km apart
    d = haversine_distance_meters(*TEL_AVIV, *NETANYA)
    assert 25_000 < d < 30_000


def test_haversine_symmetric():
    d1 = haversine_distance_meters(*TEL_AVIV, *NETANYA)
    d2 = haversine_distance_meters(*NETANYA, *TEL_AVIV)
    assert d1 == pytest.approx(d2)


def test_bearing_due_north():
    bearing = bearing_degrees(0.0, 0.0, 1.0, 0.0)
    assert bearing == pytest.approx(0.0, abs=1e-6)


def test_bearing_due_east():
    bearing = bearing_degrees(0.0, 0.0, 0.0, 1.0)
    assert bearing == pytest.approx(90.0, abs=1e-6)


def test_bearing_due_south():
    bearing = bearing_degrees(0.0, 0.0, -1.0, 0.0)
    assert bearing == pytest.approx(180.0, abs=1e-6)


def test_bearing_due_west():
    bearing = bearing_degrees(0.0, 0.0, 0.0, -1.0)
    assert bearing == pytest.approx(270.0, abs=1e-6)


@pytest.mark.parametrize(
    "bearing,expected",
    [
        (0, Direction.N),
        (44, Direction.NE),
        (90, Direction.E),
        (134, Direction.SE),
        (180, Direction.S),
        (224, Direction.SW),
        (270, Direction.W),
        (314, Direction.NW),
        (359, Direction.N),
    ],
)
def test_bearing_to_direction_8_point(bearing, expected):
    assert bearing_to_direction(bearing, granularity=8) == expected


@pytest.mark.parametrize(
    "bearing,expected",
    [(0, Direction.N), (89, Direction.E), (180, Direction.S), (270, Direction.W)],
)
def test_bearing_to_direction_4_point(bearing, expected):
    assert bearing_to_direction(bearing, granularity=4) == expected


def test_unsupported_granularity_raises():
    with pytest.raises(ValueError):
        bearing_to_direction(90, granularity=16)
