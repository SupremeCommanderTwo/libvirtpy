import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain import CurrentMemory, MaxMemory, Memory


def test_memory_without_unit_keeps_unit_none() -> None:
    memory = Memory.from_xml("<memory>524288</memory>")

    assert memory.value == 524288
    assert memory.unit is None


def test_memory_without_unit_is_kib_in_bytes() -> None:
    assert Memory(value=2).to_bytes() == 2048


def test_memory_keeps_unit_as_written() -> None:
    memory = Memory.from_xml("<memory unit='GiB'>4</memory>")

    assert memory.to_xml() == b'<memory unit="GiB">4</memory>'
    assert memory.to_bytes() == 4 * 1024**3


def test_memory_dump_core_is_on_off() -> None:
    memory = Memory.from_xml("<memory dumpCore='off'>1</memory>")

    assert memory.dump_core is False


def test_memory_rejects_unknown_unit() -> None:
    with pytest.raises(ValidationError):
        Memory(value=1, unit="parsecs")


def test_memory_rejects_negative_value() -> None:
    with pytest.raises(ValidationError):
        Memory(value=-1)


def test_current_memory_uses_camel_case_tag() -> None:
    current = CurrentMemory(value=1024, unit="MiB")

    assert current.to_xml() == b'<currentMemory unit="MiB">1024</currentMemory>'


def test_max_memory_reads_slots() -> None:
    max_memory = MaxMemory.from_xml("<maxMemory slots='16' unit='KiB'>8</maxMemory>")

    assert max_memory.slots == 16
    assert max_memory.to_bytes() == 8 * 1024
