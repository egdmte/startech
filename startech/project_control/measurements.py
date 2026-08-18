"""Check that documented performance numbers carry evidence or uncertainty."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable


MEASUREMENT_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?\s+(fps|FPS|px)\b")
UNCERTAINTY_PATTERN = re.compile(
    r"(tahmin|hedef|beklenen|olmalı|civar|yaklaşık|~|"
    r"uydur|iddia|ölçülmedi|asla ölçül|"
    r"expect|target|should|about|roughly|estimate|"
    r"never (?:measured|taken|run)|invented|fabricat|"
    r"claimed|asserted|presented as)",
    re.I,
)
YEAR_PATTERN = re.compile(r"\b20\d\d\b")


def check_measurements(
    document_names: Iterable[str],
    document_path: Callable[[str], str | None],
    exemptions: list[str],
) -> list[str]:
    """Require measured-looking numbers to have a date or uncertainty marker."""

    findings = []
    for document in document_names:
        path = document_path(document)
        if path is None:
            continue
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()

        for index, line in enumerate(lines):
            if not MEASUREMENT_PATTERN.search(line):
                continue
            if any(exemption and exemption in line for exemption in exemptions):
                continue
            context = "\n".join(lines[max(0, index - 3) : index + 2])
            if YEAR_PATTERN.search(context) or UNCERTAINTY_PATTERN.search(context):
                continue
            findings.append(
                "%s:%d  %s" % (document, index + 1, line.strip()[:90])
            )
    return findings
