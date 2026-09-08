"""Gap detection: intervals within the requested window with no covering
observation. Never filled, never assumed to be a continuation of the
previous or next known location."""

from __future__ import annotations

from day_unfolded.config.settings import AnalysisConfig
from day_unfolded.domain.common import TimeWindow
from day_unfolded.domain.observation import LocationObservation
from day_unfolded.domain.timeline import Gap


def find_gaps(
    window: TimeWindow,
    observations: list[LocationObservation],
    config: AnalysisConfig,
) -> list[Gap]:
    located = sorted((o for o in observations if o.has_location), key=lambda o: o.start_time)

    gaps: list[Gap] = []
    cursor = window.start
    for obs in located:
        if obs.start_time > cursor:
            uncovered_seconds = (obs.start_time - cursor).total_seconds()
            if uncovered_seconds > config.gap_threshold_seconds:
                gaps.append(Gap(start_time=cursor, end_time=obs.start_time))
        if obs.end_time > cursor:
            cursor = obs.end_time

    if window.end > cursor:
        uncovered_seconds = (window.end - cursor).total_seconds()
        if uncovered_seconds > config.gap_threshold_seconds:
            gaps.append(Gap(start_time=cursor, end_time=window.end))

    return gaps
