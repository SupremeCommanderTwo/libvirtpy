import tarfile

import pytest

from tools.fetch_samples import wanted_path


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("libvirt-1.0/src/conf/schemas/domain.rng", "src/conf/schemas/domain.rng"),
        ("libvirt-1.0/tests/qemuxmlconfdata/a.xml", "tests/qemuxmlconfdata/a.xml"),
        ("libvirt-1.0/examples/xml/test/testdom.xml", "examples/xml/test/testdom.xml"),
    ],
)
def test_wanted_files_keep_their_relative_path(name: str, expected: str) -> None:
    assert str(wanted_path(_file_member(name))) == expected


@pytest.mark.parametrize(
    "name",
    [
        "libvirt-1.0/src/conf/domain_conf.c",
        "libvirt-1.0/tests/qemuxmlconfdata/a.args",
        "libvirt-1.0/docs/index.xml",
        "libvirt-1.0/tests/../../evil.xml",
        "/libvirt-1.0/tests/a.xml",
        "tests.xml",
    ],
)
def test_other_files_and_unsafe_paths_are_skipped(name: str) -> None:
    assert wanted_path(_file_member(name)) is None


def test_links_are_skipped() -> None:
    member = tarfile.TarInfo("libvirt-1.0/tests/link.xml")
    member.type = tarfile.SYMTYPE

    assert wanted_path(member) is None


def _file_member(name: str) -> tarfile.TarInfo:
    member = tarfile.TarInfo(name)
    member.type = tarfile.REGTYPE
    return member
