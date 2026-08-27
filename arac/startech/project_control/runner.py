"""Composition and terminal reporting for project consistency checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .claims import check_constants, check_file_names, check_section_references
from .measurements import check_measurements
from .repository import (
    allowed_names,
    file_names,
    line_exemptions,
    missing_documents,
    source_text,
)


DocumentPath = Callable[[str], str | None]


@dataclass(frozen=True)
class CheckContext:
    project_root: str
    allow_file: str
    document_names: tuple[str, ...]
    skip_dirs: set[str]
    document_path: DocumentPath


CHECK_NAMES = (
    "Beklenen belgeler bulunabiliyor mu",
    "Belgede adı geçen dosyalar var mı",
    "Belgede adı geçen sabitler kodda var mı",
    "PLAN.md bölüm atıfları geçerli mi",
    "Performans sayıları tarih taşıyor mu",
)


def check_names() -> tuple[str, ...]:
    return CHECK_NAMES


def _build_checks(context: CheckContext):
    source = source_text(context.project_root, context.skip_dirs)
    names = file_names(context.project_root, context.skip_dirs)
    allowed = allowed_names(context.allow_file, context.document_path)
    exemptions = line_exemptions(context.allow_file)

    return (
        lambda: [
            "BULUNAMADI: " + name
            for name in missing_documents(
                context.document_names, context.document_path
            )
        ],
        lambda: check_file_names(
            context.document_names,
            context.document_path,
            names,
            allowed,
        ),
        lambda: check_constants(
            context.document_names,
            context.document_path,
            source,
            allowed,
        ),
        lambda: check_section_references(context.document_path("PLAN.md")),
        lambda: check_measurements(
            context.document_names,
            context.document_path,
            exemptions,
        ),
    )


def run_checks(context: CheckContext) -> int:
    """Run all checks, print the established report format, and return an exit code."""

    failed = 0
    for name, check in zip(CHECK_NAMES, _build_checks(context)):
        findings = check()
        if findings:
            failed += 1
            print("\n[DUSTU] %s  (%d)" % (name, len(findings)))
            for finding in findings[:20]:
                print("        " + finding)
            if len(findings) > 20:
                print("        ... ve %d tane daha" % (len(findings) - 20))
        else:
            print("[TAMAM] %s" % name)

    print("")
    if failed:
        print(
            "%d kontrol dustu. Yanlis pozitifse kontrol-izin.txt'ye ekleyin."
            % failed
        )
        return 1
    print("Butun kontroller temiz.")
    return 0
