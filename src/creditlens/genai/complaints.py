"""Réclamations clients : normalisation de la taxonomie par un LLM local (Ollama, gratuit).

Données : data/raw/complaints.csv — base publique CFPB (toutes les réclamations
déposées contre des établissements financiers américains depuis 2011).
Depuis 2026 le CFPB ne publie plus le texte libre des réclamations : on travaille
donc sur les INTITULÉS déclarés (produit, problème, détail du problème).

Principe : il existe des centaines de combinaisons (produit, problème, détail),
rédigées en anglais et peu lisibles pour un comité. Le LLM lit chaque combinaison
et la range dans un des 9 motifs métier, avec une gravité. Ce classement est
ensuite appliqué à toutes les réclamations (plusieurs millions de lignes).

4 commandes, à lancer dans l'ordre :
  1. python -m creditlens.genai.complaints prepare      # agrège le gros fichier
  2. python -m creditlens.genai.complaints classify --limit 20   # test
     python -m creditlens.genai.complaints classify              # les 300 plus fréquentes
  3. python -m creditlens.genai.complaints validate     # compare le LLM à TON classement
  4. python -m creditlens.genai.complaints report       # table marts + rapport
"""
from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from creditlens.config import DOCS_DIR, RAW_DIR
from creditlens.genai import llm

SOURCE = RAW_DIR / "complaints.csv"
AGG = RAW_DIR / "complaints_agg.csv"              # nb de réclamations par année x combinaison
COMBOS = RAW_DIR / "complaints_combos.csv"        # combinaisons uniques, triées par volume
COMPANIES = RAW_DIR / "complaints_companies.csv"  # volume par établissement
LABELS = RAW_DIR / "complaints_labels_v3.jsonl"   # 1 ligne JSON par combinaison classée
VALIDATION = DOCS_DIR / "complaints_validation.csv"

WORKERS = 2          # requêtes en parallèle (le PC fait tourner le modèle)
DEFAULT_TOP = 300    # nombre de combinaisons classées par défaut (les plus fréquentes)

COLS = {"Date received": "date_received", "Product": "product", "Issue": "issue",
        "Sub-issue": "sub_issue", "Company": "company",
        "Company response to consumer": "response", "Timely response?": "timely"}
KEYS = ["product", "issue", "sub_issue"]

MOTIFS = {
    "frais": "frais, commissions, taux ou tarification contestés",
    "fraude": "fraude, arnaque, usurpation d'identité, opération non autorisée",
    "erreur_compte": "erreur ou problème sur un compte, un paiement, un virement, un relevé",
    "credit_refus_conditions": "octroi, refus, conditions ou modification d'un crédit",
    "recouvrement": "recouvrement de dette, relances, menaces, dette non reconnue",
    "rapport_credit": "information erronée ou usage abusif d'un rapport / score de crédit",
    "difficulte_remboursement": "difficultés à rembourser, saisie, restructuration, impayés",
    "service_client": "service client, communication, délais, enquête de l'établissement",
    "autre": "aucun des motifs ci-dessus",
}

PROMPT = """Tu es analyste qualité dans une banque. Voici une catégorie de réclamation client
(intitulés officiels en anglais).

1. Range-la dans UN seul motif métier :
{motifs}

2. Réponds par true ou false à ces 3 questions :
- "fraude" : s'agit-il d'une fraude, d'une arnaque ou d'une usurpation d'identité ?
- "menace_ou_saisie" : y a-t-il une menace, une action en justice, une saisie ou la perte du logement ?
- "impact_financier" : le client subit-il une erreur ou un préjudice concret (information erronée
  dans son dossier, montant ou frais contesté, dette réclamée à tort, paiement mal traité,
  crédit refusé) ? Réponds false s'il s'agit seulement d'un retard, d'un manque d'information
  ou d'une mauvaise communication.

Réponds UNIQUEMENT avec un objet JSON :
{{"motif": "<un des motifs>", "fraude": <true ou false>, "menace_ou_saisie": <true ou false>,
"impact_financier": <true ou false>, "resume": "<description en une phrase, en français>"}}

Catégorie de réclamation :
- Produit : {product}
- Problème : {issue}
- Détail : {sub_issue}"""

