import json
from datetime import datetime, timedelta, timezone

from day_unfolded.domain.common import TimeWindow
from day_unfolded.domain.result import AnalysisResult
from day_unfolded.domain.timeline import (
    Conflict,
    ConflictObservationRef,
    Gap,
    MovementState,
    TimelineSegment,
)
from day_unfolded.presentation.hebrew_presenter import present_in_hebrew

T0 = datetime(2026, 9, 8, 9, 0, tzinfo=timezone.utc)


class FakeLLMProvider:
    def __init__(self, response: str = "ok"):
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.response


def _sample_result() -> AnalysisResult:
    window = TimeWindow(start=T0, end=T0 + timedelta(hours=3))
    segment = TimelineSegment(
        start_time=T0,
        end_time=T0 + timedelta(hours=1),
        state=MovementState.STATIONARY,
        representative_latitude=32.08,
        representative_longitude=34.78,
        supporting_observation_ids=["o1"],
        source_ids=["DB_X"],
    )
    gap = Gap(start_time=T0 + timedelta(hours=1), end_time=T0 + timedelta(hours=2))
    conflict = Conflict(
        start_time=T0 + timedelta(hours=2),
        end_time=T0 + timedelta(hours=2, minutes=5),
        observations=[
            ConflictObservationRef(
                observation_id="o2", source_id="DB_X", latitude=32.08, longitude=34.78, time=T0 + timedelta(hours=2)
            ),
            ConflictObservationRef(
                observation_id="o3", source_id="DB_Y", latitude=32.30, longitude=34.90, time=T0 + timedelta(hours=2)
            ),
        ],
    )
    return AnalysisResult(scooter_id="p1", window=window, segments=[segment], gaps=[gap], conflicts=[conflict])


def test_exactly_one_llm_call_is_made():
    provider = FakeLLMProvider()
    present_in_hebrew(_sample_result(), provider)
    assert len(provider.calls) == 1


def test_system_prompt_carries_the_required_guardrails():
    provider = FakeLLMProvider()
    present_in_hebrew(_sample_result(), provider)
    system_prompt, _ = provider.calls[0]
    lowered = system_prompt.lower()
    assert "conflict" in lowered
    assert "gap" in lowered
    assert "driving" in lowered or "transportation" in lowered
    assert "hebrew" in lowered


def test_user_prompt_contains_only_structured_facts():
    provider = FakeLLMProvider()
    present_in_hebrew(_sample_result(), provider)
    _, user_prompt = provider.calls[0]

    payload = json.loads(user_prompt)
    assert set(payload.keys()) == {"scooter_id", "events"}
    assert {e["type"] for e in payload["events"]} == {"segment", "gap", "conflict"}

    # raw-observation-only fields must never leak into the LLM-facing prompt
    assert "source_record_ref" not in user_prompt
    assert "uncertainty_meters" not in user_prompt
    assert "metadata" not in user_prompt


def test_events_are_chronologically_ordered():
    provider = FakeLLMProvider()
    present_in_hebrew(_sample_result(), provider)
    _, user_prompt = provider.calls[0]
    starts = [e["start"] for e in json.loads(user_prompt)["events"]]
    assert starts == sorted(starts)


def test_conflict_event_presents_all_competing_observations():
    provider = FakeLLMProvider()
    present_in_hebrew(_sample_result(), provider)
    _, user_prompt = provider.calls[0]

    conflict_events = [e for e in json.loads(user_prompt)["events"] if e["type"] == "conflict"]
    assert len(conflict_events) == 1
    assert {o["source"] for o in conflict_events[0]["observations"]} == {"DB_X", "DB_Y"}


def test_provider_response_is_returned_verbatim():
    provider = FakeLLMProvider(response="09:00–10:00 — שהה באזור תל אביב (DB_X)")
    result = present_in_hebrew(_sample_result(), provider)
    assert result == provider.response
