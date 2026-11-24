from pathlib import Path

from libvirtpy.xml import PresenceFlag
from libvirtpy.xml.domain import Apic, Domain, Features, FeatureState, Memory, Vcpu
from tests.helpers.xmlcompare import assert_xml_equal

EXPECTED_DIR = Path(__file__).parent / "expected"


def test_build_small_kvm_guest() -> None:
    domain = Domain(
        type="kvm",
        name="builder",
        uuid="c7a5fdbd-edaf-9455-926a-d65c16db1809",
        memory=Memory(value=2, unit="GiB"),
        vcpu=Vcpu(value=2, placement="static"),
        features=Features(
            acpi=PresenceFlag(),
            apic=Apic(),
            pmu=FeatureState(state=False),
        ),
    )

    expected = (EXPECTED_DIR / "small_kvm_guest.xml").read_bytes()
    assert_xml_equal(expected, domain.to_xml())
