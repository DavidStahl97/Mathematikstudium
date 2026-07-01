#!/usr/bin/env python3
"""
Baut ein Anki-Deck (.apkg) aus den bereits gerenderten Lernkarten-SVGs.

Voraussetzung: `generate_docs.py` wurde mit GENERATE_LERNKARTEN=1 ausgefuehrt,
so dass die SVGs unter .lernkarten-cache/<hash>-{front,back}.svg liegen.

Karten-GUIDs werden deterministisch aus
    <lernkarten-relpath> + <front-LaTeX>
abgeleitet. Wiederimport in Anki erkennt Karten an der GUID, sodass der
Lernfortschritt bei Aenderungen der Rueckseite erhalten bleibt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import genanki

from generate_docs import (
    DOCS_DIR,
    LERNKARTEN_CACHE_DIR,
    SKRIPTE_DIR,
    _collect_lernkarten_jobs,
    _card_hash,
    folder_to_title,
)


# Stabile, einmal gewuerfelte IDs. NICHT veraendern, sonst gilt das gesamte
# Deck/Model nach dem naechsten Import als neu.
DECK_ROOT_NAME = "Mathematikstudium"
MODEL_ID = 1716453821
TOP_DECK_ID = 1716453822


_MODEL = genanki.Model(
    MODEL_ID,
    "Mathematikstudium Lernkarte (SVG)",
    fields=[{"name": "Front"}, {"name": "Back"}],
    templates=[{
        "name": "Karte",
        "qfmt": "{{Front}}",
        "afmt": "{{Front}}<hr id=\"answer\">{{Back}}",
    }],
    css=(
        ".card{font-family:sans-serif;text-align:center;background:#fff;}"
        ".card img{max-width:100%;height:auto;"
        "background:#fff;padding:12px;border-radius:4px;}"
    ),
)


def _module_and_lesson(source_tex: Path) -> tuple[str, str, str]:
    """Liefert (Modul-Slug, Modul-Titel, Lektions-Titel) aus dem Kartenquellen-Pfad.

    Erwartete Struktur: skripte/<modul>/<lektion>/lernkarten.tex
    """
    rel = source_tex.resolve().relative_to(SKRIPTE_DIR.resolve())
    parts = rel.parts
    # parts: (<modul>, <lektion>, "lernkarten.tex")
    modul_slug = parts[0] if len(parts) >= 1 else "unbekannt"
    modul = folder_to_title(modul_slug)
    lektion = folder_to_title(parts[1]) if len(parts) >= 2 else "Unbekannt"
    return modul_slug, modul, lektion


def _card_guid(source_tex: Path, card: dict) -> str:
    """Stabile, eindeutige GUID einer Karte.

    Bevorzugt die explizite, inhaltsunabhaengige Karten-id (\\lernkarte[id]{..}).
    Damit bleibt der Anki-Lernfortschritt erhalten, auch wenn sich Titel oder
    Rueckseite spaeter aendern. Die id muss global eindeutig sein.

    Fallback (Karte ohne id): (Datei-Pfad, Abschnitt, Titel) -- eindeutig, aber
    nicht stabil gegen Titelaenderungen.
    """
    cid = card.get('id')
    if cid:
        return genanki.guid_for("lernkarte", cid)
    rel = source_tex.resolve().relative_to(SKRIPTE_DIR.resolve())
    key = f"{card.get('section', '')}||{card.get('title', card.get('front', ''))}"
    return genanki.guid_for(str(rel).replace("\\", "/"), key)


def _deck_id_for(name: str) -> int:
    """Deterministische, stabile Deck-ID aus dem Deck-Namen.

    Anki erlaubt 1 <= deck_id < 2**63. Wir erzeugen einen Hash-basierten Wert.
    """
    import hashlib
    h = hashlib.sha1(name.encode("utf-8")).digest()
    # 8 Byte → 63-Bit-Integer
    val = int.from_bytes(h[:8], "big") & ((1 << 63) - 1)
    return val or 1


def build_anki_packages(out_dir: Path) -> list[dict] | None:
    """Baut pro Modul eine eigene .apkg-Datei.

    Returns:
        Liste mit Metadaten je gebautem Modul-Deck
        ({"modul_slug", "modul_title", "apkg": Path, "lessons", "notes"}),
        oder None bei Fehler. Leere Liste, wenn keine Karten vorhanden sind.
    """
    print("Sammle Lernkarten fuer Anki-Export ...")
    jobs = _collect_lernkarten_jobs(SKRIPTE_DIR, DOCS_DIR)
    if not jobs:
        print("  Keine Lernkarten gefunden — ueberspringe Anki-Build.")
        return []

    for job in jobs:
        for c in job["cards"]:
            c["_hash"] = _card_hash(c)

    # Jobs nach Modul gruppieren
    by_module: dict[str, list[dict]] = {}
    module_titles: dict[str, str] = {}
    for job in jobs:
        modul_slug, modul_title, _ = _module_and_lesson(job["source_tex"])
        by_module.setdefault(modul_slug, []).append(job)
        module_titles[modul_slug] = modul_title

    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    missing_svgs: list[Path] = []

    for modul_slug in sorted(by_module):
        modul_title = module_titles[modul_slug]
        module_jobs = by_module[modul_slug]

        decks_by_name: dict[str, genanki.Deck] = {}
        media_files: set[Path] = set()
        notes_count = 0

        # Container-Deck pro Modul
        root_name = f"{DECK_ROOT_NAME}::{modul_title}"
        decks_by_name[root_name] = genanki.Deck(_deck_id_for(root_name), root_name)

        for job in module_jobs:
            source_tex: Path = job["source_tex"]
            _, _, lektion = _module_and_lesson(source_tex)
            deck_name = f"{root_name}::{lektion}"

            if deck_name not in decks_by_name:
                decks_by_name[deck_name] = genanki.Deck(
                    _deck_id_for(deck_name), deck_name
                )
            deck = decks_by_name[deck_name]

            for c in job["cards"]:
                h = c["_hash"]
                front_svg = LERNKARTEN_CACHE_DIR / f"{h}-front.svg"
                back_svg = LERNKARTEN_CACHE_DIR / f"{h}-back.svg"
                if not front_svg.exists() or not back_svg.exists():
                    missing_svgs.append(
                        front_svg if not front_svg.exists() else back_svg
                    )
                    continue
                media_files.add(front_svg)
                media_files.add(back_svg)

                note = genanki.Note(
                    model=_MODEL,
                    fields=[
                        f'<img src="{front_svg.name}">',
                        f'<img src="{back_svg.name}">',
                    ],
                    guid=_card_guid(source_tex, c),
                )
                deck.add_note(note)
                notes_count += 1

        apkg_path = out_dir / f"{modul_slug}.apkg"
        package = genanki.Package(list(decks_by_name.values()))
        package.media_files = [str(p) for p in sorted(media_files)]
        package.write_to_file(str(apkg_path))

        lessons = len(decks_by_name) - 1  # ohne Container-Deck
        print(f"Anki-Deck erstellt: {apkg_path} "
              f"({lessons} Lektions-Decks, {notes_count} Karten)")
        results.append({
            "modul_slug": modul_slug,
            "modul_title": modul_title,
            "apkg": apkg_path,
            "lessons": lessons,
            "notes": notes_count,
        })

    if missing_svgs:
        print(f"  [WARN] {len(missing_svgs)} SVG(s) fehlen — bitte zuerst "
              "generate_docs.py mit GENERATE_LERNKARTEN=1 ausfuehren.",
              file=sys.stderr)
        return None

    return results


def main() -> int:
    out_dir = DOCS_DIR / "assets" / "anki"
    result = build_anki_packages(out_dir)
    return 0 if result is not None else 1


if __name__ == "__main__":
    sys.exit(main())
