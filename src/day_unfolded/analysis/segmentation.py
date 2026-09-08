"""Deterministic timeline segmentation.

Walks chronologically-sorted, non-conflicting observations and produces
stationary/moving segments. Three behaviors are deliberate, not incidental:

- Two observations separated by more than `gap_threshold_seconds` never
  become a MOVING segment, however far apart they are — that would assert
  continuous movement across a span we simply didn't observe. This must use
  the exact same threshold `gaps.find_gaps` uses to decide the same
  boundary is unobserved, so the two never both claim the same interval
  (one as "moving", the other as a "gap").
- An implausible jump (per anomalies.detect_anomaly) never becomes a MOVING
  segment with an asserted distance/speed/direction — that would be
  inventing a route. It's recorded in the returned anomalies list instead,
  and the timeline simply shows one segment ending and the next beginning.
- A MOVING segment only ever states "moving <direction>" (via
  TimelineSegment.direction) — it carries no notion of transportation mode.
  Whether that's driving, walking, or anything else is not something this
  layer is allowed to infer.
"""

from __future__ import annotations

from day_unfolded.analysis.anomalies import detect_anomaly
from day_unfolded.analysis.geo import bearing_degrees, bearing_to_direction, haversine_distance_meters
from day_unfolded.analysis.movement import classify_movement, compute_speed_mps
from day_unfolded.config.settings import AnalysisConfig
from day_unfolded.domain.observation import LocationObservation
from day_unfolded.domain.timeline import Anomaly, MovementState, TimelineSegment


def segment_timeline(
    observations: list[LocationObservation], config: AnalysisConfig
) -> tuple[list[TimelineSegment], list[Anomaly]]:
    located = sorted((o for o in observations if o.has_location), key=lambda o: o.start_time)
    if not located:
        return [], []

    anomalies: list[Anomaly] = []
    segments: list[TimelineSegment] = []

    seg_start_time = located[0].start_time
    seg_end_time = located[0].end_time
    anchor_lat, anchor_lon = located[0].latitude, located[0].longitude
    supporting_ids = [located[0].id]
    seg_source_ids = {located[0].source_id}

    def flush_stationary() -> None:
        segments.append(
            TimelineSegment(
                start_time=seg_start_time,
                end_time=seg_end_time,
                state=MovementState.STATIONARY if len(supporting_ids) > 1 else MovementState.UNKNOWN,
                representative_latitude=anchor_lat,
                representative_longitude=anchor_lon,
                supporting_observation_ids=list(supporting_ids),
                source_ids=sorted(seg_source_ids),
            )
        )

    for prev, obs in zip(located, located[1:]):
        uncovered_seconds = max(0.0, (obs.start_time - prev.end_time).total_seconds())
        if uncovered_seconds > config.gap_threshold_seconds:
            # Same threshold gaps.find_gaps uses for the same boundary — this
            # span is a gap, not movement, so no segment bridges it here.
            flush_stationary()
            seg_start_time, seg_end_time = obs.start_time, obs.end_time
            anchor_lat, anchor_lon = obs.latitude, obs.longitude
            supporting_ids = [obs.id]
            seg_source_ids = {obs.source_id}
            continue

        step_distance = haversine_distance_meters(
            prev.latitude, prev.longitude, obs.latitude, obs.longitude
        )
        elapsed_seconds = (obs.midpoint_time - prev.midpoint_time).total_seconds()

        anomaly = detect_anomaly(step_distance, elapsed_seconds, prev.id, obs.id, config)
        if anomaly is not None:
            anomalies.append(anomaly)
            flush_stationary()
            seg_start_time, seg_end_time = obs.start_time, obs.end_time
            anchor_lat, anchor_lon = obs.latitude, obs.longitude
            supporting_ids = [obs.id]
            seg_source_ids = {obs.source_id}
            continue

        state = classify_movement(step_distance, config)

        if state is MovementState.MOVING:
            flush_stationary()
            bearing = bearing_degrees(prev.latitude, prev.longitude, obs.latitude, obs.longitude)
            segments.append(
                TimelineSegment(
                    start_time=prev.end_time,
                    end_time=obs.start_time if obs.start_time >= prev.end_time else prev.end_time,
                    state=MovementState.MOVING,
                    direction=bearing_to_direction(bearing, config.direction_granularity),
                    distance_meters=step_distance,
                    speed_mps=compute_speed_mps(step_distance, elapsed_seconds),
                    supporting_observation_ids=[prev.id, obs.id],
                    source_ids=sorted({prev.source_id, obs.source_id}),
                )
            )
            seg_start_time, seg_end_time = obs.start_time, obs.end_time
            anchor_lat, anchor_lon = obs.latitude, obs.longitude
            supporting_ids = [obs.id]
            seg_source_ids = {obs.source_id}
            continue

        # STATIONARY step: only fold into the current segment if still within
        # stationary_radius of the segment's *original* anchor, so slow drift
        # across many small steps doesn't silently accumulate into one huge
        # "stationary" segment covering a real relocation.
        drift_from_anchor = haversine_distance_meters(anchor_lat, anchor_lon, obs.latitude, obs.longitude)
        if drift_from_anchor <= config.stationary_radius_meters:
            seg_end_time = obs.end_time
            supporting_ids.append(obs.id)
            seg_source_ids.add(obs.source_id)
        else:
            flush_stationary()
            seg_start_time, seg_end_time = obs.start_time, obs.end_time
            anchor_lat, anchor_lon = obs.latitude, obs.longitude
            supporting_ids = [obs.id]
            seg_source_ids = {obs.source_id}

    flush_stationary()
    segments.sort(key=lambda s: s.start_time)
    return segments, anomalies
