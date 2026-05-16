#!/usr/bin/env python3
"""
Lokaler One-Shot-Build: kompiliert alle .tex-Dateien in skripte/ zu PDFs
und ruft anschließend generate_docs.py auf.

Verwendung:
    python build.py            # kompiliert + generiert docs/
    python build.py --serve    # zusätzlich: startet mkdocs serve danach
    python build.py --force    # alle PDFs neu kompilieren (sonst nur veraltete)
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKRIPTE_DIR = Path("skripte")

def _find_pdflatex() -> str:
    env = os.environ.get("PDFLATEX")
    if env and Path(env).exists():
        return env
    on_path = shutil.which("pdflatex")
    if on_path:
        return on_path
    candidates = [
        r"C:\texlive\2026\bin\windows\pdflatex.exe",
        r"C:\texlive\2025\bin\windows\pdflatex.exe",
        r"C:\texlive\2024\bin\windows\pdflatex.exe",
        "/c/texlive/2026/bin/windows/pdflatex.exe",
        "/usr/bin/pdflatex",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return "pdflatex"


PDFLATEX = _find_pdflatex()


def needs_rebuild(tex: Path, force: bool) -> bool:
    if force:
        return True
    pdf = tex.with_suffix(".pdf")
    if not pdf.exists():
        return True
    return tex.stat().st_mtime > pdf.stat().st_mtime


def compile_tex(tex: Path) -> bool:
    """Kompiliert eine .tex-Datei (zweimal für ToC). Gibt True bei Erfolg zurück."""
    for _ in range(2):
        proc = subprocess.run(
            [PDFLATEX, "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=str(tex.parent),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            print(f"  [FEHLER] {tex}", file=sys.stderr)
            log = tex.with_suffix(".log")
            if log.exists():
                tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
                print("\n".join(tail), file=sys.stderr)
            return False
    return True


def cleanup_aux(tex: Path) -> None:
    """Entfernt LaTeX-Hilfsdateien neben der .tex."""
    for ext in (".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk", ".synctex.gz"):
        f = tex.with_suffix(ext)
        if f.exists():
            f.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Mathematikstudium – lokaler Build")
    parser.add_argument("--serve", action="store_true",
                        help="Nach Build mkdocs serve starten")
    parser.add_argument("--force", action="store_true",
                        help="Alle .tex-Dateien neu kompilieren")
    parser.add_argument("--skip-tex", action="store_true",
                        help="LaTeX-Kompilierung überspringen, nur Docs neu bauen")
    args = parser.parse_args()

    if not SKRIPTE_DIR.exists():
        print(f"[FEHLER] Verzeichnis {SKRIPTE_DIR} nicht gefunden – im Repo-Root ausführen.",
              file=sys.stderr)
        return 1

    if not args.skip_tex:
        if not Path(PDFLATEX).exists() and not shutil.which(PDFLATEX):
            print(f"[FEHLER] pdflatex nicht gefunden ({PDFLATEX}). "
                  f"PDFLATEX-Umgebungsvariable setzen oder TeX Live installieren.",
                  file=sys.stderr)
            return 1

        tex_files = sorted(SKRIPTE_DIR.rglob("*.tex"))
        todo = [t for t in tex_files if needs_rebuild(t, args.force)]
        print(f"LaTeX: {len(todo)} von {len(tex_files)} Dateien kompilieren …")

        failed = []
        for i, tex in enumerate(todo, 1):
            rel = tex.relative_to(SKRIPTE_DIR)
            print(f"  [{i}/{len(todo)}] {rel}")
            if not compile_tex(tex):
                failed.append(tex)
            cleanup_aux(tex)

        if failed:
            print(f"\n[FEHLER] {len(failed)} Datei(en) konnten nicht kompiliert werden:",
                  file=sys.stderr)
            for f in failed:
                print(f"  - {f}", file=sys.stderr)
            return 1

    print("\nGeneriere docs/ …")
    proc = subprocess.run([sys.executable, "generate_docs.py"])
    if proc.returncode != 0:
        return proc.returncode

    if args.serve:
        print("\nStarte mkdocs serve …")
        subprocess.run([sys.executable, "-m", "mkdocs", "serve"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
