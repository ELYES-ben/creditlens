"""Configuration commune : chemins du projet et connexion à PostgreSQL.

Les identifiants sont lus dans le fichier .env (jamais écrits dans le code).
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

# Racine du projet : src/creditlens/config.py -> on remonte de 2 dossiers
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DOCS_DIR = PROJECT_ROOT / "docs"

# Lit le fichier .env et place ses valeurs dans les variables d'environnement
load_dotenv(PROJECT_ROOT / ".env")


def db_url() -> URL:
    """Construit l'adresse de connexion à partir du .env."""
    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )


def get_engine():
    """Renvoie un moteur SQLAlchemy connecté à la base CreditLens."""
    return create_engine(db_url())