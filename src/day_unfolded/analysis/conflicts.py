"""Duplicate / corroboration / conflict detection.

Three distinct outcomes for observations that relate to each other, per
spec: a literal duplicate (same record reported twice) is collapsed but its
provenance is retained; independent corroboration (different sources agree)
is recorded but never merged into one observation; contradiction (different
sources disagree) is recorded as a Conflict and no winner is picked — those
observations are excluded from the normal single-path segmentation stream
and surfaced to the customer as an explicit conflict instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from day_unfolded.analysis.geo import haversine_distance_meters
from day_unfolded.config.settings import AnalysisConfig
from day_unfolded.domain.observation import LocationObservation
from day_unfolded.domain.timeline import Conflict, ConflictObservationRef, CorroborationGroup, DuplicateGroup


@dataclass
class ConflictAnalysisResult:
    # All observations after collapsing literal duplicates, chronologically sorted.
    deduped_observations: list[LocationObservation]
    # deduped_observations minus anything caught up in a Conflict — this is
    # what segmentation should walk chronologically.
    segmentation_input: list[LocationObservation]
    duplicates: list[DuplicateGroup] = field(default_factory=list)
    corroborations: list[CorroborationGroup] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)


def _find_duplicates(
    observations: list[LocationObservation],
) -> tuple[list[LocationObservation], list[DuplicateGroup]]:
    groups: dict[tuple[str, str], list[LocationObservation]] = {}
    for obs in observations:
        groups.setdefault((obs.source_id, obs.source_record_ref), []).append(obs)

    kept: list[LocationObservation] = []
    duplicate_groups: list[DuplicateGroup] = []
    for group in groups.values():
        kept.append(group[0])
        if len(group) > 1:
            duplicate_groups.append(
                DuplicateGroup(
                    kept_observation_id=group[0].id,
                    duplicate_observation_ids=[o.id for o in group[1:]],
                )
            )
    return kept, duplicate_groups


def _cluster_by_time(
    observations: list[LocationObservation], window_seconds: int
) -> list[list[LocationObservation]]:
    """Chain-group observations whose midpoint times are within
    `window_seconds` of the previous observation in the (already
    time-sorted) list."""
    clusters: list[list[LocationObservation]] = []
    for obs in observations:
        if (
            clusters
            and (obs.midpoint_time - clusters[-1][-1].midpoint_time).total_seconds()
            <= window_seconds
        ):
            clusters[-1].append(obs)
        else:
            clusters.append([obs])
    return clusters


def _max_pairwise_distance_meters(observations: list[LocationObservation]) -> float:
    max_distance = 0.0
    for i in range(len(observations)):
        for j in range(i + 1, len(observations)):
            a, b = observations[i], observations[j]
            d = haversine_distance_meters(a.latitude, a.longitude, b.latitude, b.longitude)
            max_distance = max(max_distance, d)
    return max_distance


def analyze_conflicts(
    observations: list[LocationObservation], config: AnalysisConfig
) -> ConflictAnalysisResult:
    deduped, duplicate_groups = _find_duplicates(observations)
    deduped_sorted = sorted(deduped, key=lambda o: o.midpoint_time)

    located = [o for o in deduped_sorted if o.has_location]
    clusters = _cluster_by_time(located, config.corroboration_time_window_seconds)

    corroborations: list[CorroborationGroup] = []
    conflicts: list[Conflict] = []
    conflicted_ids: set[str] = set()

    for cluster in clusters:
        source_ids = {o.source_id for o in cluster}
        if len(source_ids) < 2:
            continue  # nothing to corroborate or conflict with

        if _max_pairwise_distance_meters(cluster) <= config.conflict_distance_threshold_meters:
            corroborations.append(
                CorroborationGroup(
                    start_time=min(o.start_time for o in cluster),
                    end_time=max(o.end_time for o in cluster),
                    observation_ids=[o.id for o in cluster],
                    source_ids=sorted(source_ids),
                )
            )
        else:
            conflicts.append(
                Conflict(
                    start_time=min(o.start_time for o in cluster),
                    end_time=max(o.end_time for o in cluster),
                    observations=[
                        ConflictObservationRef(
                            observation_id=o.id,
                            source_id=o.source_id,
                            latitude=o.latitude,
                            longitude=o.longitude,
                            time=o.midpoint_time,
                        )
                        for o in cluster
                    ],
                )
            )
            conflicted_ids.update(o.id for o in cluster)

    segmentation_input = [o for o in deduped_sorted if o.id not in conflicted_ids]

    return ConflictAnalysisResult(
        deduped_observations=deduped_sorted,
        segmentation_input=segmentation_input,
        duplicates=duplicate_groups,
        corroborations=corroborations,
        conflicts=conflicts,
    )
