# CLAUDE.md – Hinweise für Claude

## Repository
Mathe-Zusammenfassungen als LaTeX-Skripte, kompiliert zu PDF via GitHub Actions.

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
- Workflow: `.github/workflows/latex-compile.yml`
- Kompilierung via `apt-get install texlive-*` + `pdflatex` (zweimal für ToC)
- `permissions: contents: write` ist nötig für den Release-Upload-Schritt
- **Nicht** `xu-cheng/latex-action@v3` verwenden – Docker-basiert, fehleranfällig

## Typischer Fix-Workflow
1. Action-Runs via API prüfen (`actions/runs` → `jobs`)
2. Fehlerhafte Steps identifizieren
3. Fix auf neuem Branch committen und pushen
4. PR via GitHub API erstellen (Token beim Benutzer anfragen falls nötig)
