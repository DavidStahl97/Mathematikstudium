#!/usr/bin/env python3
"""
Generiert MkDocs-Dokumentation aus der skripte/-Ordnerstruktur.

- Traversiert skripte/ rekursiv
- Baut Navigationsstruktur aus Ordnerhierarchie
- Für jede .tex-Datei (Leaf): erstellt .md-Seite mit eingebetteter PDF
- Kopiert PDFs nach docs/assets/pdfs/
- Aktualisiert den nav-Abschnitt in mkdocs.yml
"""

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


def main():
    # docs/ komplett neu aufbauen
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir()

    # Startseite
    (DOCS_DIR / "index.md").write_text(
        "# Mathematikstudium\n\n"
        "Willkommen zu den Zusammenfassungen und Einsendeaufgaben.\n\n"
        "Navigiere über das Menü zu den einzelnen Skripten.\n",
        encoding="utf-8",
    )

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

    page_count = sum(1 for _ in DOCS_DIR.rglob("*.md"))
    print(f"Fertig: {page_count} Seiten generiert.")


if __name__ == "__main__":
    main()
