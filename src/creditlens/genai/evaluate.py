"""Évaluation de l'agent text-to-SQL : mesure sa fiabilité sur des questions-tests.

Pour chaque question de evals/questions.yaml :
  1. on exécute la requête SQL DE RÉFÉRENCE (écrite à la main) -> réponse attendue
  2. on pose la question à l'agent -> sa requête + son résultat
  3. on compare les CHIFFRES des deux résultats (tolérance pour les arrondis)

Les bonnes réponses ne sont jamais écrites en dur : elles sont recalculées à chaque
exécution. Le score mesuré est le pourcentage de questions où l'agent trouve les
mêmes chiffres que la requête de référence.

Utilisation :  python -m creditlens.genai.evaluate
"""
from __future__ import annotations

import json
import re

import pandas as pd
import yaml

from creditlens.config import DOCS_DIR, PROJECT_ROOT
from creditlens.genai import agent

QUESTIONS = PROJECT_ROOT / "evals" / "questions.yaml"
REL_TOL = 0.02        # 2 % d'écart relatif toléré
ABS_TOL = 0.5         # ou 0.5 en valeur absolue (pour les pourcentages arrondis)


def numbers_from_rows(rows: list) -> list[float]:
    """Extrait tous les nombres d'un résultat (on ignore le texte des libellés)."""
    out = []
    for row in rows:
        for value in row:
            if isinstance(value, bool):
                out.append(float(value))
            elif isinstance(value, (int, float)):
                out.append(float(value))
            elif isinstance(value, str):
                m = re.fullmatch(r"-?\d+(?:\.\d+)?", value.strip())
                if m:
                    out.append(float(value))
    return out


def close(a: float, b: float) -> bool:
    return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))


def matches(expected: list[float], got: list[float]) -> bool:
    """Chaque nombre attendu doit se retrouver dans le résultat de l'agent."""
    if not expected:
        return False
    available = list(got)
    for value in expected:
        hit = next((g for g in available if close(value, g)), None)
        if hit is None:
            return False
        available.remove(hit)
    return True


def reference_numbers(engine, sql: str) -> list[float]:
    """Nombres attendus = valeurs de la DERNIÈRE colonne (la mesure).
    Les premières colonnes sont des étiquettes de groupe (risk_class, gender...)
    ou des 0/1 qu'il ne faut pas comparer."""
    with engine.connect() as conn:
        from sqlalchemy import text
        rows = [list(r) for r in conn.execute(text(sql))]
    measure = [[float(r[-1]) if hasattr(r[-1], "as_tuple") else r[-1]] for r in rows]
    return numbers_from_rows(measure)


def main() -> None:
    from creditlens.config import get_engine

    engine = get_engine()
    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    records = []
    print(f"Évaluation de l'agent sur {len(questions)} questions ({agent.llm.LLM_MODEL})...\n")
    for i, q in enumerate(questions, 1):
        expected = reference_numbers(engine, q["reference_sql"])
        res = agent.answer(q["question"])
        got = numbers_from_rows(res.result["rows"]) if res.result else []
        ok = res.error is None and matches(expected, got)
        records.append({"id": q["id"], "question": q["question"], "correct": ok,
                        "attendu": expected, "obtenu": got,
                        "sql_agent": res.sql or "", "erreur": res.error or ""})
        print(f"  [{i:2}/{len(questions)}] {q['id']} {'OK ' if ok else 'ECHEC'} — {q['question'][:60]}")
        if not ok:
            print(f"        attendu {expected} | obtenu {got} | {res.error or res.sql}")

    df = pd.DataFrame(records)
    score = 100 * df["correct"].mean()
    print(f"\n=== Fiabilité de l'agent : {score:.0f} % ({df['correct'].sum()}/{len(df)}) ===")

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "agent_eval_results.json").write_text(
        json.dumps({"nb_questions": len(df), "nb_correct": int(df["correct"].sum()),
                    "fiabilite_pct": round(score, 1), "modele": agent.llm.LLM_MODEL,
                    "details": records}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    report = [
        "# Évaluation de l'agent text-to-SQL", "",
        f"**Fiabilité : {score:.0f} %** — {int(df['correct'].sum())} réponses correctes "
        f"sur {len(df)} questions-tests, avec le modèle local `{agent.llm.LLM_MODEL}`.", "",
        "Méthode : pour chaque question, le résultat de l'agent est comparé à celui d'une "
        "requête SQL de référence écrite à la main. Les chiffres attendus sont recalculés à "
        "chaque exécution (jamais écrits en dur).", "",
        "| # | Question | Résultat |", "|---|---|---|",
        *[f"| {r['id']} | {r['question']} | {'✅' if r['correct'] else '❌'} |" for r in records], "",
    ]
    (DOCS_DIR / "agent_eval_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Rapport : docs/agent_eval_report.md")


if __name__ == "__main__":
    main()
