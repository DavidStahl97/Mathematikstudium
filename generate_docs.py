#!/usr/bin/env python3
"""
Generiert MkDocs-Dokumentation aus der skripte/-Ordnerstruktur.

- Traversiert skripte/ rekursiv
- Baut Navigationsstruktur aus Ordnerhierarchie
- Für jede .tex-Datei (Leaf): erstellt .md-Seite mit eingebetteter PDF
- Für jede Lektion mit Glossar/glossar.tex: erstellt lernkarten.md
- Kopiert PDFs nach docs/assets/pdfs/
- Aktualisiert den nav-Abschnitt in mkdocs.yml
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import yaml
from pathlib import Path

SKRIPTE_DIR = Path("skripte")
DOCS_DIR = Path("docs")
MKDOCS_FILE = Path("mkdocs.yml")

PDFLATEX = (os.environ.get("PDFLATEX") or shutil.which("pdflatex")
            or "/c/texlive/2026/bin/windows/pdflatex.exe")
PDFTOCAIRO = (os.environ.get("PDFTOCAIRO") or shutil.which("pdftocairo")
              or "/c/texlive/2026/bin/windows/pdftocairo.exe")


def folder_to_title(name: str) -> str:
    """Ordnername zu lesbarem Titel: 'lektion-1' → 'Lektion 1'"""
    return name.replace("-", " ").title()


def tex_to_title(stem: str) -> str:
    """Dateiname zu Titel: 'aufgabe-1_1' → 'Aufgabe 1.1'"""
    return stem.replace("_", ".").replace("-", " ").title()


# ---------------------------------------------------------------------------
# Lernkarten-Logik
# ---------------------------------------------------------------------------

def _extract_brace(s: str, pos: int) -> tuple[str, int]:
    """Extract content of {…} starting at pos. Returns (content, end_pos)."""
    assert s[pos] == '{', f"Expected '{{' at pos {pos}, got {s[pos]!r}"
    depth = 1
    i = pos + 1
    while i < len(s) and depth > 0:
        if s[i] == '\\' and i + 1 < len(s):
            i += 2  # skip escape sequence (e.g. \{ \})
            continue
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
        i += 1
    return s[pos + 1:i - 1], i


def extract_flashcards(tex_path: Path) -> list[dict]:
    r"""Parse glossar.tex and return [{front, back}] dicts for each \gentry."""
    text = tex_path.read_text(encoding='utf-8')
    cards = []
    for m in re.finditer(r'\\gentry\b', text):
        pos = m.end()
        while pos < len(text) and text[pos] in ' \t\n':
            pos += 1
        if pos >= len(text) or text[pos] != '{':
            continue
        try:
            num, pos = _extract_brace(text, pos)
            while pos < len(text) and text[pos] in ' \t\n':
                pos += 1
            title, pos = _extract_brace(text, pos)
            while pos < len(text) and text[pos] in ' \t\n':
                pos += 1
            content, pos = _extract_brace(text, pos)
        except (AssertionError, IndexError):
            continue
        num = num.strip()
        title = title.strip()
        front_tex = f"{num}\\quad {title}" if num else title
        cards.append({'front': front_tex, 'back': content.strip()})
    return cards


_CARDS_TEX_PREAMBLE = r"""\documentclass[border=10pt,varwidth=8cm,multi=lkcard]{standalone}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[ngerman]{babel}
\usepackage{amsmath, amssymb}
\usepackage{enumitem}
\usepackage{array, booktabs}
\begin{document}
"""


def render_cards_to_svg(cards: list[dict], svg_out_dir: Path) -> bool:
    """Kompiliert alle Karten via pdflatex + pdftocairo zu SVGs.

    Erzeugt card-<k>-front.svg / card-<k>-back.svg in svg_out_dir (k ist 1-basiert).
    """
    if not cards:
        return False
    svg_out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="lernkarten_") as tmp:
        tmp_dir = Path(tmp)
        tex_lines = [_CARDS_TEX_PREAMBLE]
        for c in cards:
            tex_lines.append(r"\begin{lkcard}")
            tex_lines.append(r"\textbf{" + c["front"] + "}")
            tex_lines.append(r"\end{lkcard}")
            tex_lines.append(r"\begin{lkcard}")
            tex_lines.append(c["back"])
            tex_lines.append(r"\end{lkcard}")
        tex_lines.append(r"\end{document}")
        tex_file = tmp_dir / "cards.tex"
        tex_file.write_text("\n".join(tex_lines), encoding="utf-8")

        try:
            subprocess.run(
                [PDFLATEX, "-interaction=nonstopmode", "-halt-on-error",
                 "-output-directory", str(tmp_dir), str(tex_file)],
                check=True, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError:
            print(f"  [ERROR] pdflatex fehlgeschlagen fuer {svg_out_dir}", file=sys.stderr)
            log = tmp_dir / "cards.log"
            if log.exists():
                tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
                print("\n".join(tail), file=sys.stderr)
            return False

        pdf_file = tmp_dir / "cards.pdf"
        if not pdf_file.exists():
            print(f"  [ERROR] cards.pdf nicht erzeugt fuer {svg_out_dir}", file=sys.stderr)
            return False

        for i in range(len(cards)):
            for side, page in (("front", 2 * i + 1), ("back", 2 * i + 2)):
                out_svg = svg_out_dir / f"card-{i + 1}-{side}.svg"
                try:
                    subprocess.run(
                        [PDFTOCAIRO, "-svg", "-f", str(page), "-l", str(page),
                         str(pdf_file), str(out_svg)],
                        check=True, capture_output=True, text=True,
                    )
                except subprocess.CalledProcessError as e:
                    print(f"  [ERROR] pdftocairo (Seite {page}) fuer {out_svg}: {e.stderr}",
                          file=sys.stderr)
                    return False
    return True

_FLASHCARD_TEMPLATE = """\
# Lernkarten -- __LESSON_TITLE__

