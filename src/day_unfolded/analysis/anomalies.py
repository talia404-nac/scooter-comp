"""Implausible-movement detection.

Flags, never "fixes": an anomaly is reported alongside the two observations
that produced it. No intermediate route or corrected position is invented.
"""

from __future__ import annotations

from day_unfolded.analysis.movement import compute_speed_mps
from day_unfolded.config.settings import AnalysisConfig
from day_unfolded.domain.timeline import Anomaly


def detect_anomaly(
    distance_meters: float,
    elapsed_seconds: float,
    from_observation_id: str,
    to_observation_id: str,
    config: AnalysisConfig,
) -> Anomaly | None:
    speed = compute_speed_mps(distance_meters, elapsed_seconds)
    if speed <= config.max_reasonable_speed_mps:
        return None
    return Anomaly(
        from_observation_id=from_observation_id,
        to_observation_id=to_observation_id,
        distance_meters=distance_meters,
        elapsed_seconds=elapsed_seconds,
        implied_speed_mps=speed,
        max_reasonable_speed_mps=config.max_reasonable_speed_mps,
    )
