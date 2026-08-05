#!/usr/bin/env python3
"""pdf_yap.py — PLAN_New.md ve HATA_DEFTERI.md dosyalarindan PDF uretir.

Kullanim:
    python pdf_yap.py            # her ucunu de uretir
    python pdf_yap.py plan       # sadece PLAN.pdf
    python pdf_yap.py hata       # sadece HATA_DEFTERI.pdf
    python pdf_yap.py paylasim   # sadece HATA_DEFTERI_PAYLASIM.pdf (isimsiz)

Gereksinim:  pip install markdown      (baska bir sey gerekmez)
PDF uretimi icin sistemde Chrome veya Edge kurulu olmali.
"""
import os
import subprocess
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

try:
    import markdown
except ImportError:
    sys.exit(
        "HATA: 'markdown' paketi yok.\n"
        "  Kur:  python -m pip install markdown\n"
    )

# --- tarayici bul (PDF motoru) ------------------------------------------
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/chromium", "/usr/bin/google-chrome", "/usr/bin/chromium-browser",
]


def find_browser():
    for b in BROWSERS:
        if os.path.exists(b):
            return b
    sys.exit("HATA: Chrome/Edge bulunamadi. PDF uretilemez.")


CSS_BASE = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Calibri, system-ui, sans-serif;
       font-size: 9.6pt; line-height: 1.45; color: #1a1a1a; margin: 0; }
