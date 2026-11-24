import pytest
from pydantic import ValidationError

from libvirtpy.xml.domain import Cpu, CpuCache, CpuFeature, CpuModel, CpuTopology, Vcpu


def test_vcpu_minimal() -> None:
    vcpu = Vcpu.from_xml("<vcpu>2</vcpu>")

    assert vcpu == Vcpu(value=2)


def test_vcpu_reads_all_attributes() -> None:
    vcpu = Vcpu.from_xml("<vcpu placement='auto' cpuset='0-3,^2' current='1'>4</vcpu>")

    assert vcpu.placement == "auto"
    assert vcpu.cpuset == "0-3,^2"
    assert vcpu.current == 1


def test_vcpu_rejects_unknown_placement() -> None:
    with pytest.raises(ValidationError):
        Vcpu.from_xml("<vcpu placement='random'>4</vcpu>")


def test_host_passthrough_cpu_without_children() -> None:
    cpu = Cpu.from_xml("<cpu mode='host-passthrough' migratable='on'/>")

    assert cpu == Cpu(mode="host-passthrough", migratable=True)


def test_cpu_model_text_and_attributes() -> None:
    cpu = Cpu.from_xml("<cpu><model fallback='allow'>Haswell</model></cpu>")

    assert cpu.model == CpuModel(value="Haswell", fallback="allow")


def test_empty_cpu_model_is_kept() -> None:
    cpu = Cpu.from_xml("<cpu mode='host-model'><model/></cpu>")

    assert cpu.model == CpuModel()
    assert cpu.to_xml() == b'<cpu mode="host-model"><model/></cpu>'


def test_cpu_model_rejects_short_vendor_id() -> None:
    with pytest.raises(ValidationError):
        CpuModel(value="Haswell", vendor_id="Intel")


def test_cpu_features_keep_order() -> None:
    cpu = Cpu.from_xml(
        "<cpu><feature policy='require' name='vmx'/>"
        "<feature policy='disable' name='hle'/></cpu>"
    )

    assert cpu.features == [
        CpuFeature(policy="require", name="vmx"),
        CpuFeature(policy="disable", name="hle"),
    ]


def test_cpu_topology_requires_cores_and_threads() -> None:
    with pytest.raises(ValidationError):
        Cpu.from_xml("<cpu><topology sockets='1'/></cpu>")


def test_cpu_topology_optional_dies_stay_none() -> None:
    cpu = Cpu.from_xml("<cpu><topology sockets='2' cores='4' threads='1'/></cpu>")

    assert cpu.topology == CpuTopology(sockets=2, cores=4, threads=1)


@pytest.mark.parametrize("level", ["1", "2", "3"])
def test_cpu_cache_level_parses_from_text(level: str) -> None:
    cpu = Cpu.from_xml(f"<cpu><cache level='{level}' mode='emulate'/></cpu>")

    assert cpu.cache == CpuCache(level=int(level), mode="emulate")


def test_cpu_cache_rejects_level_four() -> None:
    with pytest.raises(ValidationError):
        Cpu.from_xml("<cpu><cache level='4' mode='emulate'/></cpu>")
