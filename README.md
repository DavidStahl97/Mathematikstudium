# Mathematikstudium

Zusammenfassungen und Einsendeaufgaben zum Fernstudium Mathematik, geschrieben in LaTeX.

## GitHub Pages

Die fertige Dokumentationsseite wird automatisch bei jedem Push auf `main` generiert und deployed:

**https://davidstahl97.github.io/Mathematikstudium/**

## Struktur

```
skripte/
└── <modul>/
    └── <lektion>/
        └── <aufgabentyp>/
            └── <aufgabe>.tex
```

Beispiel:
```
skripte/
└── 61111-mathematische-grundlagen/
    └── lektion-1/
        └── Einsendeaufgabe/
            └── aufgabe-1_1.tex
```

## Wie es funktioniert

1. **LaTeX-Quellen** liegen in `skripte/` und werden per `pdflatex` zu PDFs kompiliert
2. **`generate_docs.py`** traversiert `skripte/` rekursiv und baut daraus die MkDocs-Dokumentation:
   - Ordnerstruktur → Navigationsmenü
   - Jede `.tex`-Datei → Seite mit eingebetteter PDF und Download-Button
3. **GitHub Actions** führt alles automatisch aus und deployed auf GitHub Pages

Die `docs/`-Ordner wird **nicht im Repository gespeichert** – er wird vollständig in der GitHub Action generiert.

## Lokal ausführen

```bash
# Abhängigkeiten installieren
pip install mkdocs-material pyyaml

# .tex-Dateien kompilieren (TeX Live benötigt)
find skripte -name "*.tex" | while read f; do
  (cd "$(dirname "$f")" && pdflatex "$(basename "$f")" && pdflatex "$(basename "$f")")
done

# Docs generieren
python generate_docs.py

# Lokaler Dev-Server
mkdocs serve
```

## Neue Inhalte hinzufügen

Einfach eine neue `.tex`-Datei in der passenden Ordnerstruktur anlegen:

```
skripte/<modul>/<lektion>/<typ>/aufgabe-X_Y.tex
```

Beim nächsten Push auf `main` wird die Seite automatisch aktualisiert.
