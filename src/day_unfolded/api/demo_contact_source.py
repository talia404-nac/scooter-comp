"""DEMO ONLY — not a real source integration.

Generates fixed, obviously-synthetic customer call/message records so the
API/UI have something to render before any real call-center or messaging
source is documented and wired in. Per the project's own rules (see
sources/contact_registry.py and sources/contact_base.py), this must never be
mistaken for "real source integration ready" — it exists purely so the
framework is demoable end-to-end. Delete this module once real contact
sources are connected.
"""

from __future__ import annotations

from day_unfolded.domain.common import TimeWindow
from day_unfolded.domain.contact import ContactChannel, CustomerContactEvent
from day_unfolded.sources.contact_registry import ContactSourceRegistry
from day_unfolded.sources.registry import SourceConfig


class DemoContactAdapter:
    source_id = "DEMO_CONTACT_SOURCE"

    def __init__(self) -> None:
        self._scooter_id: str | None = None

    def fetch(self, scooter_id: str, window: TimeWindow) -> list[dict]:
        self._scooter_id = scooter_id
        total = window.end - window.start
        t_call = window.start + total * 0.35
        t_message = window.start + total * 0.65
        return [
            {
                "t": t_call,
                "channel": "call",
                "summary": "לקוח התקשר לדווח שהקורקינט תקוע ולא ניתן לנעילה.",
                "ref": "demo-call-1",
            },
            {
                "t": t_message,
                "channel": "message",
                "summary": "הודעת SMS מהלקוח: 'הבטריה נגמרה, איפה אפשר להחליף קורקינט?'",
                "ref": "demo-msg-1",
            },
        ]

    def to_events(self, records: list[dict]) -> list[CustomerContactEvent]:
        return [
            CustomerContactEvent(
                scooter_id=self._scooter_id,
                time=r["t"],
                channel=ContactChannel(r["channel"]),
                summary=r["summary"],
                source_id=self.source_id,
                source_record_ref=r["ref"],
            )
            for r in records
        ]


def build_demo_contact_registry() -> ContactSourceRegistry:
    registry = ContactSourceRegistry()
    registry.register(
        SourceConfig(
            id="DEMO_CONTACT_SOURCE",
            name="Demo Contact Source (synthetic — not a real source)",
            description="Fabricated demo call/message data for local UI/API testing only.",
            interpretation_rules="N/A — synthetic demo data, not a real interpretation.",
            scooter_id_rules="Whatever scooter_id is requested is echoed back verbatim.",
            timestamp_rules="Fixed points spread proportionally across the requested window.",
            location_rules="N/A — contact events never carry a location.",
            limitations="Fabricated. Must never be treated as a real customer interaction.",
        ),
        DemoContactAdapter(),
    )
    return registry
