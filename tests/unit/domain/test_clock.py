import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain import Catchup, Clock, Timer


def test_clock_minimal() -> None:
    assert Clock.from_xml("<clock offset='utc'/>") == Clock(offset="utc")


def test_clock_adjustment_is_kept_as_text() -> None:
    clock = Clock.from_xml("<clock offset='variable' adjustment='+0'/>")

    assert clock.adjustment == "+0"
    assert clock.to_xml() == b'<clock offset="variable" adjustment="+0"/>'


def test_clock_rejects_unknown_offset() -> None:
    with pytest.raises(ValidationError):
        Clock.from_xml("<clock offset='moon'/>")


def test_timers_keep_order_and_attributes() -> None:
    clock = Clock.from_xml(
        "<clock offset='utc'><timer name='rtc' tickpolicy='catchup'>"
        "<catchup slew='120'/></timer><timer name='hpet' present='no'/></clock>"
    )

    assert clock.timers == [
        Timer(name="rtc", tickpolicy="catchup", catchup=Catchup(slew=120)),
        Timer(name="hpet", present=False),
    ]
