import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain import Numa, NumaCell, NumaSibling


def test_numa_cell_minimal() -> None:
    numa = Numa.from_xml("<numa><cell cpus='0-1' memory='1048576'/></numa>")

    assert numa.cells == [NumaCell(cpus="0-1", memory=1048576)]


def test_numa_cell_without_memory_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Numa.from_xml("<numa><cell cpus='0'/></numa>")


def test_numa_distances_keep_order() -> None:
    numa = Numa.from_xml(
        "<numa><cell id='0' memory='1'><distances>"
        "<sibling id='0' value='10'/><sibling id='1' value='20'/>"
        "</distances></cell></numa>"
    )

    distances = numa.cells[0].distances
    assert distances is not None
    assert distances.siblings == [
        NumaSibling(id=0, value=10),
        NumaSibling(id=1, value=20),
    ]


@pytest.mark.parametrize("value", ["9", "256"])
def test_numa_distance_outside_schema_range_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError):
        NumaSibling.from_xml(f"<sibling id='0' value='{value}'/>")
