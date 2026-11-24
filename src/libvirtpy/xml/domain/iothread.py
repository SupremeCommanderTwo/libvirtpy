"""``<iothreads>``, ``<iothreadids>`` and ``<defaultiothread>``.

See https://libvirt.org/formatdomain.html#iothreads-allocation
"""

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel

__all__ = ["DefaultIothread", "IothreadId", "IothreadIds", "IothreadPoll"]


class IothreadPoll(LibvirtXmlModel, tag="poll"):
    """``<poll>``: adaptive polling of an I/O thread."""

    max: int | None = attr(name="max", default=None, ge=0)
    grow: int | None = attr(name="grow", default=None, ge=0)
    shrink: int | None = attr(name="shrink", default=None, ge=0)
    weight: int | None = attr(name="weight", default=None, ge=0)


class IothreadId(LibvirtXmlModel, tag="iothread"):
    """``<iothread>``: one I/O thread with its settings."""

    id: int = attr(name="id", ge=0)
    thread_pool_min: int | None = attr(name="thread_pool_min", default=None, ge=0)
    thread_pool_max: int | None = attr(name="thread_pool_max", default=None, ge=0)
    poll: IothreadPoll | None = element(tag="poll", default=None)


class IothreadIds(LibvirtXmlModel, tag="iothreadids"):
    """``<iothreadids>``: the I/O threads, by ID."""

    iothreads: list[IothreadId] = element(tag="iothread", default_factory=list)


class DefaultIothread(LibvirtXmlModel, tag="defaultiothread"):
    """``<defaultiothread>``: thread pool limits of the default I/O thread."""

    thread_pool_min: int | None = attr(name="thread_pool_min", default=None, ge=0)
    thread_pool_max: int | None = attr(name="thread_pool_max", default=None, ge=0)
