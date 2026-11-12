"""Serveur MCP de CreditLens : expose la base de données à un agent IA, en lecture seule.

MCP (Model Context Protocol) est un standard ouvert : n'importe quel client compatible
(notre agent, Claude Desktop, un IDE...) peut découvrir et appeler ces 3 outils.

    list_tables      -> quelles tables puis-je interroger ?
    describe_table   -> quelles colonnes contient cette table, et que signifient-elles ?
    run_query        -> exécute une requête SELECT (200 lignes max, lecture seule)

Lancement manuel (l'agent le démarre tout seul) :  python mcp_server/server.py
"""
from __future__ import annotations

import importlib
import json
import os

try:                                    # SDK MCP version 2
    from mcp.server.mcpserver import MCPServer
except ImportError:                     # SDK MCP version 1
    from mcp.server.fastmcp import FastMCP as MCPServer

# Le module d'accès à la base peut être remplacé pour les tests (sans PostgreSQL)
db = importlib.import_module(os.getenv("CREDITLENS_DB_BACKEND", "creditlens.genai.db_readonly"))

server = MCPServer("creditlens")


def _json(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


@server.tool()
def list_tables() -> str:
    """Liste les tables que l'agent peut interroger, avec leur description."""
    try:
        return _json(db.list_tables())
    except Exception as exc:
        return _json({"error": str(exc)})


@server.tool()
def describe_table(table: str) -> str:
    """Donne les colonnes d'une table (nom, type, description en français)."""
    try:
        return _json(db.describe_table(table))
    except Exception as exc:
        return _json({"error": str(exc)})


@server.tool()
def run_query(sql: str) -> str:
    """Exécute une requête SQL SELECT en lecture seule (200 lignes maximum)."""
    try:
        return _json(db.run_query(sql))
    except Exception as exc:
        message = str(exc).split("\n")[0][:400]      # message court : il sera relu par le LLM
        return _json({"error": message})


if __name__ == "__main__":
    server.run()        # transport stdio : le client lance ce script et lui parle directement