# Mots-clés qui imposent la gravité 3, quelle que soit la réponse du LLM (filet de sécurité)
GRAVE_KEYWORDS = ("identity theft", "fraud", "scam", "foreclosure", "sue ", "sued", "lawsuit",
                  "legal action", "arrest", "jail", "threaten", "repossess", "garnish")


def compute_gravite(flags: dict, row: dict) -> int:
    """La gravité est calculée par une RÈGLE fixe, pas notée par le LLM.

    3 = fraude, menace, action en justice ou saisie
    2 = erreur ou préjudice financier concret
    1 = retard, manque d'information, mauvaise communication
    """
    text = f"{row['issue']} {row['sub_issue']}".lower()
    if flags["fraude"] or flags["menace_ou_saisie"] or any(k in text for k in GRAVE_KEYWORDS):
        return 3
    return 2 if flags["impact_financier"] else 1


# --------------------------------------------------------------------------- 1. prepare
def prepare() -> None:
    """Lit le gros fichier par morceaux et compte les réclamations par année et combinaison."""
    if not SOURCE.exists():
        raise SystemExit(f"Fichier introuvable : {SOURCE}")
    parts, companies, total = [], [], 0
    for chunk in pd.read_csv(SOURCE, usecols=list(COLS), chunksize=500_000, dtype=str):
        chunk = chunk.rename(columns=COLS)
        total += len(chunk)
        chunk["annee"] = chunk["date_received"].str[:4]
        chunk[KEYS] = chunk[KEYS].fillna("")
        chunk["dans_les_delais"] = (chunk["timely"] == "Yes").astype(int)
        chunk["dedommagement"] = (chunk["response"] == "Closed with monetary relief").astype(int)
        parts.append(chunk.groupby(["annee", *KEYS], as_index=False)
                          .agg(nb=("dans_les_delais", "size"), nb_dans_les_delais=("dans_les_delais", "sum"),
                               nb_dedommagement=("dedommagement", "sum")))
        companies.append(chunk.groupby("company").size())
        print(f"\r    {total:,} réclamations lues", end="", flush=True)
    print()
    agg = pd.concat(parts).groupby(["annee", *KEYS], as_index=False).sum()
    combos = (agg.groupby(KEYS, as_index=False)["nb"].sum()
                 .sort_values("nb", ascending=False).reset_index(drop=True))
    combos.insert(0, "combo_id", [f"C{i:04d}" for i in range(1, len(combos) + 1)])
    combos["part_cumulee_pct"] = (100 * combos["nb"].cumsum() / combos["nb"].sum()).round(2)
    agg = agg.merge(combos[["combo_id", *KEYS]], on=KEYS)
    agg.to_csv(AGG, index=False)
    combos.to_csv(COMBOS, index=False)
    (pd.concat(companies).groupby(level=0).sum().sort_values(ascending=False)
       .rename("nb").rename_axis("company").reset_index().to_csv(COMPANIES, index=False))
    top = min(DEFAULT_TOP, len(combos))
    print(f"    {total:,} réclamations, de {agg['annee'].min()} à {agg['annee'].max()}")
    print(f"    {len(combos):,} combinaisons (produit, problème, détail) différentes")
    print(f"    Les {top} plus fréquentes couvrent {combos['part_cumulee_pct'].iloc[top - 1]} % des réclamations")


# --------------------------------------------------------------------------- 2. classify
def build_prompt(row: dict) -> str:
    motifs = "\n".join(f"- {k} : {v}" for k, v in MOTIFS.items())
    return PROMPT.format(motifs=motifs, product=row["product"], issue=row["issue"],
                         sub_issue=row["sub_issue"] or "(non précisé)")


def to_bool(value) -> bool:
    return value is True or str(value).strip().lower() in ("true", "vrai", "oui", "yes", "1")


def parse_answer(text: str, row: dict) -> dict:
    """Extrait le JSON de la réponse, le vérifie et calcule la gravité."""
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError(f"pas de JSON : {text[:80]}")
    data = json.loads(match.group(0))
    motif = str(data.get("motif", "")).strip()
    if motif not in MOTIFS:
        motif = "autre"
    flags = {k: to_bool(data.get(k, False)) for k in ("fraude", "menace_ou_saisie", "impact_financier")}
    return {"motif": motif, "gravite": compute_gravite(flags, row), **flags,
            "resume": str(data.get("resume", "")).strip()}


