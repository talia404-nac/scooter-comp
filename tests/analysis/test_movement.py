from day_unfolded.analysis.movement import classify_movement, compute_speed_mps
from day_unfolded.domain.timeline import MovementState


def test_small_distance_is_stationary_noise(config):
    state = classify_movement(config.min_movement_distance_meters - 1, config)
    assert state is MovementState.STATIONARY


def test_distance_at_or_above_threshold_is_moving(config):
    state = classify_movement(config.min_movement_distance_meters + 1, config)
    assert state is MovementState.MOVING


def test_compute_speed_normal_case():
    assert compute_speed_mps(100.0, 10.0) == 10.0


def test_compute_speed_zero_elapsed_nonzero_distance_is_infinite():
    assert compute_speed_mps(100.0, 0.0) == float("inf")


def test_compute_speed_zero_elapsed_zero_distance_is_zero():
    assert compute_speed_mps(0.0, 0.0) == 0.0
