"""Accès en LECTURE SEULE à la base, utilisé par le serveur MCP de l'agent.

Trois protections superposées (« défense en profondeur ») :
  1. l'utilisateur PostgreSQL creditlens_reader n'a que le droit SELECT sur marts
  2. la requête est vérifiée ici : une seule instruction, SELECT ou WITH, aucun mot-clé d'écriture
  3. le résultat est limité à MAX_ROWS lignes et la requête à 20 secondes
"""
from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

from creditlens.config import PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")

MAX_ROWS = 200
ALLOWED_TABLES = ("v_portefeuille", "fct_complaints")     # ce que l'agent a le droit de voir
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|do|vacuum|"
    r"comment|merge|execute|set|reset|lock)\b", re.IGNORECASE)

_engine = None


def get_reader_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(URL.create(
            drivername="postgresql+psycopg2",
            username=os.getenv("DB_READER_USER", "creditlens_reader"),
            password=os.getenv("DB_READER_PASSWORD", "reader_local_only"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "creditlens"),
        ))
    return _engine


def check_sql(sql: str) -> str:
    """Vérifie que la requête est une lecture simple. Renvoie la requête nettoyée."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("requête vide")
    if ";" in cleaned:
        raise ValueError("une seule instruction SQL est autorisée")
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise ValueError("seules les requêtes SELECT sont autorisées")
    without_strings = re.sub(r"'[^']*'", "''", cleaned)       # on ignore le contenu des textes
    found = FORBIDDEN.search(without_strings)
    if found:
        raise ValueError(f"mot-clé interdit : {found.group(1).upper()}")
    return cleaned


def list_tables() -> list[dict]:
    sql = """SELECT c.relname AS table_name, obj_description(c.oid) AS description
             FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'marts' AND c.relname = ANY(:tables) ORDER BY 1"""
    with get_reader_engine().connect() as conn:
        rows = conn.execute(text(sql), {"tables": list(ALLOWED_TABLES)})
        return [{"table": f"marts.{r[0]}", "description": r[1] or ""} for r in rows]


def describe_table(table: str) -> list[dict]:
    name = table.split(".")[-1].strip().lower()
    if name not in ALLOWED_TABLES:
        raise ValueError(f"table inconnue : {table}. Tables disponibles : "
                         + ", ".join(f"marts.{t}" for t in ALLOWED_TABLES))
    sql = """SELECT a.attname, format_type(a.atttypid, a.atttypmod), col_description(a.attrelid, a.attnum)
             FROM pg_attribute a
             JOIN pg_class c ON c.oid = a.attrelid
             JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'marts' AND c.relname = :name AND a.attnum > 0 AND NOT a.attisdropped
             ORDER BY a.attnum"""
    with get_reader_engine().connect() as conn:
        rows = conn.execute(text(sql), {"name": name})
        return [{"column": r[0], "type": r[1], "description": r[2] or ""} for r in rows]


def run_query(sql: str) -> dict:
    cleaned = check_sql(sql)
    wrapped = f"SELECT * FROM ({cleaned}) AS q LIMIT {MAX_ROWS}"
    with get_reader_engine().connect() as conn:
        result = conn.execute(text(wrapped))
        columns = list(result.keys())
        rows = [[None if v is None else (float(v) if hasattr(v, "as_tuple") else v) for v in row]
                for row in result]
    return {"columns": columns, "rows": rows, "row_count": len(rows)}
