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

Einmalig Abhängigkeiten installieren (TeX Live separat):

```bash
pip install mkdocs-material pyyaml
```

Danach reicht ein einziger Befehl:

```bash
python build.py            # kompiliert nur geänderte .tex → .pdf und generiert docs/
python build.py --serve    # zusätzlich: startet mkdocs serve danach
python build.py --force    # alle .tex neu kompilieren
python build.py --skip-tex # nur docs/ regenerieren, ohne LaTeX-Lauf
python build.py --skip-docs # nur LaTeX kompilieren, ohne docs/-Generierung
```

Pfad zu `pdflatex` ggf. per Umgebungsvariable `PDFLATEX` setzen (Default unter Windows:
`/c/texlive/2026/bin/windows/pdflatex.exe`).

## Cache-Logik

`build.py` kompiliert nur geänderte `.tex`-Dateien neu – sowohl lokal als auch in CI. Die Erkennung erfolgt **content-hash-basiert** über sogenannte Sidecar-Dateien:

- Neben jeder erfolgreich kompilierten `<file>.pdf` wird `<file>.tex.hash` angelegt – eine Textdatei mit dem SHA-256 der zugehörigen `.tex`.
- Beim nächsten Build vergleicht `build.py` den aktuellen Hash der `.tex` mit dem gespeicherten. Stimmen sie überein und die PDF existiert noch, wird die Kompilierung übersprungen.
- Eine `.tex` gilt nur dann als "veraltet", wenn ihr Inhalt sich tatsächlich geändert hat – `touch` oder Branch-Wechsel allein lösen keinen Rebuild aus.

Sidecars sind reine Build-Artefakte und werden via [.gitignore](.gitignore) (`skripte/**/*.tex.hash`) nicht ins Repo committed.

### Warum content-hash statt mtime?

Modifikationszeiten (`mtime`) sind nach `git checkout` oder in einem frischen Worktree unzuverlässig: alle Dateien bekommen denselben Zeitstempel. Inhaltshashes überleben Checkouts unverändert und funktionieren damit auch in der GitHub-Action.

### Lernkarten-Cache

Lernkarten-SVGs (siehe `generate_docs.py`) nutzen denselben Content-Hash-Ansatz: gerenderte SVGs liegen unter `.lernkarten-cache/<hash>-{front,back}.svg`. Lernkarten-Generierung ist standardmäßig deaktiviert (`GENERATE_LERNKARTEN=0`) – in CI wird sie über die Environment-Variable im Workflow aktiviert.

### CI-Caching

`.github/workflows/docs.yml` persistiert die Cache-Artefakte zwischen Workflow-Runs via [`actions/cache@v4`](https://github.com/actions/cache):

```yaml
path: |
  skripte/**/*.pdf
  skripte/**/*.tex.hash
  .lernkarten-cache
```

Damit kompiliert die CI nach einer einzelnen `.tex`-Änderung nur diese eine Datei neu; alle anderen PDFs und Lernkarten-SVGs werden aus dem Cache restauriert.

## Neue Inhalte hinzufügen

Einfach eine neue `.tex`-Datei in der passenden Ordnerstruktur anlegen:

```
skripte/<modul>/<lektion>/<typ>/aufgabe-X_Y.tex
```

Beim nächsten Push auf `main` wird die Seite automatisch aktualisiert.
