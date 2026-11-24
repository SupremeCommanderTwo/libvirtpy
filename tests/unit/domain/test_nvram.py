from libvirtpy.xml.domain import Os
from libvirtpy.xml.domain.os import BlockNvram, FileNvram, NetworkNvram
from libvirtpy.xml.domain.storage_source import FileSource


def test_nvram_text_path_is_a_file_nvram() -> None:
    nvram = _os("<nvram template='/t'>/var/guest_VARS.fd</nvram>").nvram

    assert nvram == FileNvram(value="/var/guest_VARS.fd", template="/t")


def test_nvram_with_file_source() -> None:
    nvram = _os("<nvram type='file'><source file='/v.fd'/></nvram>").nvram

    assert nvram == FileNvram(type="file", source=FileSource(file="/v.fd"))


def test_nvram_type_selects_block_and_network_variants() -> None:
    assert isinstance(
        _os("<nvram type='block'><source dev='/d'/></nvram>").nvram, BlockNvram
    )
    assert isinstance(
        _os(
            "<nvram type='network' format='raw'><source protocol='nbd'/></nvram>"
        ).nvram,
        NetworkNvram,
    )


def _os(nvram: str) -> Os:
    return Os.from_xml(f"<os><type>hvm</type>{nvram}</os>")
