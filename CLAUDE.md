# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A framework for producing a chronological "day in the life" location timeline for a scooter (fleet asset tracking for a scooter company) by combining multiple authorized data sources. It is built for a real commercial deployment but currently ships with **zero real sources wired in** — see "Framework vs. source integration" below before assuming anything here is production-ready.

## Commands

Python package, `src/` layout, installed editable into `.venv`.

```powershell
# one-time setup
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,api]"

# run the full test suite
.\.venv\Scripts\python.exe -m pytest -q

# run a single test file / single test
.\.venv\Scripts\python.exe -m pytest tests/analysis/test_segmentation.py -q
.\.venv\Scripts\python.exe -m pytest tests/analysis/test_segmentation.py::test_impossible_jump_is_anomaly_not_a_moving_segment -q

# run the demo API + UI (http://127.0.0.1:8000/)
.\.venv\Scripts\python.exe -m uvicorn day_unfolded.api.app:app --reload
```

There is no lint/format/type-check tooling configured yet (no ruff/black/mypy in `pyproject.toml`) — don't assume one exists.

`tzdata` is a hard runtime dependency (not just dev): Windows has no bundled IANA timezone database, so `zoneinfo.ZoneInfo("Asia/Jerusalem")` etc. fail without it.

## Architecture

Data flows one direction through five layers, each only aware of the layer directly below it:

```
sources (raw, source-specific)
    -> canonical LocationObservation  (domain/observation.py)
    -> deterministic analysis          (analysis/*.py, orchestrated by analysis/pipeline.py)
    -> structured AnalysisResult       (domain/result.py)
    -> Hebrew presentation              (presentation/hebrew_presenter.py, via an LLMProvider)
```

The analysis engine (`analysis/`) never sees a raw source record and never branches on `source_id`. It only operates on `LocationObservation`. Adding a new source means writing one adapter class in `sources/` — nothing in `analysis/`, `domain/`, or `presentation/` should need to change.

### Framework vs. source integration

`sources/registry.py`'s `SourceRegistry` ships **empty** by design. Real adapters are only added once a source's documentation is provided (identity, meaning, scooter-matching rule, timestamp rule, location-derivation rule, limitations, sample data) — nothing is guessed. `src/day_unfolded/api/demo_source.py` (`DemoAdapter`, `DEMO_SOURCE`) is explicitly fabricated data for exercising the UI/API locally; it must never be mistaken for a real source and should be deleted once real sources exist.

### Provenance and derived vs. direct locations

`LocationObservation.origin_type` is `direct` or `derived`. A `derived` observation *must* carry a `derivation` string explaining the rule used (e.g. `"cell_tower_lookup"`); a `direct` one *must not*. This is enforced by a pydantic validator on the model itself (`domain/observation.py`), not by convention — don't work around it.

### Conflicts are never resolved

`analysis/conflicts.py` classifies overlapping-time, cross-source observations as duplicate (same source + same record — collapsed, provenance kept), corroboration (different sources agree — kept, unmerged), or conflict (different sources disagree). Conflicting observations are excluded from the normal segmentation stream and surfaced as an explicit `Conflict` instead. No confidence/reliability scoring exists yet — do not add a "pick a winner" step without an explicit product decision to do so.

### Gaps and movement segments share one threshold — do not decouple them

`analysis/gaps.py` and `analysis/segmentation.py` both use `AnalysisConfig.gap_threshold_seconds` to decide whether the interval between two observations is "close enough in time" to reason about at all. If the elapsed time between two consecutive observations exceeds this threshold, `segmentation.py` refuses to assert a `moving` (or even `stationary`) segment across it, and `gaps.py` reports that same span as a `Gap`. This is deliberate: two same-location points hours apart do **not** get merged into "stayed there the whole time" (see spec-level rule: never fill a gap). If you change one module's use of this threshold without the other, you will get the same interval reported as both "moving" and "a gap" simultaneously — this exact bug was caught and fixed once already during a smoke test.

### Anomalies vs. movement

`analysis/anomalies.py` flags physically implausible speed between two observations. When flagged, `segmentation.py` does **not** emit a `moving` segment bridging them (that would assert a route that was never observed) — it closes the prior segment and starts a fresh one, and the anomaly is only recorded in `AnalysisResult.anomalies`.

### LLM boundary

`presentation/llm_provider.py` defines a minimal `LLMProvider` protocol (`complete(system_prompt, user_prompt) -> str`); no concrete LLM-backed provider is wired in (an intentional choice, not an oversight — swap one in by implementing that one method). `presentation/hebrew_presenter.py` builds the *only* input the model ever sees — the already-computed structured facts (segment times/states/directions, gaps, conflicts) as JSON — with a system prompt instructing it never to invent, resolve conflicts, fill gaps, or assume a transport mode. `presentation/template_provider.py` (`TemplateHebrewProvider`) is a deterministic, non-LLM implementation of the same protocol used for local dev/testing so nothing requires API credentials.

### Config

Every threshold used by the deterministic analysis (`stationary_radius_meters`, `min_movement_distance_meters`, `max_reasonable_speed_mps`, `gap_threshold_seconds`, `direction_granularity`, `conflict_distance_threshold_meters`, `corroboration_time_window_seconds`) lives in `config/settings.py` as `AnalysisConfig`. The shipped defaults are explicitly labeled placeholders, not calibrated against real source precision — don't treat them as correct without recalibration once real sources exist.

### API/UI

`src/day_unfolded/api/app.py` is a minimal FastAPI wrapper (`POST /api/analyze`) with no auth, no persistence — a local dev aid, not a production surface. It serves `src/day_unfolded/api/static/index.html`, a single self-contained page (no external requests/CDN — everything inline) styled around a "day-arc" motif: a 24-hour gradient (night -> dawn -> midday -> dusk) that colors timeline markers/spine by the actual time of day each event occurred, not decoratively.
