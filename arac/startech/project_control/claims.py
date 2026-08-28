"""Checks for documented filenames, constants, and section references."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable


IGNORED_CONSTANT_WORDS = {
    "MEB",
    "HSV",
    "PWM",
    "GPIO",
    "CLAHE",
    "JSON",
    "HTTP",
    "HTTPS",
    "LEGACY",
    "PLAN",
    "UYARI",
    "DIKKAT",
    "STOP",
    "GG",
    "EZ",
    "RC",
    "SD",
    "USB",
    "CSI",
    "RTC",
    "NAT",
    "VPS",
    "API",
    "URL",
    "UTF",
    "SHA",
    "R2",
    "PD",
    "CV",
    "ML",
    "OK",
}


def check_file_names(
    document_names: Iterable[str],
    document_path: Callable[[str], str | None],
    existing_names: set[str],
    allowed: set[str],
) -> list[str]:
    """Require each documented filename to exist or be explicitly planned."""

    findings = []
    pattern = re.compile(
        r"\b([\w-]+\.(?:py|cs|js|json|md|pdf|txt|sh|service|csproj|html))\b"
    )
    for document in document_names:
        path = document_path(document)
        if path is None:
            continue
        with open(path, encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                for name in pattern.findall(line):
                    if name not in existing_names and name not in allowed:
                        findings.append("%s:%d  %s" % (document, number, name))
    return findings


def check_constants(
    document_names: Iterable[str],
    document_path: Callable[[str], str | None],
    source: str,
    allowed: set[str],
) -> list[str]:
    """Require documented uppercase identifiers to exist in active source."""

    findings = []
    pattern = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,})\b")
    for document in document_names:
        path = document_path(document)
        if path is None:
            continue
        with open(path, encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                for name in pattern.findall(line):
                    if name in IGNORED_CONSTANT_WORDS or name in allowed:
                        continue
                    if re.search(
                        r"\b%s\.(?:py|cs|js|json|md|pdf|txt|sh|service|csproj|html)\b"
                        % re.escape(name),
                        line,
                    ):
                        continue
                    if re.search(r"\b%s\b" % re.escape(name), source) and source.count(
                        name
                    ) > line.count(name):
                        continue
                    findings.append("%s:%d  %s" % (document, number, name))
    return findings


def check_section_references(plan_path: str | None) -> list[str]:
    """Require PLAN section references to point at a real heading."""

    if plan_path is None:
        return ["PLAN.md bulunamadi"]
    with open(plan_path, encoding="utf-8") as handle:
        text = handle.read()

    headings = {
        match.group(1)
        for match in re.finditer(
            r"^#{2,3} (\d+(?:\.\d+[a-z]?)?)\.", text, re.M
        )
    }
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        for reference in re.findall(r"§(\d+(?:\.\d+[a-z]?)?)", line):
            root_number = reference.split(".")[0]
            if reference not in headings and root_number not in headings:
                findings.append("PLAN.md:%d  §%s" % (number, reference))
        for reference in re.findall(r"[Ss]ection (\d+)", line):
            if reference not in headings:
                findings.append("PLAN.md:%d  section %s" % (number, reference))
    return findings
