"""A deterministic, non-LLM implementation of LLMProvider.

This exists so the pipeline is demoable and testable end-to-end without any
API credentials. It mechanically renders the same structured facts a real
LLM would receive into Hebrew lines — no natural-language generation, no
model call. Swap in a real provider (e.g. backed by the Claude API) by
implementing `LLMProvider.complete` and passing that instead; nothing else
in the presentation layer needs to change.
"""

from __future__ import annotations

import json

from day_unfolded.presentation.llm_provider import LLMProvider

_DIRECTION_HE = {
    "N": "צפון",
    "NE": "צפון מזרח",
    "E": "מזרח",
    "SE": "דרום מזרח",
    "S": "דרום",
    "SW": "דרום מערב",
    "W": "מערב",
    "NW": "צפון מערב",
}


def _sources_tag(sources: list[str]) -> str:
    return "(" + ", ".join(sources) + ")"


def _render_event(event: dict) -> str:
    start, end = event["start"], event["end"]

    if event["type"] == "gap":
        return f"{start}–{end} — אין מידע מספיק לקבוע את מיקומו."

    if event["type"] == "conflict":
        parts = [
            f'({o["latitude"]:.4f}, {o["longitude"]:.4f}) ({o["source"]})' for o in event["observations"]
        ]
        return f"{start} — נמצאו מיקומים סותרים: " + " / ".join(parts)

    # segment
    tag = _sources_tag(event["sources"])
    if event["state"] == "moving":
        direction = _DIRECTION_HE.get(event["direction"], event["direction"] or "")
        return f"{start}–{end} — היה בתנועה לכיוון {direction} {tag}"
    if event["latitude"] is not None and event["longitude"] is not None:
        loc = f'({event["latitude"]:.4f}, {event["longitude"]:.4f})'
    else:
        loc = "מיקום לא ידוע"
    return f"{start}–{end} — נמצא באזור {loc} {tag}"


class TemplateHebrewProvider(LLMProvider):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.loads(user_prompt)
        lines = [_render_event(e) for e in payload["events"]]
        return "\n".join(lines) if lines else "לא נמצא מידע עבור טווח הזמן המבוקש."
