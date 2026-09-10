from datetime import date, time

import pytest
from pydantic import ValidationError

from day_unfolded.domain.request import AnalysisRequest


def test_valid_same_day_request():
    req = AnalysisRequest(
        scooter_id="p1",
        date=date(2026, 9, 8),
        start_time=time(9, 0),
        end_time=time(18, 0),
        timezone="Asia/Jerusalem",
    )
    assert req.window.duration_seconds == 9 * 3600


def test_valid_overnight_request_with_explicit_end_date():
    req = AnalysisRequest(
        scooter_id="p1",
        date=date(2026, 9, 8),
        start_time=time(22, 0),
        end_date=date(2026, 9, 9),
        end_time=time(2, 0),
        timezone="UTC",
    )
    assert req.window.duration_seconds == 4 * 3600


def test_exactly_24_hours_is_allowed():
    req = AnalysisRequest(
        scooter_id="p1",
        date=date(2026, 9, 8),
        start_time=time(0, 0),
        end_date=date(2026, 9, 9),
        end_time=time(0, 0),
        timezone="UTC",
    )
    assert req.window.duration_seconds == 24 * 3600


def test_over_24_hours_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            scooter_id="p1",
            date=date(2026, 9, 8),
            start_time=time(0, 0),
            end_date=date(2026, 9, 10),
            end_time=time(0, 1),
            timezone="UTC",
        )


def test_end_before_start_same_day_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            scooter_id="p1",
            date=date(2026, 9, 8),
            start_time=time(18, 0),
            end_time=time(9, 0),
            timezone="UTC",
        )


def test_zero_duration_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            scooter_id="p1",
            date=date(2026, 9, 8),
            start_time=time(9, 0),
            end_time=time(9, 0),
            timezone="UTC",
        )


def test_invalid_timezone_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            scooter_id="p1",
            date=date(2026, 9, 8),
            start_time=time(9, 0),
            end_time=time(18, 0),
            timezone="Not/AZone",
        )


def test_blank_scooter_id_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            scooter_id="   ",
            date=date(2026, 9, 8),
            start_time=time(9, 0),
            end_time=time(18, 0),
            timezone="UTC",
        )


def test_source_ids_defaults_to_none():
    req = AnalysisRequest(
        scooter_id="p1", date=date(2026, 9, 8), start_time=time(9, 0), end_time=time(18, 0), timezone="UTC"
    )
    assert req.source_ids is None


def test_source_ids_explicit_subset_is_kept():
    req = AnalysisRequest(
        scooter_id="p1",
        date=date(2026, 9, 8),
        start_time=time(9, 0),
        end_time=time(18, 0),
        timezone="UTC",
        source_ids=["DB_A", "DB_B"],
    )
    assert req.source_ids == ["DB_A", "DB_B"]


def test_empty_source_ids_list_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            scooter_id="p1",
            date=date(2026, 9, 8),
            start_time=time(9, 0),
            end_time=time(18, 0),
            timezone="UTC",
            source_ids=[],
        )


def test_duplicate_source_ids_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            scooter_id="p1",
            date=date(2026, 9, 8),
            start_time=time(9, 0),
            end_time=time(18, 0),
            timezone="UTC",
            source_ids=["DB_A", "DB_A"],
        )


def test_blank_source_id_entry_rejected():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            scooter_id="p1",
            date=date(2026, 9, 8),
            start_time=time(9, 0),
            end_time=time(18, 0),
            timezone="UTC",
            source_ids=["DB_A", "   "],
        )
