import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain import Domain


def test_domain_minimal() -> None:
    domain = Domain.from_xml("<domain type='kvm'><name>vm</name></domain>")

    assert domain.type == "kvm"
    assert domain.name == "vm"
    assert domain.memory is None
    assert domain.features is None


def test_domain_without_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Domain.from_xml("<domain><name>vm</name></domain>")


def test_domain_without_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Domain.from_xml("<domain type='kvm'/>")


def test_domain_reads_runtime_id() -> None:
    domain = Domain.from_xml("<domain type='kvm' id='3'><name>vm</name></domain>")

    assert domain.id == 3


def test_domain_lifecycle_actions() -> None:
    domain = Domain.from_xml(
        "<domain type='kvm'><name>vm</name><on_poweroff>destroy</on_poweroff>"
        "<on_crash>coredump-restart</on_crash></domain>"
    )

    assert domain.on_poweroff == "destroy"
    assert domain.on_crash == "coredump-restart"
    assert domain.on_reboot is None


def test_domain_rejects_crash_action_for_poweroff() -> None:
    with pytest.raises(ValidationError):
        Domain.from_xml(
            "<domain type='kvm'><name>vm</name>"
            "<on_poweroff>coredump-restart</on_poweroff></domain>"
        )


def test_empty_bootloader_is_kept() -> None:
    domain = Domain.from_xml("<domain type='xen'><name>vm</name><bootloader/></domain>")

    assert domain.bootloader == ""
    assert b"<bootloader></bootloader>" in domain.to_xml()
