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
Die lokale Gitea-Proxy-API unterstützt keine PR-Erstellung. PRs müssen manuell auf GitHub erstellt werden:
- URL: `https://github.com/DavidStahl97/Mathematikstudium/compare/main...<branch>`

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
4. Benutzer bittet, PR zu mergen (oder Link zum PR-Erstellen schicken)
