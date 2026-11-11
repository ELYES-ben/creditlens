"""Vérifie que Python peut se connecter à la base CreditLens."""
from sqlalchemy import text

from creditlens.config import get_engine


def test_database_responds():
    """La base répond à une requête simple."""
    with get_engine().connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1


def test_three_schemas_exist():
    """Les 3 couches raw, staging et marts existent."""
    with get_engine().connect() as conn:
        rows = conn.execute(text("SELECT schema_name FROM information_schema.schemata"))
        schemas = {row[0] for row in rows}
    assert {"raw", "staging", "marts"} <= schemas