h1 { font-size: 21pt; margin: 0 0 2mm; color: #111; letter-spacing: -0.2pt; }
h2 { font-size: 14pt; margin: 0 0 3mm; padding-bottom: 1.5mm;
     border-bottom: 1.4pt solid ACCENT; color: ACCENT;
     page-break-before: always; page-break-after: avoid; }
h1 + h2, h2:first-of-type { page-break-before: avoid; }
h3 { font-size: 11pt; margin: 5mm 0 2mm; color: DARKACC; page-break-after: avoid; }
h4 { font-size: 9.8pt; margin: 4mm 0 1.5mm; page-break-after: avoid; }
p { margin: 0 0 2.2mm; } p, li { orphans: 3; widows: 3; }
ul, ol { margin: 0 0 2.5mm; padding-left: 6mm; } li { margin-bottom: 1mm; }
strong { color: #000; }
code { font-family: Consolas, "Courier New", monospace; font-size: 8.6pt;
       background: #f2f4f7; padding: 0.3mm 1mm; border-radius: 1.5px;
       word-break: break-word; }
pre { background: #f6f8fa; border: 0.4pt solid #d6dbe1; border-left: 2.2pt solid ACCENT;
      padding: 2.5mm 3mm; margin: 0 0 3mm; white-space: pre-wrap;
      overflow-wrap: break-word; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.2pt; }
/* Sema kutulari (inline SVG). Bir sema iki sayfaya bolunurse okunmaz hale gelir,
   bu yuzden page-break-inside: avoid sart. Genislik yuzde olarak verilir ki
   A4 kenar bosluklarina uysun. */
.sema { page-break-inside: avoid; break-inside: avoid; margin: 3mm 0 4mm;
        text-align: center; }
.sema svg { max-width: 100%; height: auto; }
blockquote { margin: 0 0 3mm; padding: 2mm 3mm; background: #fff8e6;
             border-left: 2.2pt solid #d9a441; page-break-inside: avoid; }
blockquote p:last-child { margin-bottom: 0; }
table { border-collapse: collapse; width: 100%; margin: 0 0 3.5mm;
        font-size: 8.4pt; page-break-inside: auto; }
th, td { border: 0.4pt solid #c3c9d1; padding: 1.3mm 1.8mm;
         text-align: left; vertical-align: top; overflow-wrap: anywhere; }
th { background: THBG; font-weight: 600; color: DARKACC; }
tr { page-break-inside: avoid; }
tbody tr:nth-child(even) { background: #fafbfc; }
hr { border: none; border-top: 0.5pt solid #ccd2da; margin: 4mm 0; }
a { color: ACCENT; text-decoration: none; }
.cover { page-break-after: always; padding-top: 52mm; text-align: center; }
.cover .sub { font-size: 12pt; color: #4a5568; margin-top: 3mm; }
.cover .meta { margin-top: 26mm; font-size: 9pt; color: #6b7280; line-height: 1.8; }
.cover .warn { margin: 18mm auto 0; max-width: 128mm; font-size: 8.6pt;
               color: #7a4a00; background: #fff8e6; border: 0.5pt solid #d9a441;
               padding: 3mm 4mm; text-align: left; line-height: 1.55; }
.toc { page-break-after: always; }
.toc ul { list-style: none; padding-left: 4mm; } .toc > ul { padding-left: 0; }
.toc a { color: #1a1a1a; } .toc li { margin-bottom: 0.8mm; font-size: 9pt; }
.toc > ul > li { font-weight: 600; margin-top: 1.6mm; }
.toc > ul > li ul li { font-weight: 400; color: #444; }
"""

WARN_PLAN = """<strong>This PDF is a read-only snapshot.</strong> The living document is
<code>PLAN_New.md</code> in the project repository &mdash; edit that, never this. If this
file and the repository disagree, the repository is right.<br><br>
<strong>New here?</strong> Read only section&nbsp;0.0 (&ldquo;Coming back after a
break&rdquo;). It is one page and it is the front door.<br><br>
<strong>Tuna:</strong> read <code>Tuna.txt</code> instead &mdash; it is written for you."""

WARN_HATA = """<strong>This PDF is a read-only snapshot.</strong> The living document is
<code>HATA_DEFTERI.md</code>; <code>PLAN_New.md</code> is authoritative above both.<br><br>
<strong>Read section&nbsp;0 before the defect list.</strong> A fault list read on its own
gives a false impression of the build it describes, and section&nbsp;0 is not padding.<br><br>
<strong>The output of this document is section&nbsp;7</strong> &mdash; seven guards. The
list of faults is only the evidence for them."""

# name, source, output pdf, title, subtitle, warn, accent, anonymous?
JOBS = {
    "plan": ("PLAN_New.md", "PLAN.pdf", "PLAN",
             "Otonom Ara&ccedil; &mdash; full project plan",
             WARN_PLAN, ("#2a4d7a", "#14385e", "#eef2f7"), True),
    "hata": ("HATA_DEFTERI.md", "HATA_DEFTERI.pdf", "HATA DEFTER\u0130",
             "LEGACY defect log &mdash; 4 May 2026 build",
             WARN_HATA, ("#7a2a2a", "#5e1414", "#f7eeee"), True),
    "paylasim": ("HATA_DEFTERI.md", "HATA_DEFTERI_PAYLASIM.pdf", "HATA DEFTER\u0130",
                 "Autonomous car &mdash; defect log of a previous build",
                 WARN_HATA, ("#7a2a2a", "#5e1414", "#f7eeee"), True),
}


def build(key):
    src, out_pdf, title, subtitle, warn, colours, anon = JOBS[key]
    src_path = os.path.join(HERE, src)
    if not os.path.exists(src_path):
        print(f"  atlandi (kaynak yok): {src}")
        return
    with open(src_path, encoding="utf-8") as f:
        text = f.read()

    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "toc", "sane_lists", "attr_list"])
    body, toc = md.convert(text), md.toc
    built = datetime.date.today().strftime("%d %B %Y")

    accent, dark, thbg = colours
    css = (CSS_BASE.replace("ACCENT", accent)
                   .replace("DARKACC", dark)
                   .replace("THBG", thbg))

    if anon:
        org = ("<div class='sub' style='font-size:10pt;'>MEB Uluslararas&#305; "
               "Robot Yar&#305;&#351;mas&#305; &middot; Otonom Ara&ccedil;</div>")
        meta = f"Snapshot built {built}"
    else:
        org = ("<div class='sub' style='font-size:10pt;'>Dyl-Startech &middot; "
               "MEB Uluslararas&#305; Robot Yar&#305;&#351;mas&#305;</div>")
        meta = ("Egemen Yusuf K. &middot; Tuna B.<br>"
                "Dan&#305;&#351;man: Mehmet Emin U.<br><br>"
                f"Snapshot built {built}")

    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>{css}</style></head><body>"
        f"<div class='cover'><h1 style='border:none;font-size:26pt;'>{title}</h1>"
        f"<div class='sub'>{subtitle}</div>{org}"
        f"<div class='meta'>{meta}</div>"
        f"<div class='warn'>{warn}</div></div>"
        "<div class='toc'><h2 style='page-break-before:avoid;'>Contents</h2>"
        f"{toc}</div>{body}</body></html>"
    )

    tmp_html = os.path.join(HERE, f".{key}_tmp.html")
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(html)

    out_path = os.path.join(HERE, out_pdf)
    subprocess.run([find_browser(), "--headless", "--disable-gpu",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={out_path}",
                    "file:///" + tmp_html.replace("\\", "/")],
                   check=True, capture_output=True)
    os.remove(tmp_html)
    size = os.path.getsize(out_path) / 1024
    print(f"  {out_pdf}  ({size:.0f} KB)")


if __name__ == "__main__":
    keys = sys.argv[1:] or list(JOBS)
    bad = [k for k in keys if k not in JOBS]
    if bad:
        sys.exit(f"Bilinmeyen hedef: {bad}. Secenekler: {list(JOBS)}")
    print("PDF uretiliyor...")
    for k in keys:
        build(k)
    print("Bitti.")