def classify_one(row: dict) -> dict:
    reply = llm.chat(build_prompt(row), json_mode=True, temperature=0, max_tokens=200)
    return {"combo_id": row["combo_id"], **parse_answer(reply.text, row), "model": reply.model,
            "input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens}


def done_ids() -> set[str]:
    if not LABELS.exists():
        return set()
    with open(LABELS, encoding="utf-8") as f:
        return {json.loads(line)["combo_id"] for line in f if line.strip()}


def classify(limit: int | None) -> None:
    combos = pd.read_csv(COMBOS, dtype=str, keep_default_na=False)
    target = combos.head(limit or DEFAULT_TOP)            # les plus fréquentes d'abord
    todo = target[~target["combo_id"].isin(done_ids())]
    print(f"    {len(todo):,} combinaisons à classer avec {llm.LLM_MODEL} (local, gratuit)")
    tokens_in = tokens_out = errors = 0
    start = time.time()
    with open(LABELS, "a", encoding="utf-8") as out, ThreadPoolExecutor(WORKERS) as pool:
        futures = {pool.submit(classify_one, r): r for r in todo.to_dict("records")}
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                res = fut.result()
                out.write(json.dumps(res, ensure_ascii=False) + "\n")
                out.flush()
                tokens_in += res["input_tokens"]
                tokens_out += res["output_tokens"]
            except Exception as exc:                     # une réponse ratée n'arrête pas tout
                errors += 1
                print(f"\n    erreur sur {futures[fut]['combo_id']} : {exc}")
            print(f"\r    {i}/{len(todo)} | tokens entrée {tokens_in:,} | sortie {tokens_out:,} "
                  f"| erreurs {errors} | {time.time() - start:.0f} s", end="", flush=True)
    print("\n    Terminé. Relance la commande pour retenter les erreurs éventuelles.")


def load_labels() -> pd.DataFrame:
    labels = pd.read_json(LABELS, lines=True, dtype={"combo_id": str})
    return labels.drop_duplicates("combo_id", keep="last")


# --------------------------------------------------------------------------- 3. validate
def validate() -> None:
    """Crée le fichier à annoter, ou mesure l'accord LLM / humain s'il est rempli."""
    if not VALIDATION.exists():
        combos = pd.read_csv(COMBOS, dtype=str, keep_default_na=False)
        sample = combos.merge(load_labels(), on="combo_id").head(50)
        sample["mon_motif"] = ""
        sample[["combo_id", *KEYS, "mon_motif", "motif", "gravite", "resume"]].to_csv(
            VALIDATION, index=False, encoding="utf-8-sig")
        print(f"    Fichier créé : {VALIDATION}\n"
              f"    1. Ouvre-le dans Excel et masque les colonnes motif, gravite et resume (celles du LLM)\n"
              f"    2. Pour chaque ligne, écris TON motif dans mon_motif, parmi :\n"
              f"       {', '.join(MOTIFS)}\n"
              f"    3. Enregistre au format CSV, puis relance cette commande")
        return
    val = pd.read_csv(VALIDATION, dtype=str, encoding="utf-8-sig", sep=None, engine="python",
                      keep_default_na=False)
    val = val[val["mon_motif"].str.strip() != ""]
    if val.empty:
        print("    Colonne mon_motif encore vide : remplis-la puis relance.")
        return
    agree = val["mon_motif"].str.strip() == val["motif"].str.strip()
    print(f"    Accord LLM / humain : {agree.mean():.0%} sur {len(val)} combinaisons")
    if (~agree).any():
        print("    Désaccords :")
        print(val.loc[~agree, ["combo_id", "issue", "mon_motif", "motif"]].to_string(index=False))


# --------------------------------------------------------------------------- 4. report
def report() -> None:
    from creditlens.config import get_engine

    agg = pd.read_csv(AGG, dtype={"annee": int}, keep_default_na=False)
    labels = load_labels()[["combo_id", "motif", "gravite", "resume"]]
    df = agg.merge(labels, on="combo_id", how="left")
    df["motif"] = df["motif"].fillna("non_classe")
    df.to_sql("fct_complaints", get_engine(), schema="marts", if_exists="replace",
              index=False, chunksize=10_000, method="multi")

    total = int(df["nb"].sum())
    classed = df[df["motif"] != "non_classe"]
    coverage = 100 * classed["nb"].sum() / total

    def weighted(g: pd.DataFrame) -> pd.Series:
        return pd.Series({
            "nb": int(g["nb"].sum()),
            "part_pct": round(100 * g["nb"].sum() / classed["nb"].sum(), 1),
            "gravite_moyenne": round((g["gravite"] * g["nb"]).sum() / g["nb"].sum(), 2),
            "reponse_dans_les_delais_pct": round(100 * g["nb_dans_les_delais"].sum() / g["nb"].sum(), 1),
            "dedommagement_pct": round(100 * g["nb_dedommagement"].sum() / g["nb"].sum(), 1),
        })

    by_motif = (classed.groupby("motif")[["nb", "gravite", "nb_dans_les_delais", "nb_dedommagement"]]
                .apply(weighted).sort_values("nb", ascending=False).reset_index())
    by_motif["nb"] = by_motif["nb"].astype(int)
    yearly = classed.pivot_table(index="annee", columns="motif", values="nb", aggfunc="sum", fill_value=0)
    yearly_share = (100 * yearly.div(yearly.sum(axis=1), axis=0)).round(1)
    top_products = classed.groupby("product")["nb"].sum().nlargest(8).index
    by_product = classed[classed["product"].isin(top_products)].pivot_table(
        index="product", columns="motif", values="nb", aggfunc="sum", fill_value=0)
    by_product = (100 * by_product.div(by_product.sum(axis=1), axis=0)).round(1)
    grave = (classed[classed["gravite"] == 3].groupby(["motif", "issue", "resume"], as_index=False)["nb"]
             .sum().nlargest(8, "nb"))
    companies = pd.read_csv(COMPANIES).head(10)
    lab = load_labels()

    lines = [
        "# Réclamations clients : taxonomie normalisée par l'IA", "",
        f"**{total:,} réclamations** (base publique CFPB, {int(df['annee'].min())}–{int(df['annee'].max())}).",
        f"Un LLM local (`{lab['model'].iloc[0]}`, via Ollama) a rangé les {len(lab)} catégories de "
        f"réclamation les plus fréquentes dans 9 motifs métier : elles couvrent **{coverage:.1f} %** "
        "des réclamations.", "",
        "> Limite : depuis 2026 le CFPB ne publie plus le texte libre des réclamations. "
        "Le LLM classe donc les intitulés déclarés (produit, problème, détail), pas le récit du client.", "",
        "## Motifs de réclamation", "", by_motif.to_markdown(index=False), "",
        "## Évolution par année (part de chaque motif, en %)", "", yearly_share.to_markdown(), "",
        "## Nombre de réclamations par année", "",
        yearly.assign(total=yearly.sum(axis=1)).to_markdown(), "",
        "## Motifs par produit (% des réclamations du produit, 8 produits principaux)", "",
        by_product.to_markdown(), "",
        "## Catégories graves les plus fréquentes (gravité 3)", "",
        *[f"- **{r.motif}** — {r.issue} ({r.nb:,} réclamations) : {r.resume}" for r in grave.itertuples()], "",
        "## Les 10 établissements les plus visés", "", companies.to_markdown(index=False), "",
    ]
    (DOCS_DIR / "complaints_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(by_motif.to_string(index=False))
    print(f"\n    {coverage:.1f} % des {total:,} réclamations classées.")
    print("    Table marts.fct_complaints et docs/complaints_report.md écrits.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Réclamations clients : taxonomie normalisée par un LLM")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    c = sub.add_parser("classify")
    c.add_argument("--limit", type=int, help=f"nombre de combinaisons (défaut : {DEFAULT_TOP})")
    sub.add_parser("validate")
    sub.add_parser("report")
    args = parser.parse_args()
    {"prepare": prepare, "validate": validate, "report": report}.get(
        args.cmd, lambda: classify(args.limit))()


if __name__ == "__main__":
    main()
