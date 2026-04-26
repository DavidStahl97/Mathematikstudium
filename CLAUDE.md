# CLAUDE.md – Hinweise für Claude

## Repository
Mathe-Zusammenfassungen als LaTeX-Skripte, kompiliert zu PDF via GitHub Actions.

## Pfade
Der Ordner `Mathematikstudium` ist als Workspace freigegeben – immer **relative Pfade** verwenden, nie absolute (kein `D:\source\repos\Mathematikstudium\...`).
Das aktuelle Arbeitsverzeichnis ist bereits `D:\source\repos\Mathematikstudium` – kein `cd` in dieses Verzeichnis nötig.

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
**Keinen PR automatisch erstellen** – keinen GitHub-Token anfragen und keine API-Calls zum Erstellen von PRs machen.

Nach dem Push einfach den Compare-Link im Chat posten, damit der Benutzer selbst einen PR erstellen kann:

```
https://github.com/DavidStahl97/Mathematikstudium/compare/main...<branch>
```

## LaTeX / GitHub Action
- TeX-Dateien liegen in `skripte/`
- Workflow: `.github/workflows/docs.yml`
- Kompilierung via `apt-get install texlive-*` + `pdflatex` (zweimal für ToC)
- `permissions: contents: write` ist nötig für den gh-deploy-Schritt
- **Nicht** `xu-cheng/latex-action@v3` verwenden – Docker-basiert, fehleranfällig

## Lokale Kompilierung mit pdflatex

TeX Live ist lokal installiert. pdflatex ist erreichbar unter:
```
/c/texlive/2026/bin/windows/pdflatex.exe
```

Nach dem Schreiben oder Ändern einer `.tex`-Datei **immer kompilieren und das erzeugte PDF prüfen**:

```bash
PDFLATEX=/c/texlive/2026/bin/windows/pdflatex.exe

"$PDFLATEX" -interaction=nonstopmode -output-directory=<verzeichnis> <datei>.tex
```

Dabei prüfen:
- Kompilierung fehlerfrei (Exit-Code 0, keine Fehler im Log)
- PDF mit dem Read-Tool öffnen und auf korrekte Formatierung prüfen (Abstände, Formeln, Einrückungen, Seitenumbrüche)

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

## Umgang mit LaTeX-Lösungen (Einsendeaufgaben)
- **Nur transkribieren** – ausschließlich das in LaTeX übertragen, was im handschriftlichen PDF steht. Keinen eigenen Erklärungstext, Zwischenschritte oder Formulierungen erfinden oder ergänzen.
- **Nicht selbst korrigieren** – wenn etwas fehlerhaft oder unleserlich erscheint, beim Benutzer nachfragen
- **Kein eigener Text** – kein „Aus den Gleichungen folgt:", kein „Damit ist die Lösungsmenge:", keine selbst formulierten Sätze – nur was im PDF steht
- Der Benutzer muss die Lösungen selbst erarbeiten; Claude dient nur zur Transkription

## Attachments-Workflow

Der Ordner `Attachments/` dient als Ablageort für Dateien, die der Benutzer hochlädt und von Claude verarbeitet werden sollen.

### Ablauf
1. Benutzer legt eine Datei in `Attachments/` ab (z.B. `Attachments/icon.png`, `Attachments/loesung.pdf`)
2. Claude liest/verarbeitet die Datei (z.B. Bild als Icon einbinden, PDF transkribieren)
3. Claude löscht die Datei danach mit `rm Attachments/<dateiname>`

### Hinweise
- Der Ordner selbst ist im Repo (via `.gitkeep`), die Inhalte stehen in `.gitignore`
- Hochgeladene Dateien werden also **nicht** in Git getrackt und nicht gepusht
- Nach der Verarbeitung immer löschen, damit der Ordner sauber bleibt
- Unterstützte Dateitypen: PNG, JPG, PDF – alles was Claude lesen kann

## Typischer Fix-Workflow
1. Action-Runs via API prüfen (`actions/runs` → `jobs`)
2. Fehlerhafte Steps identifizieren
3. Fix auf neuem Branch committen und pushen
4. PR via GitHub API erstellen (Token beim Benutzer anfragen falls nötig)

## Formatvorlagen

