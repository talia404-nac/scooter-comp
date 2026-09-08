"""Orchestrates the full deterministic pipeline: query every registered
source independently, normalize to canonical observations, then run
duplicate/conflict/gap/segmentation analysis and assemble the structured
result.

A single source failing (unavailable, timeout, malformed data) never
prevents a result from the other sources — it is recorded in
`source_statuses` and the result is still produced from whatever succeeded.
"""

from __future__ import annotations

import logging
import time

from day_unfolded.analysis.conflicts import analyze_conflicts
from day_unfolded.analysis.gaps import find_gaps
from day_unfolded.analysis.segmentation import segment_timeline
from day_unfolded.config.settings import DEFAULT_CONFIG, AnalysisConfig
from day_unfolded.domain.observation import LocationObservation
from day_unfolded.domain.request import AnalysisRequest
from day_unfolded.domain.result import AnalysisResult, SourceStatus, SourceStatusCode
from day_unfolded.sources.base import SourceMalformedDataError, SourceTimeoutError, SourceUnavailableError
from day_unfolded.sources.registry import SourceRegistry

logger = logging.getLogger(__name__)


def _query_source(
    adapter, scooter_id: str, window
) -> tuple[list[LocationObservation], SourceStatus]:
    started = time.monotonic()
    try:
        records = adapter.fetch(scooter_id, window)
    except SourceTimeoutError as exc:
        logger.warning("source %s timed out: %s", adapter.source_id, exc)
        return [], SourceStatus(source_id=adapter.source_id, status=SourceStatusCode.TIMEOUT, error=str(exc))
    except SourceUnavailableError as exc:
        logger.warning("source %s unavailable: %s", adapter.source_id, exc)
        return [], SourceStatus(source_id=adapter.source_id, status=SourceStatusCode.FAILED, error=str(exc))

    if not records:
        logger.info("source %s: no data (%.3fs)", adapter.source_id, time.monotonic() - started)
        return [], SourceStatus(source_id=adapter.source_id, status=SourceStatusCode.NO_DATA, record_count=0)

    try:
        observations = adapter.to_observations(records)
    except SourceMalformedDataError as exc:
        logger.warning("source %s returned malformed data: %s", adapter.source_id, exc)
        return [], SourceStatus(
            source_id=adapter.source_id,
            status=SourceStatusCode.MALFORMED_DATA,
            record_count=len(records),
            error=str(exc),
        )

    duration = time.monotonic() - started
    logger.info(
        "source %s: %d records -> %d observations (%.3fs)",
        adapter.source_id,
        len(records),
        len(observations),
        duration,
    )
    return observations, SourceStatus(
        source_id=adapter.source_id,
        status=SourceStatusCode.OK,
        record_count=len(records),
        observation_count=len(observations),
    )


def run_analysis(
    request: AnalysisRequest,
    registry: SourceRegistry,
    config: AnalysisConfig = DEFAULT_CONFIG,
) -> AnalysisResult:
    window = request.window

    all_observations: list[LocationObservation] = []
    source_statuses: list[SourceStatus] = []

    for adapter in registry.all_adapters():
        observations, status = _query_source(adapter, request.scooter_id, window)
        all_observations.extend(observations)
        source_statuses.append(status)

    conflict_result = analyze_conflicts(all_observations, config)
    segments, anomalies = segment_timeline(conflict_result.segmentation_input, config)
    gaps = find_gaps(window, conflict_result.segmentation_input, config)

    logger.info(
        "analysis complete: %d observations, %d segments, %d gaps, %d conflicts, "
        "%d anomalies, %d duplicate groups",
        len(conflict_result.deduped_observations),
        len(segments),
        len(gaps),
        len(conflict_result.conflicts),
        len(anomalies),
        len(conflict_result.duplicates),
    )

    return AnalysisResult(
        scooter_id=request.scooter_id,
        window=window,
        observations=conflict_result.deduped_observations,
        segments=segments,
        gaps=gaps,
        conflicts=conflict_result.conflicts,
        anomalies=anomalies,
        duplicates=conflict_result.duplicates,
        corroborations=conflict_result.corroborations,
        source_statuses=source_statuses,
    )
