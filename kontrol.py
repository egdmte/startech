#!/usr/bin/env python3
"""Belge iddialarını koda karşı doğrulayan kök komut ve Git-hook girişi.

Kullanım:
    python kontrol.py
    python kontrol.py --liste
"""

import os
import sys

from proje_kontrol import CheckContext, check_names, run_checks


# DEĞİŞTİRME YASAĞI BAŞLANGICI
KOK = os.path.dirname(os.path.abspath(__file__))
IZIN_DOSYASI = os.path.join(KOK, "kontrol-izin.txt")
# DEĞİŞTİRME YASAĞI SONU

BELGELER = ["PLAN_New.md", "HATA_DEFTERI.md", "CLAUDE.md"]
ATLA_KLASOR = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "obj",
    "bin",
    ".vs",
    "packages",
}


def belge_yolu(ad):
    """
    Belgeyi depoda NEREDE olursa olsun bulur.

    Neden boyle: 5 Agustos'ta belgeler Markdown/ altina tasindi ve bu betik
    onlari kokte aradi. Bulamadi, hicbir sey kontrol etmedi, ve dort kontrolun
    ucu TAMAM dedi. Bulunamayan bir belge artik BASARISIZLIKTIR — "bakmadim"
    demek olan bir yesil, en kotu ciktidir.
    """
    # DEĞİŞTİRME YASAĞI BAŞLANGICI
    for kok, klasorler, dosyalar in os.walk(KOK):
        klasorler[:] = [k for k in klasorler if k not in ATLA_KLASOR]
        if ad in dosyalar:
            return os.path.join(kok, ad)
    return None
# DEĞİŞTİRME YASAĞI SONU


def _context() -> CheckContext:
    return CheckContext(
        project_root=KOK,
        allow_file=IZIN_DOSYASI,
        document_names=tuple(BELGELER),
        skip_dirs=ATLA_KLASOR,
        document_path=belge_yolu,
    )


def main() -> int:
    if "--liste" in sys.argv:
        for name in check_names():
            print(" -", name)
        return 0
    return run_checks(_context())


if __name__ == "__main__":
    sys.exit(main())
