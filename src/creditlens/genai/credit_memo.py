"""Note de crédit générée par l'IA : aide à la décision pour un conseiller bancaire.

Pour un client donné :
  1. le MODÈLE calcule sa probabilité de défaut (PD), sa classe de risque et sa perte attendue
  2. on extrait les facteurs qui font monter ou baisser son risque (valeurs SHAP)
  3. le LLM local (Ollama) rédige une note courte à partir de ces faits

Règle de conception : tous les CHIFFRES viennent du code (modèle + base de données).
Le LLM ne fait que rédiger ; il lui est interdit d'inventer un chiffre.
La décision finale reste humaine.

Utilisation :
    python -m creditlens.genai.credit_memo                  # 3 clients exemples (classes A, C, E)
    python -m creditlens.genai.credit_memo --client 100002  # un client précis
"""
from __future__ import annotations

import argparse

import joblib
import numpy as np
import pandas as pd

from creditlens.config import DOCS_DIR, PROJECT_ROOT
from creditlens.genai import llm

MODEL_PATH = PROJECT_ROOT / "models" / "pd_model.pkl"
MEMO_DIR = DOCS_DIR / "credit_memos"
LGD = 0.45
CLASS_BOUNDS = [(0.025, "A"), (0.05, "B"), (0.10, "C"), (0.20, "D"), (1.01, "E")]
CLASS_LABEL = {"A": "risque très faible", "B": "risque faible", "C": "risque moyen",
               "D": "risque élevé", "E": "risque très élevé"}

# Noms lisibles des variables (pour le conseiller, pas pour le data scientist)
LABELS = {
    "ext_source_1": "score externe n°1 (agence de crédit)",
    "ext_source_2": "score externe n°2 (agence de crédit)",
    "ext_source_3": "score externe n°3 (agence de crédit)",
    "credit_term": "durée du crédit (nombre d'échéances)",
    "credit_to_goods": "montant emprunté / prix du bien",
    "credit_to_income": "montant emprunté / revenu annuel",
    "annuity_to_income": "taux d'effort (échéance / revenu)",
    "years_employed": "ancienneté dans l'emploi (années)",
    "age_years": "âge (années)",
    "income": "revenu annuel",
    "credit_amount": "montant du crédit",
    "annuity": "montant de l'échéance",
    "goods_price": "prix du bien financé",
    "education": "niveau d'études",
    "income_type": "type de revenu",
    "occupation": "profession",
    "organization_type": "secteur de l'employeur",
    "family_status": "situation familiale",
    "housing_type": "type de logement",
    "contract_type": "type de contrat",
    "owns_car": "possède une voiture (1 = oui)",
    "owns_realty": "propriétaire d'un bien immobilier (1 = oui)",
    "nb_children": "nombre d'enfants",
    "family_size": "taille du foyer",
    "region_rating": "note de la région (1 = meilleure, 3 = moins bonne)",
    "region_population": "densité de population de la région",
    "no_employment_flag": "sans emploi ou retraité (1 = oui)",
    "bureau_nb_credits": "nombre de crédits dans d'autres établissements",
    "bureau_nb_active": "crédits en cours ailleurs",
    "bureau_nb_bad_debt": "créances irrécouvrables ailleurs",
    "bureau_total_debt": "dette totale dans d'autres établissements",
    "bureau_total_overdue": "montant en retard ailleurs",
    "bureau_max_days_overdue": "retard maximum ailleurs (jours)",
    "bureau_nb_prolongations": "prolongations de crédit ailleurs",
    "prev_nb_applications": "nombre de demandes passées",
    "prev_nb_refused": "nombre de demandes refusées",
    "prev_refused_share": "part de demandes passées refusées",
    "prev_avg_amount_requested": "montant moyen demandé par le passé",
    "inst_nb_installments": "nombre d'échéances déjà payées",
    "inst_late_share": "part d'échéances payées en retard",
    "inst_max_days_late": "retard de paiement maximum (jours)",
    "inst_avg_days_late": "retard de paiement moyen (jours)",
    "inst_underpaid_share": "part d'échéances payées partiellement",
}

