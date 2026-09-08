import itertools
from datetime import datetime

import pytest

from day_unfolded.config.settings import AnalysisConfig
from day_unfolded.domain.observation import LocationObservation, OriginType

_ref_counter = itertools.count()


@pytest.fixture
def config() -> AnalysisConfig:
    return AnalysisConfig()


@pytest.fixture
def make_observation():
    def _make(
        *,
        time: datetime,
        scooter_id: str = "scooter-1",
        lat: float | None = None,
        lon: float | None = None,
        source_id: str = "DB_TEST",
        source_record_ref: str | None = None,
        origin_type: OriginType = OriginType.DIRECT,
        derivation: str | None = None,
        end_time: datetime | None = None,
    ) -> LocationObservation:
        return LocationObservation(
            scooter_id=scooter_id,
            start_time=time,
            end_time=end_time or time,
            latitude=lat,
            longitude=lon,
            origin_type=origin_type,
            derivation=derivation,
            source_id=source_id,
            source_record_ref=source_record_ref or f"rec-{next(_ref_counter)}",
        )

    return _make
