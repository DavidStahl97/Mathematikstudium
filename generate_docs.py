#!/usr/bin/env python3
"""
Generiert MkDocs-Dokumentation aus der skripte/-Ordnerstruktur.

- Traversiert skripte/ rekursiv
- Baut Navigationsstruktur aus Ordnerhierarchie
- Für jede .tex-Datei (Leaf): erstellt .md-Seite mit eingebetteter PDF
- Kopiert PDFs nach docs/assets/pdfs/
- Aktualisiert den nav-Abschnitt in mkdocs.yml
"""

import json
import os
import shutil
import urllib.parse
import yaml
from pathlib import Path

SKRIPTE_DIR = Path("skripte")
DOCS_DIR = Path("docs")
MKDOCS_FILE = Path("mkdocs.yml")


def folder_to_title(name: str) -> str:
    """Ordnername zu lesbarem Titel: 'lektion-1' → 'Lektion 1'"""
    return name.replace("-", " ").title()


def tex_to_title(stem: str) -> str:
    """Dateiname zu Titel: 'aufgabe-1_1' → 'Aufgabe 1.1'"""
    return stem.replace("_", ".").replace("-", " ").title()


def build_tree(skripte_path: Path, docs_path: Path, site_url: str) -> list:
    """
    Rekursiv Ordner traversieren, .md-Dateien erzeugen, Nav-Liste zurückgeben.
    skripte_path: aktueller Pfad in skripte/
    docs_path:    korrespondierender Pfad in docs/
    site_url:     absolute Basis-URL der GitHub Pages Site (mit trailing slash)
    """
    items = []

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
