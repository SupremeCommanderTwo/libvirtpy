import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain.devices import Memballoon, MemballoonStats


def test_memballoon_with_stats() -> None:
    memballoon = Memballoon.from_xml(
        "<memballoon model='virtio' autodeflate='on'><stats period='10'/></memballoon>"
    )

    assert memballoon == Memballoon(
        model="virtio", autodeflate=True, stats=MemballoonStats(period=10)
    )


def test_memballoon_requires_model() -> None:
    with pytest.raises(ValidationError):
        Memballoon.from_xml("<memballoon/>")
