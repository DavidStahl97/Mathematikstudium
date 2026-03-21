# CLAUDE.md – Hinweise für Claude

## Repository
Mathe-Zusammenfassungen als LaTeX-Skripte, kompiliert zu PDF via GitHub Actions.

## Pfade
Der Ordner `Mathematikstudium` ist als Workspace freigegeben – immer **relative Pfade** verwenden, nie absolute (kein `D:\source\repos\Mathematikstudium\...`).

## Git & Push
- Branch-Schema: `claude/<beschreibung>-<sessionId>`
- Push mit: `git push -u origin <branch-name>`
- Direkt auf `main` pushen ist **nicht erlaubt** – immer PR erstellen

## GitHub Actions API
Actions-Runs können ohne Authentifizierung über die öffentliche GitHub API abgerufen werden:

```bash
# Letzte Runs auflisten
curl -s "https://api.github.com/repos/DavidStahl97/Mathematikstudium/actions/runs?per_page=5" \
  -H "Accept: application/vnd.github.v3+json"

# Steps eines Runs anzeigen
curl -s "https://api.github.com/repos/DavidStahl97/Mathematikstudium/actions/runs/<RUN_ID>/jobs" \
  -H "Accept: application/vnd.github.v3+json"
```

Logs selbst (Volltext) benötigen Admin-Rechte (403). Step-Status reicht aber meist zur Diagnose.

## PRs erstellen
PRs können über die GitHub API erstellt werden. Den Token beim Benutzer anfragen (`GITHUB_TOKEN`):

```bash
curl -s -X POST "https://api.github.com/repos/DavidStahl97/Mathematikstudium/pulls" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "PR-Titel",
    "body": "Beschreibung",
    "head": "<branch>",
    "base": "main"
  }' | python3 -c "import sys,json; pr=json.load(sys.stdin); print(pr['html_url'])"
```

Falls kein Token vorhanden: `https://github.com/DavidStahl97/Mathematikstudium/compare/main...<branch>`

## LaTeX / GitHub Action
- TeX-Dateien liegen in `skripte/`
- Workflow: `.github/workflows/docs.yml`
- Kompilierung via `apt-get install texlive-*` + `pdflatex` (zweimal für ToC)
- `permissions: contents: write` ist nötig für den gh-deploy-Schritt
- **Nicht** `xu-cheng/latex-action@v3` verwenden – Docker-basiert, fehleranfällig

## Docs-Generierung (GitHub Pages)

### Konzept
- `docs/` wird **nicht im Repo gespeichert** – steht in `.gitignore`
- `generate_docs.py` erzeugt `docs/` vollständig aus der `skripte/`-Ordnerstruktur
- Der Workflow kompiliert LaTeX → generiert Docs → deployed via `mkdocs gh-deploy`
- Die GitHub Page liegt auf dem `gh-pages`-Branch (automatisch von mkdocs verwaltet)

### Ordnerstruktur in `skripte/`
```
skripte/
└── <modul>/               # z.B. 61111-mathematische-grundlagen
    └── <lektion>/         # z.B. lektion-1
        └── <aufgabentyp>/ # z.B. Einsendeaufgabe
            └── <aufgabe>.tex  # z.B. aufgabe-1_1.tex
```
- Ordnernamen werden zu Nav-Titeln: `lektion-1` → `Lektion 1`, `_` → `.` bei Dateinamen
- `.tex`-Dateien sind die Blätter (Leafs) des Navigationsbaums
- Jede `.tex`-Datei erzeugt eine Seite mit eingebetteter PDF + Download-Button

### `generate_docs.py`
- Löscht `docs/` und baut es komplett neu auf
- Kopiert PDFs nach `docs/assets/pdfs/<relativer-pfad>/`
- Erstellt `.md`-Seiten mit `<embed>`-Tag für die PDF
- Aktualisiert den `nav:`-Abschnitt in `mkdocs.yml` automatisch
- Lokal ausführbar (PDFs müssen vorher in `skripte/` liegen): `python generate_docs.py`

### Workflow-Ablauf (`.github/workflows/docs.yml`)
- Trigger: bei jedem PR und bei Push auf `main`/`master`
1. TeX Live installieren
2. Alle `.tex` → `.pdf` kompilieren (`pdflatex` zweimal)
3. `pip install mkdocs-material pyyaml`
4. `python generate_docs.py`
5. `mkdocs build` → HTML-Site als Artefakt (`docs-site`) hochladen
6. `mkdocs gh-deploy --force` (**nur bei main/master**)

### mkdocs.yml
- Kein `nav:`-Abschnitt im Repo – wird von `generate_docs.py` zur Laufzeit eingefügt
- Theme: Material, Sprache: de, Features: navigation.tabs, navigation.sections

## Typischer Fix-Workflow
1. Action-Runs via API prüfen (`actions/runs` → `jobs`)
2. Fehlerhafte Steps identifizieren
3. Fix auf neuem Branch committen und pushen
4. PR via GitHub API erstellen (Token beim Benutzer anfragen falls nötig)
