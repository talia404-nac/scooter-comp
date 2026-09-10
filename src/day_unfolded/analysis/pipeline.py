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
from day_unfolded.domain.contact import CustomerContactEvent
from day_unfolded.domain.observation import LocationObservation
from day_unfolded.domain.request import AnalysisRequest
from day_unfolded.domain.result import AnalysisResult, SourceStatus, SourceStatusCode
from day_unfolded.sources.base import SourceMalformedDataError, SourceTimeoutError, SourceUnavailableError
from day_unfolded.sources.contact_registry import ContactSourceRegistry
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


class UnknownSourceError(ValueError):
    """Raised when a request names a source_id neither registry has."""


def _query_contact_source(
    adapter, scooter_id: str, window
) -> tuple[list[CustomerContactEvent], SourceStatus]:
    started = time.monotonic()
    try:
        records = adapter.fetch(scooter_id, window)
    except SourceTimeoutError as exc:
        logger.warning("contact source %s timed out: %s", adapter.source_id, exc)
        return [], SourceStatus(source_id=adapter.source_id, status=SourceStatusCode.TIMEOUT, error=str(exc))
    except SourceUnavailableError as exc:
        logger.warning("contact source %s unavailable: %s", adapter.source_id, exc)
        return [], SourceStatus(source_id=adapter.source_id, status=SourceStatusCode.FAILED, error=str(exc))

    if not records:
        logger.info("contact source %s: no data (%.3fs)", adapter.source_id, time.monotonic() - started)
        return [], SourceStatus(source_id=adapter.source_id, status=SourceStatusCode.NO_DATA, record_count=0)

    try:
        events = adapter.to_events(records)
    except SourceMalformedDataError as exc:
        logger.warning("contact source %s returned malformed data: %s", adapter.source_id, exc)
        return [], SourceStatus(
            source_id=adapter.source_id,
            status=SourceStatusCode.MALFORMED_DATA,
            record_count=len(records),
            error=str(exc),
        )

    duration = time.monotonic() - started
    logger.info(
        "contact source %s: %d records -> %d events (%.3fs)",
        adapter.source_id,
        len(records),
        len(events),
        duration,
    )
    return events, SourceStatus(
        source_id=adapter.source_id,
        status=SourceStatusCode.OK,
        record_count=len(records),
        observation_count=len(events),
    )


def _validate_source_ids(
    request: AnalysisRequest, registry: SourceRegistry, contact_registry: ContactSourceRegistry
) -> None:
    if request.source_ids is None:
        return
    known = set(registry.source_ids()) | set(contact_registry.source_ids())
    unknown = [sid for sid in request.source_ids if sid not in known]
    if unknown:
        raise UnknownSourceError(f"unknown source_id(s): {', '.join(unknown)}")


def _select_adapters(request: AnalysisRequest, registry: SourceRegistry) -> list:
    if request.source_ids is None:
        return registry.all_adapters()
    return registry.adapters_for(request.source_ids)


def _select_contact_adapters(request: AnalysisRequest, contact_registry: ContactSourceRegistry) -> list:
    if request.source_ids is None:
        return contact_registry.all_adapters()
    return contact_registry.adapters_for(request.source_ids)


def run_analysis(
    request: AnalysisRequest,
    registry: SourceRegistry,
    config: AnalysisConfig = DEFAULT_CONFIG,
    contact_registry: ContactSourceRegistry | None = None,
) -> AnalysisResult:
    contact_registry = contact_registry if contact_registry is not None else ContactSourceRegistry()
    _validate_source_ids(request, registry, contact_registry)

    window = request.window

    all_observations: list[LocationObservation] = []
    source_statuses: list[SourceStatus] = []

    for adapter in _select_adapters(request, registry):
        observations, status = _query_source(adapter, request.scooter_id, window)
        all_observations.extend(observations)
        source_statuses.append(status)

    customer_contacts: list[CustomerContactEvent] = []
    for adapter in _select_contact_adapters(request, contact_registry):
        events, status = _query_contact_source(adapter, request.scooter_id, window)
        customer_contacts.extend(events)
        source_statuses.append(status)
    customer_contacts.sort(key=lambda e: e.time)

    conflict_result = analyze_conflicts(all_observations, config)
    segments, anomalies = segment_timeline(conflict_result.segmentation_input, config)
    gaps = find_gaps(window, conflict_result.segmentation_input, config)

    logger.info(
        "analysis complete: %d observations, %d segments, %d gaps, %d conflicts, "
        "%d anomalies, %d duplicate groups, %d customer contacts",
        len(conflict_result.deduped_observations),
        len(segments),
        len(gaps),
        len(conflict_result.conflicts),
        len(anomalies),
        len(conflict_result.duplicates),
        len(customer_contacts),
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
        customer_contacts=customer_contacts,
        source_statuses=source_statuses,
    )
