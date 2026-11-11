"""Exécute un fichier SQL, ou tous les fichiers .sql d'un dossier dans l'ordre (01_, 02_, ...).

Utilisation (racine du projet, environnement virtuel activé) :
    python -m creditlens.run_sql sql/02_staging          # crée toutes les tables staging
    python -m creditlens.run_sql sql/04_analysis/01_portefeuille.sql   # affiche le résultat
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from creditlens.config import PROJECT_ROOT


def sql_files(target: Path) -> list[Path]:
    """Renvoie le fichier, ou les .sql du dossier triés par nom."""
    if target.is_file():
        return [target]
    files = sorted(target.glob("*.sql"))
    if not files:
        raise SystemExit(f"Aucun fichier .sql dans {target}")
    return files


def format_table(columns: list[str], rows: list[tuple], max_rows: int = 50) -> str:
    """Met un résultat de requête en forme de tableau texte lisible."""
    shown = [["" if v is None else str(v) for v in row] for row in rows[:max_rows]]
    widths = [max([len(c)] + [len(r[i]) for r in shown]) for i, c in enumerate(columns)]
    line = " | ".join(c.ljust(w) for c, w in zip(columns, widths))
    sep = "-+-".join("-" * w for w in widths)
    body = [" | ".join(v.ljust(w) for v, w in zip(r, widths)) for r in shown]
    more = [f"... ({len(rows) - max_rows} lignes de plus)"] if len(rows) > max_rows else []
    return "\n".join([line, sep, *body, *more])


def run_file(conn, path: Path) -> None:
    """Exécute un fichier ; si la dernière instruction renvoie des lignes, les affiche."""
    start = time.time()
    cur = conn.cursor()
    try:
        cur.execute(path.read_text(encoding="utf-8"))
        rows = cur.fetchall() if cur.description else None
        columns = [d[0] for d in cur.description] if cur.description else []
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
    print(f"OK  {path.name}  ({time.time() - start:.1f} s)")
    if rows is not None:
        print(format_table(columns, rows), "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Exécute des scripts SQL sur la base CreditLens.")
    parser.add_argument("target", help="fichier .sql ou dossier contenant des .sql")
    args = parser.parse_args()

    target = Path(args.target)
    if not target.is_absolute():
        target = PROJECT_ROOT / target

    from creditlens.config import get_engine

    conn = get_engine().raw_connection()
    try:
        for path in sql_files(target):
            run_file(conn, path)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