<div id="fc-grid-view">
  <p style="color:#666;font-size:.9em">__CARD_COUNT__ Karten &middot; auf eine Karte klicken zum Lernen</p>
  <div class="fc-grid" id="fc-grid"></div>
</div>

<div id="fc-detail-view" style="display:none">
  <div class="fc-toolbar">
    <button class="md-button" onclick="fcGoToGrid()">&#8592; &Uuml;bersicht</button>
    <span class="fc-progress">Karte <span id="fc-curr">1</span> von <span id="fc-total">__CARD_COUNT__</span></span>
  </div>
  <p style="color:#666;font-size:.85em;text-align:center;margin:.2em 0 1em">Leertaste/Klick: umdrehen &middot; &larr; &rarr;: bl&auml;ttern</p>
  <div class="fc-scene" id="fc-scene" title="Klicken zum Umdrehen">
    <div class="fc-card" id="fc-card">
      <div class="fc-face fc-front"><img id="fc-front-img" alt="Vorderseite"></div>
      <div class="fc-face fc-back"><img id="fc-back-img" alt="R&uuml;ckseite"></div>
    </div>
  </div>
  <div class="fc-btns">
    <button class="md-button" onclick="fcPrev()">&#8592; Zur&uuml;ck</button>
    <button class="md-button md-button--primary" onclick="fcFlip()">Umdrehen</button>
    <button class="md-button" onclick="fcNext()">Weiter &#8594;</button>
  </div>
</div>

