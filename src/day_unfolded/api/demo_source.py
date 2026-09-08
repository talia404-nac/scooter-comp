"""DEMO ONLY — not a real source integration.

Generates fixed, obviously-synthetic location observations (Tel Aviv ->
Netanya) so the API/UI have something to render before any real source is
documented and wired in. Per the project's own rules (see
sources/registry.py and sources/base.py), this must never be mistaken for
"real source integration ready" — it exists purely so the framework is
demoable end-to-end. Delete this module once real sources are connected.
"""

from __future__ import annotations

from day_unfolded.domain.common import TimeWindow
from day_unfolded.domain.observation import LocationObservation, OriginType
from day_unfolded.sources.registry import SourceConfig, SourceRegistry

TEL_AVIV = (32.0853, 34.7818)
NETANYA = (32.3215, 34.8532)


class DemoAdapter:
    source_id = "DEMO_SOURCE"

    def __init__(self) -> None:
        self._scooter_id: str | None = None

    def fetch(self, scooter_id: str, window: TimeWindow) -> list[dict]:
        self._scooter_id = scooter_id
        total = window.end - window.start
        t_leave = window.start + total * 0.3
        t_arrive = window.start + total * 0.4
        return [
            {"t": window.start, "lat": TEL_AVIV[0], "lon": TEL_AVIV[1], "ref": "demo-1"},
            {"t": t_leave, "lat": TEL_AVIV[0], "lon": TEL_AVIV[1], "ref": "demo-2"},
            {"t": t_arrive, "lat": NETANYA[0], "lon": NETANYA[1], "ref": "demo-3"},
            {"t": window.end, "lat": NETANYA[0], "lon": NETANYA[1], "ref": "demo-4"},
        ]

    def to_observations(self, records: list[dict]) -> list[LocationObservation]:
        return [
            LocationObservation(
                scooter_id=self._scooter_id,
                start_time=r["t"],
                end_time=r["t"],
                latitude=r["lat"],
                longitude=r["lon"],
                origin_type=OriginType.DIRECT,
                source_id=self.source_id,
                source_record_ref=r["ref"],
            )
            for r in records
        ]


def build_demo_registry() -> SourceRegistry:
    registry = SourceRegistry()
    registry.register(
        SourceConfig(
            id="DEMO_SOURCE",
            name="Demo Source (synthetic — not a real source)",
            description="Fabricated demo data for local UI/API testing only.",
            interpretation_rules="N/A — synthetic demo data, not a real interpretation.",
            scooter_id_rules="Whatever scooter_id is requested is echoed back verbatim.",
            timestamp_rules="Fixed points spread proportionally across the requested window.",
            location_rules="Fixed demo coordinates (Tel Aviv, then Netanya).",
            limitations="Fabricated. Must never be treated as real location evidence.",
        ),
        DemoAdapter(),
    )
    return registry
