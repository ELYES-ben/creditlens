"""Rapport de qualité des données : docs/data_quality_report.md

Contrôles réalisés sur le schéma raw :
  1. volumétrie : lignes et colonnes de chaque table
  2. unicité des identifiants (doublons)
  3. intégrité : lignes dont le client n'existe pas dans application_train
  4. valeurs manquantes par colonne (application_train)
  5. anomalies métier connues (365243, 'XNA', revenus aberrants, âges)

Utilisation :  python -m creditlens.quality.profile
"""
from __future__ import annotations

from datetime import date
from typing import Callable

from creditlens.config import DOCS_DIR

QueryFn = Callable[[str], list[tuple]]

# table -> colonne qui doit être unique
KEYS = {
    "application_train": "sk_id_curr",
    "bureau": "sk_id_bureau",
    "previous_application": "sk_id_prev",
}
# tables enfants -> doivent pointer vers un client existant
CHILDREN = ["bureau", "previous_application", "installments_payments"]

ANOMALIES = [
    ("DAYS_EMPLOYED = 365243 (code « sans emploi / retraité »)",
     "SELECT COUNT(*) FROM raw.application_train WHERE days_employed = '365243'",
     "Remplacé par NULL + colonne `no_employment_flag`"),
    ("CODE_GENDER = 'XNA' (sexe inconnu)",
     "SELECT COUNT(*) FROM raw.application_train WHERE code_gender = 'XNA'",
     "Remplacé par NULL"),
    ("ORGANIZATION_TYPE = 'XNA'",
     "SELECT COUNT(*) FROM raw.application_train WHERE organization_type = 'XNA'",
     "Remplacé par NULL (mêmes clients que 365243)"),
    ("NAME_FAMILY_STATUS = 'Unknown'",
     "SELECT COUNT(*) FROM raw.application_train WHERE name_family_status = 'Unknown'",
     "Remplacé par NULL"),
    ("Revenu > 10 M (valeur aberrante)",
     "SELECT COUNT(*) FROM raw.application_train WHERE amt_income_total::numeric > 10000000",
     "Conservé, signalé par `income_outlier_flag`"),
    ("Âge hors de 18-75 ans",
     "SELECT COUNT(*) FROM raw.application_train "
     "WHERE -days_birth::numeric / 365.25 NOT BETWEEN 18 AND 75",
     "À vérifier si > 0"),
    ("AMT_ANNUITY manquant",
     "SELECT COUNT(*) FROM raw.application_train WHERE amt_annuity IS NULL",
     "Ratios financiers à NULL pour ces clients"),
]


def scalar(query: QueryFn, sql: str):
    return query(sql)[0][0]


def raw_tables(query: QueryFn) -> list[str]:
    rows = query("SELECT table_name FROM information_schema.tables "
                 "WHERE table_schema = 'raw' ORDER BY table_name")
    return [r[0] for r in rows]


def columns_of(query: QueryFn, table: str) -> list[str]:
    rows = query("SELECT column_name FROM information_schema.columns "
                 f"WHERE table_schema = 'raw' AND table_name = '{table}' ORDER BY ordinal_position")
    return [r[0] for r in rows]


def num(n: int) -> str:
    """1234567 -> '1 234 567' (format français)."""
    return f"{n:,}".replace(",", " ")


def pct(part: int, total: int) -> str:
    return f"{100 * part / total:.2f} %" if total else "—"


def build_report(query: QueryFn, top_missing: int = 25) -> str:
    """Construit le rapport Markdown. `query(sql)` doit renvoyer une liste de tuples."""
    tables = raw_tables(query)
    out = [f"# Rapport qualité des données — CreditLens", "",
           f"Généré le {date.today():%d/%m/%Y} sur le schéma `raw`.", ""]

    # 1. Volumétrie
    out += ["## 1. Volumétrie", "", "| Table | Lignes | Colonnes |", "|---|---:|---:|"]
    n_rows = {}
    for t in tables:
        n_rows[t] = scalar(query, f"SELECT COUNT(*) FROM raw.{t}")
        out.append(f"| {t} | {num(n_rows[t])} | {len(columns_of(query, t))} |")
    out.append("")

    # 2. Unicité
    out += ["## 2. Unicité des identifiants", "", "| Table | Clé | Doublons |", "|---|---|---:|"]
    for t, key in KEYS.items():
        if t in tables:
            dup = scalar(query, f"SELECT COUNT(*) - COUNT(DISTINCT {key}) FROM raw.{t}")
            out.append(f"| {t} | {key} | {dup} |")
    out.append("")

    # 3. Intégrité
    if "application_train" in tables:
        out += ["## 3. Intégrité : clients inconnus dans les tables liées", "",
                "Lignes dont `sk_id_curr` n'existe pas dans `application_train` "
                "(normal en partie : Home Credit sépare les clients en train et test).", "",
                "| Table | Lignes orphelines | Part |", "|---|---:|---:|"]
        for t in CHILDREN:
            if t in tables:
                orphans = scalar(query,
                                 f"SELECT COUNT(*) FROM raw.{t} c WHERE NOT EXISTS "
                                 f"(SELECT 1 FROM raw.application_train a WHERE a.sk_id_curr = c.sk_id_curr)")
                out.append(f"| {t} | {num(orphans)} | {pct(orphans, n_rows[t])} |")
        out.append("")

    # 4. Valeurs manquantes
    if "application_train" in tables:
        cols = columns_of(query, "application_train")
        counts = query("SELECT " + ", ".join(f"COUNT({c})" for c in cols)
                       + " FROM raw.application_train")[0]
        total = n_rows["application_train"]
        missing = sorted(((c, total - k) for c, k in zip(cols, counts)), key=lambda x: -x[1])
        n_with_missing = sum(1 for _, m in missing if m > 0)
        n_over_50 = sum(1 for _, m in missing if total and m / total > 0.5)
        out += ["## 4. Valeurs manquantes (application_train)", "",
                f"{n_with_missing} colonnes sur {len(cols)} ont des valeurs manquantes ; "
                f"{n_over_50} en ont plus de 50 %.", "",
                f"| Colonne | Manquants | Part |", "|---|---:|---:|"]
        for c, m in missing[:top_missing]:
            if m == 0:
                break
            out.append(f"| {c} | {num(m)} | {pct(m, total)} |")
        out.append("")

    # 5. Anomalies
    if "application_train" in tables:
        total = n_rows["application_train"]
        out += ["## 5. Anomalies métier", "", "| Anomalie | Lignes | Part | Décision |",
                "|---|---:|---:|---|"]
        for label, sql, decision in ANOMALIES:
            k = scalar(query, sql)
            out.append(f"| {label} | {num(k)} | {pct(k, total)} | {decision} |")
        out.append("")

    return "\n".join(out)


def main() -> None:
    from sqlalchemy import text

    from creditlens.config import get_engine

    engine = get_engine()
    with engine.connect() as conn:
        report = build_report(lambda sql: [tuple(r) for r in conn.execute(text(sql))])
    path = DOCS_DIR / "data_quality_report.md"
    path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nRapport écrit dans {path}")


if __name__ == "__main__":
    main()
