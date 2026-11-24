"""Terminal summary for the corpus round-trip run (``pytest -m corpus``)."""

import os
import re
from collections import Counter

import pytest

from tests.helpers.corpus import corpus_version
from tests.roundtrip.test_corpus_roundtrip import DIFFERENCES_PROPERTY, SCHEMA_PROPERTY

TOP_DIFFERENCES = int(os.environ.get("CORPUS_TOP", "40"))

_INDEX = re.compile(r"\[\d+\]")


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    by_schema = _roundtrip_results(terminalreporter)
    if not by_schema:
        return

    write = terminalreporter.write_line
    terminalreporter.section("libvirt corpus round-trip")
    for schema, results in sorted(by_schema.items()):
        passing = sum(1 for found in results if not found)
        share = 100 * passing / len(results)

        write(
            f"libvirt {corpus_version()} {schema}: "
            f"{passing}/{len(results)} files ({share:.1f}%)"
        )

        # Count each key once per file, so the ranking is "files affected".
        ranking = Counter(
            key for found in results for key in {_difference_key(d) for d in found}
        )

        for key, count in ranking.most_common(TOP_DIFFERENCES):
            write(f"{count:6d}  {key}")


def _difference_key(difference: str) -> str:
    """Turn a difference into a ranking key: path without indexes, plus its kind.

    ``/domain/devices/disk[2]/@bus: 'virtio' != None`` -> ``/domain/devices/disk/@bus``
    ``/domain/os: missing element`` -> ``/domain/os (missing element)``
    """
    path, _, detail = difference.partition(": ")
    path = _INDEX.sub("", path)

    if path.startswith("parse error"):
        return difference
    if detail.endswith("element"):
        return f"{path} ({detail})"
    return path


def _roundtrip_results(
    terminalreporter: pytest.TerminalReporter,
) -> dict[str, list[list[str]]]:
    """Return the differences of every file, grouped by schema."""
    results: dict[str, list[list[str]]] = {}
    for outcome in ("passed", "failed"):
        for report in terminalreporter.stats.get(outcome, []):
            properties = dict(getattr(report, "user_properties", []))
            if DIFFERENCES_PROPERTY not in properties:
                continue
            schema = properties.get(SCHEMA_PROPERTY, "unknown")
            results.setdefault(schema, []).append(properties[DIFFERENCES_PROPERTY])
    return results
