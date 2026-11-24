"""``<clock>``: guest time keeping.

``Clock`` and ``Timer`` are single models: their variants (by ``offset`` and by
timer ``name``) differ by one or two optional attributes only.

See https://libvirt.org/formatdomain.html#time-keeping
"""

from typing import Literal

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from libvirtpy.xml._types import YesNo

__all__ = ["Catchup", "Clock", "Timer"]


class Catchup(LibvirtXmlModel, tag="catchup"):
    """``<catchup>``: how a ``tickpolicy='catchup'`` timer catches up."""

    threshold: int | None = attr(name="threshold", default=None, ge=0)
    slew: int | None = attr(name="slew", default=None, ge=0)
    limit: int | None = attr(name="limit", default=None, ge=0)


class Timer(LibvirtXmlModel, tag="timer"):
    """``<timer>``: one guest timer device."""

    name: Literal[
        "platform",
        "rtc",
        "tsc",
        "hpet",
        "pit",
        "armvtimer",
        "kvmclock",
        "hypervclock",
    ] = attr(name="name")
    track: Literal["boot", "guest", "wall", "realtime"] | None = attr(
        name="track", default=None, description="Only for ``platform`` and ``rtc``."
    )
    tickpolicy: Literal["delay", "catchup", "merge", "discard"] | None = attr(
        name="tickpolicy", default=None
    )
    frequency: int | None = attr(
        name="frequency", default=None, ge=0, description="Hz; only for ``tsc``."
    )
    mode: Literal["auto", "native", "emulate", "paravirt", "smpsafe"] | None = attr(
        name="mode", default=None, description="Only for ``tsc``."
    )
    present: YesNo | None = attr(name="present", default=None)
    catchup: Catchup | None = element(tag="catchup", default=None)


class Clock(LibvirtXmlModel, tag="clock"):
    """``<clock>``: how the guest clock is synchronized to the host."""

    offset: Literal["localtime", "utc", "timezone", "variable", "absolute"] = attr(
        name="offset"
    )
    adjustment: str | None = attr(
        name="adjustment",
        default=None,
        description="Seconds to add, e.g. ``-3600``, or ``reset``. Kept as text.",
    )
    timezone: str | None = attr(
        name="timezone", default=None, description="For ``offset='timezone'``."
    )
    basis: Literal["utc", "localtime"] | None = attr(
        name="basis", default=None, description="For ``offset='variable'``."
    )
    start: int | None = attr(
        name="start",
        default=None,
        ge=0,
        description="Epoch seconds, for ``offset='absolute'``.",
    )
    timers: list[Timer] = element(tag="timer", default_factory=list)