Fertige LaTeX-Startdateien liegen in `vorlagen/`:

| Datei | Verwendung |
|---|---|
| `vorlagen/einsendeaufgabe.tex` | Neue Einsendeaufgabe anlegen |
| `vorlagen/ziele.tex` | Neue Ziele-Datei für eine Lektion |
| `vorlagen/glossar.tex` | Neues Glossar für eine Lektion |

Beim Erstellen einer neuen `.tex`-Datei die passende Vorlage kopieren und die Platzhalter (`N`, `M`, `MODULNAME`, `NUMMER`, `TITEL` usw.) ersetzen.





# Format-Referenz: Einsendeaufgaben, Ziele & Glossar
## Mathematikstudium – Modul 61111 (und weitere)

Orientierung an der **FernUni Analysis-Leseprobe (Modul 61211)**.
Dokumente liegen in der Ordnerstruktur:
```
skripte/<modul>/lektion-<n>/Einsendeaufgabe/aufgabe-N_M.tex
skripte/<modul>/lektion-<n>/Ziele/ziele.tex
skripte/<modul>/lektion-<n>/Glossar/glossar.tex
```

---

## 0. Einsendeaufgaben (`aufgabe-N_M.tex`)

### Zweck
Transkription der handschriftlichen Lösung des Studierenden in LaTeX. Nur was im
Handschrift-PDF steht – kein eigener Text, keine Korrekturen, keine Ergänzungen.

### Dokumentklasse & Pakete
```latex
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[ngerman]{babel}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{enumitem}
\usepackage{geometry}
\geometry{a4paper, margin=2.5cm}
% Für Beweise mit \qed:
% \usepackage{amsthm}
```

### Titel
```latex
\title{Einsendeaufgaben -- Aufgabe N.M\\[0.5em]
\large MODUL-NUMMER MODULNAME}
\author{}
\date{}
```

### Aufbau
```latex
\section*{Aufgabe 1}
\begin{enumerate}[label=\alph*)]
  \item ...
  \item ...
\end{enumerate}
```

