"""Repository discovery and documented-exception loading."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable


SOURCE_EXTENSIONS = (
    ".py",
    ".cs",
    ".js",
    ".json",
    ".sh",
    ".service",
    ".txt",
    ".md",
)


def missing_documents(
    document_names: Iterable[str],
    document_path: Callable[[str], str | None],
) -> list[str]:
    """Return the expected documents that cannot be located."""

    return [name for name in document_names if document_path(name) is None]


def source_text(project_root: str, skip_dirs: set[str]) -> str:
    """Collect active textual repository content into one searchable string."""

    parts = []
    for root, directories, files in os.walk(project_root):
        directories[:] = [name for name in directories if name not in skip_dirs]
        for name in files:
            if name.endswith(SOURCE_EXTENSIONS):
                try:
                    with open(
                        os.path.join(root, name), encoding="utf-8", errors="ignore"
                    ) as handle:
                        parts.append(handle.read())
                except OSError:
                    pass
    return "\n".join(parts)


def file_names(project_root: str, skip_dirs: set[str]) -> set[str]:
    """Return every file basename in the active repository tree."""

    names = set()
    for _, directories, files in os.walk(project_root):
        directories[:] = [name for name in directories if name not in skip_dirs]
        names.update(files)
    return names


def allowed_names(
    allow_file: str,
    document_path: Callable[[str], str | None],
) -> set[str]:
    """Load planned filenames and explicit exceptions."""

    allowed = set()

    if os.path.exists(allow_file):
        with open(allow_file, encoding="utf-8") as handle:
            for line in handle:
                line = line.split("#")[0].strip()
                if line and not line.startswith("SATIR:"):
                    allowed.add(line)
    return allowed


def line_exemptions(allow_file: str) -> list[str]:
    """Load text-based line exemptions from the explicit allow file."""

    exemptions = []
    if os.path.exists(allow_file):
        with open(allow_file, encoding="utf-8") as handle:
            for line in handle:
                line = line.split("#")[0].strip()
                if line.startswith("SATIR:"):
                    exemptions.append(line[6:].strip())
    return exemptions
