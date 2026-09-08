"""Turns an already-computed AnalysisResult into Hebrew prose.

Single bounded LLM call. The model receives ONLY the structured facts
already computed by the deterministic pipeline (segment times/states/
directions, gaps, conflicts) — never raw observations, never raw source
records, never source documentation. It is instructed to add nothing.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from day_unfolded.domain.result import AnalysisResult
from day_unfolded.presentation.llm_provider import LLMProvider

SYSTEM_PROMPT = """\
You turn an already-computed structured location timeline into natural Hebrew \
prose for a customer. The structured data you receive is the complete and \
final set of facts — treat it as exhaustive.

Rules you must never break:
1. Use only the facts present in the structured data. Never add, guess, or \
infer a location, time, direction, or event that is not present.
2. Never resolve a conflict. A "conflict" event lists two or more competing \
observations — present all of them as competing, pick no winner.
3. Never fill a "gap" event. State plainly that there is not enough \
information for that interval; do not guess what happened during it.
4. Never assume a mode of transportation. A "segment" with state "moving" \
must be described only as movement (e.g. "בתנועה" / "היה בתנועה"), with \
direction if given — never as driving, walking, or any other mode unless \
that fact is explicitly present in the input.
5. Do not state or imply more certainty than the data supports.
6. After every timeline line, append the source tag exactly as given, \
formatted as (SOURCE_ID) — do not explain what the source is.
7. Output must be Hebrew, chronologically ordered, one line per event.
"""


def _fmt(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def build_structured_facts(result: AnalysisResult) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for seg in result.segments:
        events.append(
            {
                "type": "segment",
                "start": _fmt(seg.start_time),
                "end": _fmt(seg.end_time),
                "state": seg.state.value,
                "latitude": seg.representative_latitude,
                "longitude": seg.representative_longitude,
                "direction": seg.direction.value if seg.direction else None,
                "sources": seg.source_ids,
            }
        )

    for gap in result.gaps:
        events.append({"type": "gap", "start": _fmt(gap.start_time), "end": _fmt(gap.end_time)})

    for conflict in result.conflicts:
        events.append(
            {
                "type": "conflict",
                "start": _fmt(conflict.start_time),
                "end": _fmt(conflict.end_time),
                "observations": [
                    {
                        "source": o.source_id,
                        "latitude": o.latitude,
                        "longitude": o.longitude,
                    }
                    for o in conflict.observations
                ],
            }
        )

    events.sort(key=lambda e: e["start"])
    return events


def present_in_hebrew(result: AnalysisResult, provider: LLMProvider) -> str:
    facts = build_structured_facts(result)
    user_prompt = json.dumps({"scooter_id": result.scooter_id, "events": facts}, ensure_ascii=False, indent=2)
    return provider.complete(SYSTEM_PROMPT, user_prompt)
