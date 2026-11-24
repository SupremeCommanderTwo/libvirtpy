"""RelaxNG validation against libvirt's schemas from the corpus cache."""

from functools import cache
from pathlib import Path

from lxml import etree

__all__ = ["schema_errors"]


def schema_errors(schema: Path, document: str | bytes) -> str | None:
    """Return the validation errors of ``document``, or ``None`` if it is valid."""
    validator = _relaxng(schema)
    if validator.validate(etree.fromstring(document)):
        return None
    return "\n".join(str(error) for error in validator.error_log)


@cache
def _relaxng(schema: Path) -> etree.RelaxNG:
    return etree.RelaxNG(etree.parse(str(schema)))
