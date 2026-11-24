from libvirtpy.xml import PresenceFlag
from libvirtpy.xml.domain import Apic, Features, FeatureState


def test_features_presence_flags_parse() -> None:
    features = Features.from_xml("<features><acpi/><pae/></features>")

    assert features.acpi == PresenceFlag()
    assert features.pae == PresenceFlag()
    assert features.viridian is None


def test_empty_features_element_is_kept() -> None:
    assert Features.from_xml("<features/>").to_xml() == b"<features/>"


def test_feature_without_state_keeps_state_none() -> None:
    features = Features.from_xml("<features><hap/></features>")

    assert features.hap == FeatureState(state=None)
    assert features.to_xml() == b"<features><hap/></features>"


def test_feature_state_is_on_off() -> None:
    features = Features.from_xml("<features><pmu state='off'/></features>")

    assert features.pmu == FeatureState(state=False)


def test_apic_with_eoi() -> None:
    features = Features(apic=Apic(eoi=True))

    assert features.to_xml() == b'<features><apic eoi="on"/></features>'
