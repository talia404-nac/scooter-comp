from day_unfolded.analysis.anomalies import detect_anomaly


def test_reasonable_speed_is_not_anomalous(config):
    # 1000m in 60s = ~16.7 m/s, well under the default max
    anomaly = detect_anomaly(1000.0, 60.0, "obs-a", "obs-b", config)
    assert anomaly is None


def test_impossible_speed_is_flagged(config):
    # Tel Aviv to Eilat (~300km) in 5 minutes
    anomaly = detect_anomaly(300_000.0, 300.0, "obs-a", "obs-b", config)
    assert anomaly is not None
    assert anomaly.from_observation_id == "obs-a"
    assert anomaly.to_observation_id == "obs-b"
    assert anomaly.implied_speed_mps > config.max_reasonable_speed_mps


def test_anomaly_does_not_mutate_inputs(config):
    anomaly = detect_anomaly(300_000.0, 300.0, "obs-a", "obs-b", config)
    assert anomaly.distance_meters == 300_000.0
    assert anomaly.elapsed_seconds == 300.0
    assert anomaly.max_reasonable_speed_mps == config.max_reasonable_speed_mps
