"""Minimal demo API.

Wraps the deterministic pipeline + Hebrew presenter behind one endpoint so
the framework can be exercised from a browser. Uses the DEMO_SOURCE registry
(fabricated data, see demo_source.py) and the deterministic
TemplateHebrewProvider (no real LLM call) — both are placeholders to be
swapped out once real sources and a real LLM provider are configured.

No authentication, no persistence, no rate limiting — this is a local
development aid, not a production surface.
"""

from __future__ import annotations

from datetime import date as date_, time as time_
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from day_unfolded.analysis.pipeline import run_analysis
from day_unfolded.api.demo_source import build_demo_registry
from day_unfolded.domain.request import AnalysisRequest
from day_unfolded.presentation.hebrew_presenter import present_in_hebrew
from day_unfolded.presentation.template_provider import TemplateHebrewProvider

app = FastAPI(title="Day Unfolded — demo API")

_registry = build_demo_registry()
_provider = TemplateHebrewProvider()


class AnalyzeRequestBody(BaseModel):
    scooter_id: str
    date: str
    start_time: str
    end_date: str | None = None
    end_time: str
    timezone: str = "Asia/Jerusalem"


@app.post("/api/analyze")
def analyze(body: AnalyzeRequestBody) -> dict:
    try:
        request = AnalysisRequest(
            scooter_id=body.scooter_id,
            date=date_.fromisoformat(body.date),
            start_time=time_.fromisoformat(body.start_time),
            end_date=date_.fromisoformat(body.end_date) if body.end_date else None,
            end_time=time_.fromisoformat(body.end_time),
            timezone=body.timezone,
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = run_analysis(request, _registry)
    hebrew = present_in_hebrew(result, _provider)

    return {"structured": result.model_dump(mode="json"), "hebrew": hebrew}


app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
