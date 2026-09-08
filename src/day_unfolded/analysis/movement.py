"""Deterministic stationary/moving classification.

Two distinct thresholds are used deliberately (per config, never hardcoded):
`min_movement_distance_meters` decides whether the gap between two
consecutive observations counts as movement at all (below it: GPS/derivation
noise, not a real relocation). `stationary_radius_meters` is used downstream,
in segmentation, to decide whether a further observation still belongs to an
existing stationary segment's reference point.
"""

from __future__ import annotations

from day_unfolded.config.settings import AnalysisConfig
from day_unfolded.domain.timeline import MovementState


def compute_speed_mps(distance_meters: float, elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0:
        return float("inf") if distance_meters > 0 else 0.0
    return distance_meters / elapsed_seconds


def classify_movement(distance_meters: float, config: AnalysisConfig) -> MovementState:
    if distance_meters < config.min_movement_distance_meters:
        return MovementState.STATIONARY
    return MovementState.MOVING
