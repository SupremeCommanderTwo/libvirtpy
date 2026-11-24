import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain import Boot, Loader, Os, OsType


def test_os_type_reads_arch_machine_and_text() -> None:
    os = Os.from_xml("<os><type arch='x86_64' machine='q35'>hvm</type></os>")

    assert os.type == OsType(value="hvm", arch="x86_64", machine="q35")


def test_os_without_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Os.from_xml("<os><boot dev='hd'/></os>")


def test_os_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        Os.from_xml("<os><type>dos</type></os>")


def test_boot_order_is_kept() -> None:
    os = Os.from_xml("<os><type>hvm</type><boot dev='network'/><boot dev='hd'/></os>")

    assert os.boots == [Boot(dev="network"), Boot(dev="hd")]


def test_loader_without_path_keeps_value_none() -> None:
    os = Os.from_xml("<os><type>hvm</type><loader readonly='yes'/></os>")

    assert os.loader == Loader(value=None, readonly=True)


def test_loader_without_path_serializes_without_text() -> None:
    loader = Loader(readonly=True, type="pflash")

    assert loader.to_xml() == b'<loader readonly="yes" type="pflash"/>'


def test_empty_cmdline_is_kept_as_empty_string() -> None:
    os = Os.from_xml("<os><type>hvm</type><cmdline/></os>")

    assert os.cmdline == ""


def test_missing_cmdline_is_none() -> None:
    assert Os.from_xml("<os><type>hvm</type></os>").cmdline is None


def test_container_init_args_keep_order() -> None:
    os = Os.from_xml(
        "<os><type>exe</type><init>/sbin/init</init>"
        "<initarg>a</initarg><initarg>b</initarg></os>"
    )

    assert os.init_args == ["a", "b"]


def test_bios_reboot_timeout_accepts_minus_one() -> None:
    os = Os.from_xml("<os><type>hvm</type><bios rebootTimeout='-1'/></os>")

    assert os.bios is not None
    assert os.bios.reboot_timeout == -1
