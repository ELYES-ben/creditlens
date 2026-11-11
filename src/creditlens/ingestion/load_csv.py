"""Charge les CSV de data/raw/ dans le schéma `raw` de PostgreSQL.

Principe ELT : fichiers chargés TELS QUELS, toutes colonnes en TEXT.
Le typage et le nettoyage se font ensuite en SQL dans `staging`.

Utilisation (racine du projet, .venv activé) :
    python -m creditlens.ingestion.load_csv
    python -m creditlens.ingestion.load_csv --only application_train
"""
from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path

from creditlens.config import RAW_DIR, get_engine

ENCODINGS = ("utf-8", "latin-1")  # le dictionnaire des colonnes n'est pas en UTF-8
SKIP = {"sample_submission"}      # fichier propre à Kaggle, inutile ici


def clean_name(name: str) -> str:
    """'AMT_INCOME_TOTAL' -> 'amt_income_total' (minuscules = pas de guillemets en SQL)."""
    name = re.sub(r"[^0-9a-zA-Z_]+", "_", name.strip()).strip("_").lower() or "col"
    if name[0].isdigit():
        name = f"c_{name}"
    if name in {"table", "user", "order", "group", "select", "from", "where"}:
        name = f"{name}_"
    return name


def read_header(path: Path) -> tuple[list[str], str]:
    """Lit la ligne d'en-tête et détecte l'encodage du fichier."""
    for enc in ENCODINGS:
        try:
            with open(path, encoding=enc, newline="") as f:
                header = next(csv.reader(f))
                f.read(1_000_000)
            return header, enc
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Encodage non reconnu : {path.name}")


def unique_columns(header: list[str]) -> list[str]:
    """Nettoie les noms et évite les doublons (col, col_2...)."""
    seen: dict[str, int] = {}
    cols = []
    for raw in header:
        base = clean_name(raw)
        seen[base] = seen.get(base, 0) + 1
        cols.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return cols


def load_file(conn, path: Path) -> int:
    """Charge un CSV dans raw.<nom_du_fichier>. Renvoie le nombre de lignes."""
    table = clean_name(path.stem)
    header, enc = read_header(path)
    cols = unique_columns(header)
    cur = conn.cursor()
    try:
        cur.execute(f"DROP TABLE IF EXISTS raw.{table};")
        cur.execute(f"CREATE TABLE raw.{table} ({', '.join(c + ' TEXT' for c in cols)});")
        with open(path, encoding=enc, newline="") as f:
            cur.copy_expert(
                f"COPY raw.{table} ({', '.join(cols)}) "
                "FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')",
                f,
            )
        cur.execute(f"SELECT COUNT(*) FROM raw.{table};")
        n = cur.fetchone()[0]
        conn.commit()
        return n
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Charge les CSV dans le schéma raw.")
    parser.add_argument("--only", nargs="*", help="ex. application_train bureau")
    args = parser.parse_args()

    files = [p for p in sorted(RAW_DIR.glob("*.csv")) if p.stem.lower() not in SKIP]
    if args.only:
        wanted = {n.lower() for n in args.only}
        files = [p for p in files if p.stem.lower() in wanted]
    if not files:
        raise SystemExit(f"Aucun CSV trouvé dans {RAW_DIR}")

    conn = get_engine().raw_connection()  # connexion psycopg2, nécessaire pour COPY
    try:
        for p in files:
            start = time.time()
            print(f"-> {p.name} ({p.stat().st_size / 1e6:,.0f} Mo) ...", end=" ", flush=True)
            n = load_file(conn, p)
            print(f"{n:,} lignes en {time.time() - start:.0f} s")
    finally:
        conn.close()
    print("Chargement terminé.")


if __name__ == "__main__":
    main()
