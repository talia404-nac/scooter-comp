from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from day_unfolded.domain.contact import ContactChannel, CustomerContactEvent

T0 = datetime(2026, 9, 8, 10, 0, tzinfo=timezone.utc)


def test_valid_call_event():
    event = CustomerContactEvent(
        scooter_id="p1",
        time=T0,
        channel=ContactChannel.CALL,
        summary="customer reported a flat tire",
        source_id="DB_CALLS",
        source_record_ref="call-1",
    )
    assert event.channel == ContactChannel.CALL


def test_valid_message_event():
    event = CustomerContactEvent(
        scooter_id="p1",
        time=T0,
        channel=ContactChannel.MESSAGE,
        summary="battery is dead",
        source_id="DB_SMS",
        source_record_ref="msg-1",
    )
    assert event.channel == ContactChannel.MESSAGE


def test_blank_summary_rejected():
    with pytest.raises(ValidationError):
        CustomerContactEvent(
            scooter_id="p1",
            time=T0,
            channel=ContactChannel.CALL,
            summary="   ",
            source_id="DB_CALLS",
            source_record_ref="call-1",
        )


def test_naive_time_rejected():
    with pytest.raises(ValidationError):
        CustomerContactEvent(
            scooter_id="p1",
            time=datetime(2026, 9, 8, 10, 0),
            channel=ContactChannel.CALL,
            summary="no tz",
            source_id="DB_CALLS",
            source_record_ref="call-1",
        )