PROMPT = """Tu es analyste crédit dans une banque. Rédige une note de crédit en français pour
un conseiller, à partir des FAITS ci-dessous.

Règles strictes :
- Utilise uniquement les faits fournis. N'invente aucun chiffre et n'ajoute aucune information.
- Écris 4 paragraphes courts, avec ces titres exacts :
  **Synthèse**, **Facteurs de risque**, **Points favorables**, **Recommandation**
- 150 à 200 mots au total, ton professionnel et factuel.
- Ne calcule aucun ratio ni pourcentage toi-même : reprends les indications
  "au-dessus / en dessous de la médiane" telles quelles sont écrites.
- NE JUGE PAS toi-même si le risque est élevé ou faible : reprends le "niveau de risque"
  indiqué dans les faits (ne dis jamais qu'un risque de 1 % est élevé).
- Dans **Recommandation**, reprends mot pour mot la RECOMMANDATION INDICATIVE calculée
  dans les faits (ne la contredis jamais), justifie-la en une phrase à partir des facteurs,
  et termine par cette phrase exacte : "La décision finale appartient au conseiller."

FAITS
{facts}"""


def risk_class(pd_value: float) -> str:
    return next(label for bound, label in CLASS_BOUNDS if pd_value < bound)


def fmt(value) -> str:
    """Affiche une valeur de façon lisible."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "non renseigné"
    if isinstance(value, (int, float, np.integer, np.floating)):
        v = float(value)
        if abs(v) >= 1000:
            return f"{v:,.0f}".replace(",", " ")
        return f"{v:.2f}".rstrip("0").rstrip(".") if v != int(v) else f"{int(v)}"
    return str(value)


def to_numeric_frame(df: pd.DataFrame, categorical: list[str]) -> pd.DataFrame:
    """PostgreSQL renvoie des Decimal : on convertit les colonnes numériques."""
    df = df.copy()
    for col in df.columns:
        if col not in categorical and col != "gender":
            df[col] = pd.to_numeric(df[col].astype("object"), errors="coerce").astype(float)
    return df


def model_frame(row: pd.DataFrame, features: list[str], categorical: list[str], booster) -> pd.DataFrame:
    """Met la ligne du client au format attendu par LightGBM (mêmes catégories qu'à l'entraînement)."""
    X = row[features].copy()
    trained = booster.pandas_categorical or []
    for col, cats in zip(categorical, trained):
        X[col] = pd.Categorical(X[col], categories=cats)
    return X


def split_factors(features: list[str], contrib: np.ndarray, values: dict, top: int = 3):
    """Sépare les variables qui augmentent le risque de celles qui le diminuent."""
    order = np.argsort(-np.abs(contrib))
    up, down = [], []
    for j in order:
        name = features[j]
        item = (name, LABELS.get(name, name), values.get(name), float(contrib[j]))
        if contrib[j] > 0 and len(up) < top:
            up.append(item)
        elif contrib[j] < 0 and len(down) < top:
            down.append(item)
        if len(up) == top and len(down) == top:
            break
    return up, down


def medians(engine, names: list[str]) -> dict:
    """Médiane du portefeuille pour les variables numériques citées (point de comparaison)."""
    if not names:
        return {}
    cols = ", ".join(f"percentile_cont(0.5) WITHIN GROUP (ORDER BY {n}) AS {n}" for n in names)
    row = pd.read_sql(f"SELECT {cols} FROM marts.client_features", engine).iloc[0]
    return {n: float(row[n]) for n in names if row[n] is not None}


RISK_WORD = {"A": "très faible", "B": "faible", "C": "moyenne", "D": "élevée", "E": "très élevée"}


def recommendation(pd_value: float, threshold: float) -> str:
    """Verdict indicatif, calculé par une règle fixe (jamais laissé au LLM)."""
    if pd_value > threshold:
        return "REFUSER — probabilité de défaut au-dessus du seuil de la politique d'octroi"
    if pd_value > 0.6 * threshold:
        return "ACCEPTER AVEC VIGILANCE — risque notable mais sous le seuil (tarification au risque conseillée)"
    return "ACCEPTER — risque maîtrisé, sous le seuil de la politique d'octroi"


def build_facts(client: dict, pd_value: float, threshold: float, up, down, med: dict) -> str:
    cls = risk_class(pd_value)
    el = pd_value * LGD * float(client["credit_amount"])

    def line(item):
        name, label, value, _ = item
        ref = ""
        if name in med and isinstance(value, (int, float, np.integer, np.floating)) \
                and not (isinstance(value, float) and np.isnan(value)):
            ref = (" (au-dessus de la médiane du portefeuille)" if float(value) > med[name]
                   else " (en dessous de la médiane du portefeuille)")
        return f"  - {label} : {fmt(value)}{ref}"

    return "\n".join([
        f"- Probabilité de défaut estimée par le modèle : {100 * pd_value:.1f} % "
        f"(moyenne du portefeuille : 8,1 %) — niveau de risque : {RISK_WORD[cls]}",
        f"- Classe de risque : {cls} ({CLASS_LABEL[cls]}) sur une échelle de A (meilleur) à E",
        f"- RECOMMANDATION INDICATIVE (calculée) : {recommendation(pd_value, threshold)}",
        f"- Seuil de refus indicatif de la politique d'octroi : {100 * threshold:.1f} %",
        f"- Montant du crédit demandé : {fmt(client['credit_amount'])} ; revenu annuel : {fmt(client['income'])}",
        f"- Perte attendue : {fmt(el)} (PD x LGD 45 % x montant)",
        f"- Âge : {fmt(client['age_years'])} ans ; type de revenu : {fmt(client['income_type'])} ; "
        f"études : {fmt(client['education'])}",
        "- Éléments qui AUGMENTENT le risque (du plus au moins important) :",
        *[line(i) for i in up],
        "- Éléments qui DIMINUENT le risque (du plus au moins important) :",
        *[line(i) for i in down],
    ])


def write_memo(client_id: int, facts: str, text: str, model_name: str) -> str:
    MEMO_DIR.mkdir(parents=True, exist_ok=True)
    path = MEMO_DIR / f"memo_{client_id}.md"
    path.write_text("\n".join([
        f"# Note de crédit — client {client_id}", "",
        "## Faits (calculés par le modèle de scoring et la base de données)", "",
        facts, "",
        f"## Analyse (rédigée par l'IA : `{model_name}`, modèle local)", "",
        text.strip(), "",
        "---",
        "*Note d'aide à la décision générée automatiquement. Les chiffres proviennent du modèle "
        "de scoring ; le texte est rédigé par un LLM et doit être relu. "
        "La décision d'octroi reste de la responsabilité du conseiller.*", "",
    ]), encoding="utf-8")
    return str(path)


def make_memo(engine, bundle: dict, client_id: int) -> None:
    model, features, categorical = bundle["model"], bundle["features"], bundle["categorical"]
    raw = pd.read_sql(f"SELECT * FROM marts.client_features WHERE client_id = {int(client_id)}", engine)
    if raw.empty:
        print(f"Client {client_id} introuvable.")
        return
    row = to_numeric_frame(raw, categorical)
    X = model_frame(row, features, categorical, model.booster_)
    pd_value = float(model.predict_proba(X)[0, 1])
    contrib = model.predict(X, pred_contrib=True)[0][:-1]     # valeurs SHAP natives de LightGBM
    client = row.iloc[0].to_dict()
    up, down = split_factors(features, contrib, client)
    numeric = [i[0] for i in up + down if i[0] not in categorical]
    facts = build_facts(client, pd_value, bundle["threshold"], up, down, medians(engine, numeric))
    reply = llm.chat(PROMPT.format(facts=facts), temperature=0.2, max_tokens=500)
    path = write_memo(int(client_id), facts, reply.text, reply.model)
    print(f"\n=== Client {client_id} : PD {100 * pd_value:.1f} %, classe {risk_class(pd_value)} ===")
    print(reply.text.strip())
    print(f"-> {path}")


def example_clients(engine) -> list[int]:
    """Un client du jeu de test par classe A, C et E (jamais vus par le modèle)."""
    sql = """SELECT DISTINCT ON (risk_class) client_id
             FROM marts.fct_expected_loss
             WHERE in_test_set AND risk_class IN ('A', 'C', 'E')
             ORDER BY risk_class, client_id"""
    return pd.read_sql(sql, engine)["client_id"].astype(int).tolist()


def main() -> None:
    from creditlens.config import get_engine

    parser = argparse.ArgumentParser(description="Note de crédit générée par l'IA")
    parser.add_argument("--client", type=int, nargs="*", help="identifiant(s) client")
    args = parser.parse_args()
    if not MODEL_PATH.exists():
        raise SystemExit("Modèle introuvable : lance d'abord python -m creditlens.risk.train_model")
    engine = get_engine()
    bundle = joblib.load(MODEL_PATH)
    for client_id in (args.client or example_clients(engine)):
        make_memo(engine, bundle, client_id)


if __name__ == "__main__":
    main()
