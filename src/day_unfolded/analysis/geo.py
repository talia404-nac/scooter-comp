"""Deterministic geographic calculations. No LLM, no heuristics beyond math."""

from __future__ import annotations

from math import asin, atan2, cos, degrees, radians, sin, sqrt

from day_unfolded.domain.timeline import Direction

_EARTH_RADIUS_METERS = 6_371_000.0


def haversine_distance_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * _EARTH_RADIUS_METERS * asin(sqrt(a))


def bearing_degrees(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2, in degrees, 0-360 (0 = north)."""
    phi1, phi2 = radians(lat1), radians(lat2)
    d_lambda = radians(lon2 - lon1)
    x = sin(d_lambda) * cos(phi2)
    y = cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(d_lambda)
    theta = atan2(x, y)
    return (degrees(theta) + 360) % 360


_DIRECTIONS_BY_GRANULARITY: dict[int, list[Direction]] = {
    4: [Direction.N, Direction.E, Direction.S, Direction.W],
    8: [
        Direction.N,
        Direction.NE,
        Direction.E,
        Direction.SE,
        Direction.S,
        Direction.SW,
        Direction.W,
        Direction.NW,
    ],
}


def bearing_to_direction(bearing: float, granularity: int = 8) -> Direction:
    """Bucket a bearing into a compass direction. `granularity` must be a key
    of `_DIRECTIONS_BY_GRANULARITY` — only as fine as the data can support."""
    directions = _DIRECTIONS_BY_GRANULARITY.get(granularity)
    if directions is None:
        supported = sorted(_DIRECTIONS_BY_GRANULARITY)
        raise ValueError(
            f"unsupported direction_granularity: {granularity} (supported: {supported})"
        )
    sector = 360 / len(directions)
    idx = round(bearing / sector) % len(directions)
    return directions[idx]
