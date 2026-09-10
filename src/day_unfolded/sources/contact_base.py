"""The contact-source adapter contract.

Mirrors `sources.base.SourceAdapter` but produces `CustomerContactEvent`s
(calls/messages) instead of `LocationObservation`s. Kept as a distinct
protocol — not a variant of SourceAdapter — so a contact source can never be
registered where the location pipeline expects one, and vice versa.

No concrete adapter ships in this framework — real source formats are
provided later and adapters are implemented against the actual data, not a
guessed shape.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from day_unfolded.domain.common import TimeWindow
from day_unfolded.domain.contact import CustomerContactEvent

RawRecord = Any


@runtime_checkable
class ContactSourceAdapter(Protocol):
    source_id: str

    def fetch(self, scooter_id: str, window: TimeWindow) -> list[RawRecord]:
        """Retrieve only records relevant to this scooter and window.

        Raise SourceUnavailableError / SourceTimeoutError (from
        sources.base) on failure — do not return an empty list to mean "the
        source failed"; an empty list means "queried successfully, no
        contacts for this scooter and window".
        """
        ...

    def to_events(self, records: list[RawRecord]) -> list[CustomerContactEvent]:
        """Convert this source's raw records into canonical contact events,
        per this source's documented interpretation rules.

        Raise SourceMalformedDataError (from sources.base) for records that
        cannot be interpreted — do not silently drop them.
        """
        ...
