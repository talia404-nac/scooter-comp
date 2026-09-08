"""The source adapter contract.

A SourceAdapter is the ONLY place that is allowed to know a source's raw
field names, JSON shape, or database-specific semantics. It translates raw
records into canonical `LocationObservation`s according to that source's
documented interpretation rules (see `sources.registry.SourceConfig`).

No concrete adapter ships in this framework — real source formats are
provided later and adapters are implemented against the actual data, not a
guessed shape. `RawRecord` is intentionally untyped: each adapter defines
its own internal parsing of whatever its source actually returns.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from day_unfolded.domain.common import TimeWindow
from day_unfolded.domain.observation import LocationObservation

RawRecord = Any


class SourceError(Exception):
    """Base class for source-layer failures the pipeline knows how to handle
    without losing results from other, healthy sources."""


class SourceUnavailableError(SourceError):
    """The source could not be reached or refused the query."""


class SourceTimeoutError(SourceError):
    """The source did not respond within the allotted time."""


class SourceMalformedDataError(SourceError):
    """The source responded, but returned records the adapter could not
    parse according to its documented interpretation rules."""


@runtime_checkable
class SourceAdapter(Protocol):
    source_id: str

    def fetch(self, scooter_id: str, window: TimeWindow) -> list[RawRecord]:
        """Retrieve only records relevant to this scooter and window.

        Raise SourceUnavailableError / SourceTimeoutError on failure — do not
        return an empty list to mean "the source failed"; an empty list means
        "the source was queried successfully and has no data for this scooter
        and window".
        """
        ...

    def to_observations(self, records: list[RawRecord]) -> list[LocationObservation]:
        """Convert this source's raw records into canonical observations,
        per this source's documented interpretation rules.

        Raise SourceMalformedDataError for records that cannot be
        interpreted — do not silently drop them.
        """
        ...
