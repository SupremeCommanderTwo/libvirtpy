from pathlib import Path

from pydantic_xml import attr, element

from libvirtpy.xml._base import LibvirtXmlModel
from tools.schema_coverage import model_paths, schema_paths

RNG_HEADER = '<grammar xmlns="http://relaxng.org/ns/structure/1.0">'

COMMON_RNG = f"""{RNG_HEADER}
  <define name="leaf"><element name="leaf"><attribute name="kind"/></element></define>
  <define name="extra"><element name="replaced"><empty/></element></define>
  <define name="choices" combine="choice">
    <element name="first"><empty/></element>
  </define>
</grammar>
"""

MAIN_RNG = f"""{RNG_HEADER}
  <start><ref name="root"/></start>
  <include href="common.rng">
    <define name="extra"><element name="override"><empty/></element></define>
  </include>
  <define name="choices" combine="choice">
    <element name="second"><empty/></element>
  </define>
  <define name="root">
    <element name="root">
      <optional><attribute name="id"/></optional>
      <interleave>
        <ref name="leaf"/>
        <ref name="extra"/>
        <ref name="choices"/>
        <ref name="chain"/>
        <element name="cmd" ns="urn:x"><element name="arg"><empty/></element></element>
        <element name="metadata">
          <zeroOrMore><element><anyName/><text/></element></zeroOrMore>
        </element>
      </interleave>
    </element>
  </define>
  <define name="chain">
    <element name="chain"><optional><ref name="chain"/></optional></element>
  </define>
</grammar>
"""


def test_schema_paths_follow_includes_overrides_and_recursion(tmp_path: Path) -> None:
    (tmp_path / "common.rng").write_text(COMMON_RNG)
    (tmp_path / "main.rng").write_text(MAIN_RNG)

    assert schema_paths(tmp_path / "main.rng") == {
        "/root",
        "/root/@id",
        "/root/leaf",
        "/root/leaf/@kind",
        "/root/override",
        "/root/first",
        "/root/second",
        "/root/chain",
        "/root/{urn:x}cmd",
        "/root/{urn:x}cmd/{urn:x}arg",
        "/root/metadata",
        "/root/metadata/*",
    }


class Leaf(LibvirtXmlModel, tag="leaf"):
    kind: str = attr(name="kind")


class Root(LibvirtXmlModel, tag="root"):
    id: str | None = attr(name="id", default=None)
    leaves: list[Leaf] = element(tag="leaf", default_factory=list)
    title: str | None = element(tag="title", default=None)
    value: str | None = None


def test_model_paths_cover_attributes_elements_and_submodels() -> None:
    assert model_paths(Root) == {
        "/root",
        "/root/@id",
        "/root/leaf",
        "/root/leaf/@kind",
        "/root/title",
    }


class Chain(LibvirtXmlModel, tag="chain"):
    kind: str | None = attr(name="kind", default=None)
    next: Chain | None = element(tag="chain", default=None)


def test_model_paths_expand_a_recursive_structure_once() -> None:
    Chain.model_rebuild()

    assert model_paths(Chain) == {"/chain", "/chain/@kind"}
