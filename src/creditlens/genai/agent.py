"""Agent text-to-SQL : répond en français à une question sur le portefeuille.

L'agent se connecte au SERVEUR MCP (mcp_server/server.py) et n'a accès qu'à ses
3 outils, tous en lecture seule : list_tables, describe_table, run_query.

Déroulé d'une question :
  1. l'agent demande le schéma au serveur MCP (list_tables + describe_table)
  2. le LLM local (Ollama) écrit une requête SQL à partir de la question et du schéma
  3. le serveur MCP exécute la requête (lecture seule) et renvoie le résultat
  4. si le SQL est invalide, l'erreur est renvoyée au LLM qui se corrige (jusqu'à 3 essais)
  5. le LLM rédige la réponse finale en français à partir du résultat

Utilisation :
    python -m creditlens.genai.agent "Quel est le taux de défaut des moins de 30 ans ?"
    python -m creditlens.genai.agent                       # quelques questions de démonstration
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from creditlens.config import PROJECT_ROOT
from creditlens.genai import llm

SERVER = str(PROJECT_ROOT / "mcp_server" / "server.py")
MAX_SQL_TRIES = 3

SQL_PROMPT = """Tu écris UNE requête SQL PostgreSQL en lecture seule pour répondre à une question.

Schéma disponible (une seule table) :
{schema}

Règles de traduction (très important) :
- "combien", "nombre de clients" -> SELECT COUNT(*) ... (jamais AVG, ne sélectionne JAMAIS client_id).
- "total", "somme" -> SELECT SUM(colonne) ...
- "moyen", "moyenne" -> SELECT AVG(colonne) ... ; NE multiplie PAS par 100.
- "taux", "pourcentage", "part" -> ROUND(100.0 * AVG(colonne), 2) ; pour un taux de défaut, la colonne est is_default (0 ou 1).
- "maximum", "minimum" -> MAX(colonne) ou MIN(colonne), SANS GROUP BY.
- "par X", "pour chaque X", "selon X" -> ajoute GROUP BY X. Sinon, N'utilise PAS GROUP BY.
- probabilité de défaut = colonne pd ; défaut réel / taux de défaut = colonne is_default.
- Les colonnes de texte sont sensibles à la casse : gender vaut 'F' ou 'M', risk_class vaut 'A' à 'E'.
- Utilise uniquement les colonnes listées. Une seule instruction SELECT.

Exemples :
Question : Combien de clients ont fait défaut ?
{{"sql": "SELECT COUNT(*) FROM marts.v_portefeuille WHERE is_default = 1"}}
Question : Quel est le revenu moyen des clients ?
{{"sql": "SELECT ROUND(AVG(income)) FROM marts.v_portefeuille"}}
Question : Quelle est la perte attendue totale ?
{{"sql": "SELECT ROUND(SUM(expected_loss)) FROM marts.v_portefeuille"}}
Question : Quel est le montant de crédit maximum ?
{{"sql": "SELECT MAX(credit_amount) FROM marts.v_portefeuille"}}
Question : Quel est le taux de défaut par classe de risque, en pourcentage ?
{{"sql": "SELECT risk_class, ROUND(100.0 * AVG(is_default), 2) FROM marts.v_portefeuille GROUP BY risk_class ORDER BY risk_class"}}

Question : {question}

Réponds UNIQUEMENT avec un objet JSON : {{"sql": "SELECT ..."}}"""

FIX_PROMPT = """La requête a échoué.

Requête : {sql}
Erreur : {error}

Corrige-la. Réponds UNIQUEMENT avec un objet JSON : {{"sql": "SELECT ... corrigé"}}"""

ANSWER_PROMPT = """Question posée : {question}

Résultat de la requête SQL (format JSON) :
{result}

Rédige une réponse courte et factuelle en français, à partir de ce résultat uniquement.
N'invente aucun chiffre. Si le résultat est vide, dis-le."""


@dataclass
class AgentResult:
    question: str
    sql: str | None = None
    result: dict | None = None
    answer: str = ""
    error: str | None = None
    steps: list[str] = field(default_factory=list)


def extract_json(text: str) -> dict:
    start, depth = text.find("{"), 0
    if start == -1:
        raise ValueError(f"pas de JSON dans : {text[:80]}")
    for i in range(start, len(text)):
        depth += (text[i] == "{") - (text[i] == "}")
        if depth == 0:
            return json.loads(text[start:i + 1])
    raise ValueError("JSON incomplet")


async def _call(session: ClientSession, tool: str, args: dict) -> dict | list:
    res = await session.call_tool(tool, args)
    return json.loads(res.content[0].text)


def build_schema(tables: list, columns: list) -> str:
    desc = next((t.get("description", "") for t in tables if "v_portefeuille" in t["table"]), "")
    lines = [f"Table marts.v_portefeuille — {desc}", "Colonnes :"]
    lines += [f"  - {c['column']} ({c['type']}) : {c['description']}" for c in columns]
    return "\n".join(lines)


async def answer_async(question: str) -> AgentResult:
    result = AgentResult(question=question)
    # env=os.environ : le serveur MCP (sous-processus) hérite des mêmes réglages
    params = StdioServerParameters(command=sys.executable, args=[SERVER], env=dict(os.environ))
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tables = await _call(session, "list_tables", {})
                columns = await _call(session, "describe_table", {"table": "marts.v_portefeuille"})
                schema = build_schema(tables, columns)
                result.steps.append("schéma récupéré via MCP")

                prompt = SQL_PROMPT.format(schema=schema, question=question)
                for attempt in range(1, MAX_SQL_TRIES + 1):
                    reply = llm.chat(prompt, json_mode=True, temperature=0, max_tokens=300)
                    sql = str(extract_json(reply.text).get("sql", "")).strip()
                    result.sql = sql
                    result.steps.append(f"essai {attempt} : {sql}")
                    data = await _call(session, "run_query", {"sql": sql})
                    if isinstance(data, dict) and "error" in data:
                        result.steps.append(f"erreur : {data['error']}")
                        prompt = FIX_PROMPT.format(sql=sql, error=data["error"])
                        continue
                    result.result = data
                    break
                else:
                    result.error = "requête SQL invalide après 3 essais"
                    return result

                answer = llm.chat(
                    ANSWER_PROMPT.format(question=question,
                                         result=json.dumps(result.result, ensure_ascii=False)),
                    temperature=0.2, max_tokens=400)
                result.answer = answer.text.strip()
    except Exception as exc:                 # Ollama éteint, serveur injoignable...
        result.error = str(exc).split("\n")[0][:300]
    return result


def answer(question: str) -> AgentResult:
    """Version synchrone (pour la ligne de commande, Streamlit et les évaluations)."""
    return asyncio.run(answer_async(question))


DEMO = [
    "Quel est le taux de défaut global du portefeuille ?",
    "Combien de clients y a-t-il dans chaque classe de risque ?",
    "Quel est le taux de défaut des clients de moins de 30 ans ?",
    "Quelles sont les 3 professions avec le plus de clients, et leur taux de défaut ?",
]


def main() -> None:
    questions = sys.argv[1:] or DEMO
    for question in questions:
        print(f"\n### {question}")
        res = answer(question)
        if res.error:
            print(f"  [erreur] {res.error}")
            continue
        print(f"  SQL : {res.sql}")
        print(f"  Réponse : {res.answer}")


if __name__ == "__main__":
    main()