<style>
#fc-detail-view{max-width:820px;margin:1.5em auto;text-align:center}
.fc-toolbar{position:sticky;top:3rem;z-index:5;background:var(--md-default-bg-color,#fff);display:flex;align-items:center;justify-content:space-between;gap:1em;padding:.6em 0;border-bottom:1px solid rgba(0,0,0,.08);margin-bottom:.5em}
.fc-progress{color:#555;font-size:.9em}
.fc-scene{perspective:1400px;margin-bottom:1.2em;cursor:pointer}
.fc-card{position:relative;width:100%;height:100%;transform-style:preserve-3d;transition:transform .45s cubic-bezier(.4,0,.2,1)}
.fc-card.flipped{transform:rotateY(180deg)}
.fc-face{position:absolute;inset:0;backface-visibility:hidden;-webkit-backface-visibility:hidden;border:2px solid #3f51b5;border-radius:10px;display:flex;align-items:center;justify-content:center;padding:1.2em 1.6em;box-sizing:border-box;overflow:auto;background:#fff}
.fc-front{background:#e8eaf6}
.fc-back{transform:rotateY(180deg)}
.fc-face img{width:100%;height:auto;display:block}
.fc-btns{display:flex;gap:.8em;justify-content:center;flex-wrap:wrap}

.fc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1em;margin:1em 0}
.fc-tile{display:flex;flex-direction:column;align-items:center;justify-content:center;border:2px solid #3f51b5;border-radius:10px;background:#e8eaf6;padding:.9em .8em;cursor:pointer;transition:transform .12s,box-shadow .12s;text-decoration:none;color:inherit;min-height:120px}
.fc-tile:hover{transform:translateY(-2px);box-shadow:0 4px 10px rgba(63,81,181,.25);background:#dfe3f7}
.fc-tile img{width:100%;height:auto;max-height:90px;object-fit:contain;display:block}
.fc-tile-label{margin-top:.6em;font-size:.78em;color:#3f51b5;font-weight:600}
</style>

<script>
const FC_CARDS = __CARDS_JSON__;
const FC_BASE = "__SVG_BASE__";
let fcIdx = 0;

function fcRenderGrid() {
  const g = document.getElementById('fc-grid');
  g.innerHTML = FC_CARDS.map((c, i) =>
    '<a class="fc-tile" href="#card-' + (i + 1) + '">' +
      '<img loading="lazy" src="' + FC_BASE + c.front + '" alt="Karte ' + (i + 1) + '">' +
      '<div class="fc-tile-label">Karte ' + (i + 1) + '</div>' +
    '</a>'
  ).join('');
}

function fcShow(i) {
  document.getElementById('fc-card').classList.remove('flipped');
  const frontImg = document.getElementById('fc-front-img');
  const backImg = document.getElementById('fc-back-img');
  frontImg.src = FC_BASE + FC_CARDS[i].front;
  backImg.src = FC_BASE + FC_CARDS[i].back;
  document.getElementById('fc-curr').textContent = i + 1;
  Promise.all([
    frontImg.complete ? Promise.resolve() : new Promise(r => { frontImg.onload = r; frontImg.onerror = r; }),
    backImg.complete ? Promise.resolve() : new Promise(r => { backImg.onload = r; backImg.onerror = r; }),
  ]).then(fcResize);
}
function fcResize() {
  const scene = document.getElementById('fc-scene');
  const front = document.getElementById('fc-front-img');
  const back = document.getElementById('fc-back-img');
  if (!front.naturalWidth || !back.naturalWidth) return;
  const padX = 1.6 * 16 * 2 + 4;
  const padY = 1.2 * 16 * 2 + 4;
  const availW = scene.clientWidth - padX;
  const hF = availW * (front.naturalHeight / front.naturalWidth);
  const hB = availW * (back.naturalHeight / back.naturalWidth);
  scene.style.height = (Math.max(hF, hB) + padY) + 'px';
}
window.addEventListener('resize', fcResize);
function fcFlip() { document.getElementById('fc-card').classList.toggle('flipped'); }
function fcNext() {
  fcIdx = (fcIdx + 1) % FC_CARDS.length;
  history.replaceState(null, '', '#card-' + (fcIdx + 1));
  fcShow(fcIdx);
}
function fcPrev() {
  fcIdx = (fcIdx - 1 + FC_CARDS.length) % FC_CARDS.length;
  history.replaceState(null, '', '#card-' + (fcIdx + 1));
  fcShow(fcIdx);
}
function fcGoToGrid() {
  history.pushState(null, '', window.location.pathname + window.location.search);
  fcRoute();
  window.scrollTo({top: 0, behavior: 'smooth'});
}

function fcRoute() {
  const m = window.location.hash.match(/^#card-(\\d+)$/);
  const gridView = document.getElementById('fc-grid-view');
  const detailView = document.getElementById('fc-detail-view');
  if (m) {
    const i = Math.max(0, Math.min(FC_CARDS.length - 1, parseInt(m[1], 10) - 1));
    const wasGrid = gridView.style.display !== 'none';
    fcIdx = i;
    gridView.style.display = 'none';
    detailView.style.display = '';
    fcShow(i);
    if (wasGrid) window.scrollTo({top: detailView.offsetTop - 70, behavior: 'auto'});
  } else {
    gridView.style.display = '';
    detailView.style.display = 'none';
  }
}

document.getElementById('fc-scene').addEventListener('click', fcFlip);
document.addEventListener('keydown', function(e) {
  if (document.getElementById('fc-detail-view').style.display === 'none') return;
  if (e.key === 'ArrowRight') fcNext();
  else if (e.key === 'ArrowLeft') fcPrev();
  else if (e.key === ' ') { e.preventDefault(); fcFlip(); }
});
window.addEventListener('hashchange', fcRoute);

fcRenderGrid();
fcRoute();
</script>
"""


def generate_flashcard_page(
    glossar_tex: Path, out_md: Path, lesson_title: str,
    svg_out_dir: Path, svg_base_url: str,
) -> bool:
    """Generate a Lernkarten .md page with SVG-rendered cards.

    Returns True wenn die Seite erfolgreich geschrieben wurde, sonst False.
    """
    cards = extract_flashcards(glossar_tex)
    if not cards:
        return False
    if not render_cards_to_svg(cards, svg_out_dir):
        print(f"  [WARN] Keine Lernkarten-SVGs erzeugt fuer {glossar_tex}",
              file=sys.stderr)
        return False
    refs = [
        {"front": f"card-{i + 1}-front.svg", "back": f"card-{i + 1}-back.svg"}
        for i in range(len(cards))
    ]
    cards_json = json.dumps(refs, ensure_ascii=False)
    content = (
        _FLASHCARD_TEMPLATE
        .replace("__LESSON_TITLE__", lesson_title)
        .replace("__CARD_COUNT__", str(len(cards)))
        .replace("__CARDS_JSON__", cards_json)
        .replace("__SVG_BASE__", svg_base_url)
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(content, encoding="utf-8")
    print(f"  Lernkarten: {len(cards)} Karten -> {out_md}")
    return True


# ---------------------------------------------------------------------------
# Docs-Baum
# ---------------------------------------------------------------------------

def build_tree(skripte_path: Path, docs_path: Path, site_url: str) -> list:
    """
    Rekursiv Ordner traversieren, .md-Dateien erzeugen, Nav-Liste zurückgeben.
    skripte_path: aktueller Pfad in skripte/
    docs_path:    korrespondierender Pfad in docs/
    site_url:     absolute Basis-URL der GitHub Pages Site (mit trailing slash)
    """
    items = []
    docs_path.mkdir(parents=True, exist_ok=True)

    # Lernkarten-Seite, wenn dieses Verzeichnis ein glossar.tex enthält
    glossar_tex = skripte_path / "glossar.tex"
    if glossar_tex.exists():
        fc_md = docs_path / "lernkarten.md"
        rel_from_docs = docs_path.relative_to(DOCS_DIR)
        svg_out_dir = DOCS_DIR / "assets" / "lernkarten" / rel_from_docs
        depth = len(rel_from_docs.parts) + 1
        svg_base_url = "../" * depth + str(
            Path("assets/lernkarten") / rel_from_docs
        ).replace("\\", "/") + "/"
        if generate_flashcard_page(
            glossar_tex, fc_md, folder_to_title(skripte_path.name),
            svg_out_dir, svg_base_url,
        ):
            rel = str(fc_md.relative_to(DOCS_DIR)).replace("\\", "/")
            items.append({"Lernkarten": rel})

    for entry in sorted(skripte_path.iterdir()):
        if entry.is_dir():
            sub_docs = docs_path / entry.name
            sub_docs.mkdir(parents=True, exist_ok=True)
            sub_items = build_tree(entry, sub_docs, site_url)
            if sub_items:
                items.append({folder_to_title(entry.name): sub_items})

        elif entry.suffix == ".tex":
            stem = entry.stem
            title = tex_to_title(stem)

            # Relativer Pfad von docs/ zur aktuellen docs_path
            rel_from_docs = docs_path.relative_to(DOCS_DIR)

            # PDF: während der Action liegt sie neben der .tex
            pdf_src = entry.with_suffix(".pdf")

            # Ziel der PDF in docs/assets/pdfs/
            pdf_dest = DOCS_DIR / "assets" / "pdfs" / rel_from_docs / f"{stem}.pdf"
            pdf_dest.parent.mkdir(parents=True, exist_ok=True)

            if pdf_src.exists():
                shutil.copy2(pdf_src, pdf_dest)
            else:
                # Platzhalter, damit die Seite trotzdem generiert wird
                print(f"  [WARN] PDF nicht gefunden: {pdf_src}")

            # Relativer Pfad von der .md-Seite zur PDF
            # MkDocs rendert page.md als page/index.html → eine Ebene tiefer
            rel_pdf_from_dir = os.path.relpath(pdf_dest, docs_path)
            rel_pdf_for_page = "../" + rel_pdf_from_dir

            # Absoluter URL zur PDF (für PDF.js Viewer benötigt)
            pdf_rel_url = str(rel_from_docs / f"{stem}.pdf").replace("\\", "/")
            pdf_absolute_url = f"{site_url}assets/pdfs/{pdf_rel_url}"
            pdf_encoded = urllib.parse.quote(pdf_absolute_url, safe="")

            # Relativer Pfad vom Seitenverzeichnis zum PDF.js Viewer
            # MkDocs rendert page.md als page/index.html → depth = Tiefe + 1
            depth = len(rel_from_docs.parts) + 1
            viewer_prefix = "../" * depth
            viewer_url = f"{viewer_prefix}assets/pdfjs/web/viewer.html"

            # Markdown-Seite generieren
            md_file = docs_path / f"{stem}.md"
            md_content = f"""# {title}

<a href="{rel_pdf_for_page}" download class="md-button md-button--primary">
  PDF herunterladen
</a>
<a href="{pdf_absolute_url}" target="_blank" class="md-button">
  Anzeigen
</a>

<br><br>

<iframe
  src="{viewer_url}?file={pdf_encoded}"
  width="100%"
  height="850px"
  style="border: none;"
></iframe>
"""
            md_file.write_text(md_content, encoding="utf-8")

            # Nav-Eintrag: Pfad relativ zu docs/
            nav_path = str((rel_from_docs / f"{stem}.md")).replace("\\", "/")
            items.append({title: nav_path})

    return items


def find_first_tex_page(module_path: Path) -> str | None:
    """Gibt den relativen Docs-Pfad zur ersten .tex-Datei im Modul zurück."""
    for tex in sorted(module_path.rglob("*.tex")):
        rel = tex.relative_to(SKRIPTE_DIR)
        return str(rel.with_suffix(".md")).replace("\\", "/")
    return None


def build_module_table(skripte_path: Path) -> str:
    """Erstellt eine Markdown-Tabelle aller Module mit Links."""
    rows = []
    for entry in sorted(skripte_path.iterdir()):
        if entry.is_dir():
            title = folder_to_title(entry.name)
            first_page = find_first_tex_page(entry)
            if first_page:
                rows.append(f"| [{title}]({first_page}) |")
            else:
                rows.append(f"| {title} |")

    if not rows:
        return ""

    lines = [
        "| Modul |",
        "| ----- |",
    ] + rows
    return "\n".join(lines) + "\n"


SOURCE_ICONS_DIR = Path("assets/icons")


def generate_pwa_assets(site_url: str) -> None:
    """Erstellt manifest.webmanifest, sw.js und PWA-Icons in docs/."""

    icons_dir = DOCS_DIR / "assets" / "images" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        src = SOURCE_ICONS_DIR / f"icon-{size}.png"
        dst = icons_dir / f"icon-{size}.png"
        if src.exists():
            shutil.copy2(src, dst)
        else:
            print(f"  [WARN] Icon nicht gefunden: {src}")

    # manifest.webmanifest
    manifest = {
        "name": "Mathematikstudium",
        "short_name": "MathStudium",
        "description": "Zusammenfassungen und Einsendeaufgaben zum Mathematikstudium",
        "start_url": site_url,
        "scope": site_url,
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#3f51b5",
        "icons": [
            {
                "src": site_url + "assets/images/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": site_url + "assets/images/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
    }
    (DOCS_DIR / "manifest.webmanifest").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Service Worker – Cache-First-Strategie
    base = site_url.rstrip("/")
    sw_content = f"""const CACHE = 'mathematikstudium-v1';
const BASE = '{base}/';

self.addEventListener('install', event => {{
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll([BASE, BASE + 'index.html']))
  );
}});

self.addEventListener('activate', event => {{
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
}});

self.addEventListener('fetch', event => {{
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then(cached => {{
      const network = fetch(event.request).then(response => {{
        if (response.ok) {{
          caches.open(CACHE).then(cache => cache.put(event.request, response.clone()));
        }}
        return response;
      }});
      return cached || network;
    }})
  );
}});
"""
    (DOCS_DIR / "sw.js").write_text(sw_content, encoding="utf-8")
    print("PWA-Assets generiert (manifest, sw.js, icons).")


def generate_mathjax_config() -> None:
    """Erstellt docs/javascripts/mathjax.js für MathJax-Konfiguration."""
    js_dir = DOCS_DIR / "javascripts"
    js_dir.mkdir(parents=True, exist_ok=True)
    (js_dir / "mathjax.js").write_text(
        'window.MathJax = {\n'
        '  tex: {\n'
        '    inlineMath: [["$", "$"], ["\\\\(", "\\\\)"]],\n'
        '    displayMath: [["$$", "$$"], ["\\\\[", "\\\\]"]],\n'
        '  },\n'
        '};\n',
        encoding='utf-8',
    )


def main():
    # docs/ komplett neu aufbauen
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir()

    # Startseite mit Modultabelle
    module_table = build_module_table(SKRIPTE_DIR)
    index_content = (
        "# Mathematikstudium\n\n"
        "Willkommen zu den Zusammenfassungen und Einsendeaufgaben.\n\n"
        "## Module\n\n"
        + module_table
    )
    (DOCS_DIR / "index.md").write_text(index_content, encoding="utf-8")

    # MathJax-Konfiguration erzeugen
    generate_mathjax_config()

    # site_url für PDF.js-Viewer-Links aus mkdocs.yml lesen
    with open(MKDOCS_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    site_url = config.get("site_url", "").rstrip("/") + "/"

    # Docs-Baum aufbauen
    print("Generiere Docs aus skripte/ ...")
    nav_skripte = build_tree(SKRIPTE_DIR, DOCS_DIR, site_url)

    nav = [{"Home": "index.md"}] + nav_skripte

    # mkdocs.yml nav-Abschnitt aktualisieren
    with open(MKDOCS_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config["nav"] = nav

    with open(MKDOCS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # PWA-Assets generieren
    generate_pwa_assets(site_url)

    page_count = sum(1 for _ in DOCS_DIR.rglob("*.md"))
    print(f"Fertig: {page_count} Seiten generiert.")


if __name__ == "__main__":
    main()