- Abschnitt heißt immer `\section*{Aufgabe 1}` (ohne Modulpräfix)
- Teile mit `\begin{enumerate}[label=\alph*)]`
- Beweise: `\textbf{Induktionsanfang}`, `\textbf{Induktionsschritt}`, `align*` für mehrzeilige Gleichungen, `\qed` am Ende
- Fallunterscheidungen: `\textit{Fall 1:}`, `\textit{Fall 2:}` usw.
- Fließtext mit Formeln: `$...$` inline, `\[...\]` für abgesetzte Formeln
- Hinweise auf Sätze aus dem Lehrtext direkt übernehmen (z.B. „Satz 2.3.8(iv)")

---

## 1. Ziele (`ziele.tex`)

### Zweck
Studierhinweise für eine Lektion. Gibt dem Studierenden vor dem Lesen des
Lehrtexts einen Überblick: Was kommt? In welcher Reihenfolge? Was soll ich
am Ende können? Wie kann ich mich selbst kontrollieren?

### Dokumentklasse & Pakete
```latex
\documentclass[a4paper,12pt]{article}
% Pflicht-Pakete:
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[ngerman]{babel}
\usepackage{amsmath, amssymb}
\usepackage{tikz}
\usetikzlibrary{shapes.geometric, arrows.meta, positioning, fit, backgrounds}
\usepackage{geometry}   % left=3cm, right=3cm, top=2.5cm, bottom=2.5cm
\usepackage{enumitem}
\usepackage{parskip}
```

### Aufbau (in dieser Reihenfolge)

#### A) Titel
```latex
\begin{center}
  {\LARGE\bfseries Studierhinweise zu Lektion N}\\[0.5em]
  {\large <Modulname> (Modul <Nummer>)}
\end{center}
```

#### B) Einleitungstext (1–3 Absätze)
- Beschreibt kurz, worum es in der Lektion geht
- Gibt einen Hinweis zur Arbeitsweise (z.B. "aktiv mit Papier und Bleistift")
- Erklärt, wie die Kapitel aufeinander aufbauen
- **Kein LaTeX-Boilerplate, echter inhaltlicher Text aus dem Lehrtext**

#### C) Kursstruktur-Diagramm (TikZ)
Titel: `\section*{Struktur der Lektion N}`

Ein **TikZ-Flowchart** über alle Kapitel der Lektion:
- Je Kapitel eine Spaltengruppe von Boxen (eine Box pro Abschnitt)
- Pfeile zeigen die Lernreihenfolge innerhalb eines Kapitels (vertikal)
- Pfeile zwischen Kapiteln zeigen Abhängigkeiten (horizontal)
- Box-Inhalt: Abschnittsnummer + Stichworte der Kerninhalte

```latex
\tikzset{
  box/.style={rectangle, draw, rounded corners=3pt, text width=4.5cm,
              align=center, minimum height=1.0cm, font=\small, inner sep=4pt},
  arrow/.style={-{Latex[length=2mm]}, thick},
}
```

Beispielstruktur für Lektion mit 3 Kapiteln:
```
[Kap 1: Abschn 1.1] --> [Kap 1: Abschn 1.2] --> ... --> [Kap 2: ...] --> [Kap 3: ...]
```

#### D) Zielelemente (eines pro Abschnitt)

Für **jeden Abschnitt** (1.1, 1.2, ..., Kap 2, Kap 3 usw.) eine eigene Seite
(`\newpage`) mit folgendem festen Aufbau:

```
\section*{Zielelement X.Y -- <Titel des Abschnitts>}

\subsection*{Lerninhalte}
[TikZ-Flowchart]

\subsection*{Lernziele}
[itemize-Liste]

\subsection*{Selbstkontrollelement X.Y}
[Eine kurze Aufgabe]
```

**Lerninhalte-Flowchart:**
- TikZ-Diagramm, das die Begriffsbildungen des Abschnitts zeigt
- Boxen = Begriffe/Konzepte, Pfeile = logische Abhängigkeit
- Zeigt, wie Begriffe aufeinander aufbauen (nicht die Beweise, nur die Struktur)
- Orientierung: Welche Definitionen brauche ich für welchen Begriff?

Beispiel Abschnitt "Abbildungen":
```
[Abbildung f: M→N] --> [Bild f(m)] --> [injektiv/surjektiv/bijektiv]
                    --> [Komposition g∘f] --> [Invertierbarkeit ↔ bijektiv]
```

**Lernziele:**
- 3–6 Punkte, beginnend mit "Nach Durcharbeiten dieses Abschnitts sollten Sie:"
- Konkret und überprüfbar: "...können", "...kennen", "...verstehen und anwenden"
- Direkt aus den Studierhinweisen im Lehrtext ableiten

**Selbstkontrollelement:**
- Eine einzige, kurze, selbst beantwortbare Aufgabe
- Kein Beweis nötig, eher: Berechnen, Nachprüfen, Beispiel angeben
- Testet ob der Kernbegriff des Abschnitts verstanden wurde

---

## 2. Glossar (`glossar.tex`)

### Zweck
Kompakte Nachschlageliste aller Definitionen, Merkregeln, Sätze und
Propositionen der Lektion. Dient zur schnellen Wiederholung, **kein Ersatz**
für den Lehrtext. Keine Beweise, keine Erklärungen – nur die Kernaussagen.

### Dokumentklasse & Pakete
```latex
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[ngerman]{babel}
\usepackage{amsmath, amssymb}
\usepackage{geometry}   % left=3cm, right=3cm, top=2.5cm, bottom=2.5cm
\usepackage{array, booktabs}
\usepackage{enumitem}
\usepackage{parskip}
```

### Hilfsbefehl für Einträge
```latex
\newcommand{\gentry}[3]{%
  \noindent\textbf{#1\quad #2}\nopagebreak\\[0.2em]
  #3\par\smallskip
}
% Aufruf: \gentry{Nummer}{Fetter Titel}{Inhalt}
% Beispiel: \gentry{1.2.4}{Konjunktion $A \land B$}{Genau dann wahr, wenn ...}
% Für Einträge ohne eigene Nummer: \gentry{}{Vollständige Induktion}{...}
```

### Aufbau

#### Titel
```latex
\begin{center}
  {\LARGE\bfseries Glossar zu Lektion N}\\[0.5em]
  {\large <Modulname> (Modul <Nummer>)}
\end{center}
```
Kurzer Einleitungssatz: "Dieses Glossar fasst die wesentlichen Definitionen..."

#### Abschnitte
Gegliedert nach den **Abschnittsnummern aus dem Lehrtext**:
```latex
\section*{1.1 \quad <Titel des Abschnitts>}
\section*{1.2 \quad <Titel des Abschnitts>}
...
```

#### Einträge pro Abschnitt
Alle Definitionen, Merkregeln, Sätze, Propositionen, Korollare – in der
Reihenfolge, wie sie im Lehrtext erscheinen.

**Was kommt rein:**
- Jede `Definition` aus dem Lehrtext
- Jede `Merkregel`
- Wichtige `Proposition`, `Satz`, `Korollar` (Aussage, nicht Beweis)
- `Notation`-Abschnitte wenn relevant

**Was kommt NICHT rein:**
- Beweise
- Beispiele (außer wenn sie direkt Teil der Definition sind, wie F₂)
- Aufgaben / Übungen

**Format pro Eintrag:**
```
Nummer   Fetter Titel
Inhalt (Definition/Formel/Wahrheitstafel) in 2–5 Zeilen
```

**Wahrheitstafeln** als `array`-Umgebung:
```latex
\[
  \begin{array}{cc|c}
    A & B & A \land B \\\hline
    w & w & w \\ w & f & f \\ f & w & f \\ f & f & f
  \end{array}
\]
```

**Aufzählungen innerhalb eines Eintrags** (z.B. mehrere Eigenschaften):
```latex
\begin{itemize}[topsep=2pt,itemsep=1pt]
  \item ...
\end{itemize}
```

---

## 3. Workflow beim Erstellen

1. **Lehrtext-PDF lesen** (komplett, alle Kapitel der Lektion)
2. **Gliederung erfassen**: Welche Kapitel/Abschnitte gibt es? Wie hängen sie zusammen?
3. **Glossar zuerst**: Alle Definitionen/Sätze durchgehen und kompakt erfassen → gibt Überblick
4. **Ziele danach**: Kursstruktur-Diagramm aus der Gliederung ableiten, dann pro Abschnitt Flowchart + Lernziele aus den Studierhinweisen im Lehrtext

### Aus dem Lehrtext ableiten
- **Lernziele** stehen oft direkt in den Studierhinweisen des Lehrtexts ("Nach Durcharbeiten von Abschnitt X.Y sollten Sie...")
- **Flowchart-Struktur** ergibt sich aus der Reihenfolge der Definitionen: Was wird zuerst definiert, was baut darauf auf?
- **Kursstruktur-Diagramm**: Welche Kapitel/Abschnitte bauen auf welchen auf? (Pfeile zwischen Kapiteln nur wenn explizit nötig)

---

## 4. Beispiel-Mapping (Lektion 1, Modul 61111)

| Abschnitt | Zielelement-Titel | Kern-Begriffe im Flowchart |
|---|---|---|
| 1.1 | Das Summensymbol Σ | Σ-Notation → Doppelsummen → Merkregel Vertauschen |
| 1.2 | Aussagen, Junktoren und Quantoren | Aussage → Junktoren (¬∧∨⇒⇔) → Wahrheitstafeln → Quantoren → Negation → Induktion → Beweisprinzipien |
| 1.3 | Mengen | Menge/Element → Teilmenge/Gleichheit → ∪∩\ → Mächtigkeit → Produktmenge |
| 1.4 | Abbildungen | Abbildung → Bild/Urbild → inj/surj/bij → id_M → Komposition → Invertierbarkeit |
| 1.5 | Verknüpfungen | Verknüpfung → kommutativ/assoziativ/neutr.El. → Invertierbarkeit → Distributivgesetze → F₂ |
| 1.6 | Körper | Körper K → Axiome → Beispiele (Q,R,C,F₂) → Rechenregeln → Notation |
| Kap. 2 | Matrizen | Matrix → Addition/Skalarmultiplikation → Multiplikation → Einheitsmatrix → Invertierbarkeit |
| Kap. 3 | Elementarmatrizen | Elementare Zeilenumformungen → Elementarmatrizen → Invertierbarkeit der EM → Zeilenäquivalenz |
