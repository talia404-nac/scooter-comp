"""Analysis configuration — every threshold used by the deterministic engine
lives here, never hardcoded inline.

IMPORTANT: the defaults below are PLACEHOLDERS, chosen only so the pipeline
and its tests are runnable before real source data exists. They are not
calibrated against real-world source precision (e.g. GPS vs. cell-tower-derived
uncertainty) and must be revisited once real sources are integrated.
"""

from __future__ import annotations

from pydantic import BaseModel


class AnalysisConfig(BaseModel):
    # Below this radius, movement between two observations is treated as
    # measurement noise rather than an actual relocation.
    stationary_radius_meters: float = 150.0

    # Below this straight-line distance between consecutive observations,
    # movement is not reported at all (folded into the stationary segment).
    min_movement_distance_meters: float = 50.0

    # Implied speed above this is flagged as an anomaly rather than reported
    # as ordinary movement. ~250 km/h, deliberately generous until real
    # source precision/uncertainty is known.
    max_reasonable_speed_mps: float = 70.0

    # An interval between consecutive observations longer than this becomes
    # a Gap instead of an interpolated/assumed segment.
    gap_threshold_seconds: int = 3600

    # 4, 8, or 16 — how finely bearing is bucketed into a compass direction.
    direction_granularity: int = 8

    # Two overlapping-time observations from different sources are treated as
    # corroborating (not conflicting) if within this distance of each other.
    conflict_distance_threshold_meters: float = 500.0

    # How much two observations' time windows may be offset and still be
    # considered "the same moment" for corroboration/conflict grouping.
    corroboration_time_window_seconds: int = 900


DEFAULT_CONFIG = AnalysisConfig()
