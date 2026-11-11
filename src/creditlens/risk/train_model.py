"""Modèle de scoring : probabilité de défaut (PD) de chaque client.

Étapes :
  1. lit marts.client_features
  2. sépare 80 % entraînement / 20 % test (même proportion de défauts)
  3. entraîne une régression logistique (référence) puis un LightGBM
  4. compare AUC et Gini, choisit le seuil d'acceptation par le coût des erreurs
  5. explique le modèle avec SHAP (graphique + 3 clients)
  6. contrôle l'équité (sexe, âge) — le sexe n'est PAS utilisé par le modèle
  7. écrit les scores dans marts.client_scores et les résultats dans docs/

Utilisation :  python -m creditlens.risk.train_model
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from creditlens.config import DOCS_DIR, PROJECT_ROOT

SEED = 42
TARGET = "is_default"
ID = "client_id"

# Variables exclues du modèle :
#  - gender : interdit comme critère d'octroi (discrimination) -> utilisé SEULEMENT
#    pour contrôler l'équité à la fin
EXCLUDED = {TARGET, ID, "gender"}
CATEGORICAL = [
    "contract_type", "income_type", "education", "family_status",
    "housing_type", "occupation", "organization_type",
]

# Hypothèses pour le choix du seuil (à citer en entretien)
COST_ACCEPT_BAD = 0.45   # accepter un mauvais client : on perd la LGD (45 % du montant)
COST_REFUSE_GOOD = 0.10  # refuser un bon client : on perd la marge (≈ 10 % du montant)

FIG_DIR = DOCS_DIR / "figures"
MODEL_DIR = PROJECT_ROOT / "models"


# --------------------------------------------------------------------------- données
def load_features() -> pd.DataFrame:
    from creditlens.config import get_engine

    df = pd.read_sql("SELECT * FROM marts.client_features", get_engine())
    # PostgreSQL renvoie les NUMERIC comme des objets Decimal : on les convertit en nombres
    text_cols = set(CATEGORICAL) | {"gender"}
    for col in df.columns:
        if col not in text_cols:
            df[col] = pd.to_numeric(df[col].astype("object"), errors="coerce").astype(float)
    df[ID] = df[ID].astype("int64")
    df[TARGET] = df[TARGET].astype(int)
    return df


def split_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    features = [c for c in df.columns if c not in EXCLUDED]
    categorical = [c for c in CATEGORICAL if c in features]
    numeric = [c for c in features if c not in categorical]
    return numeric, categorical


# --------------------------------------------------------------------------- modèles
def train_logistic(X_train, y_train, numeric, categorical) -> Pipeline:
    """Régression logistique : simple, explicable, standard en banque."""
    prep = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                          ("scale", StandardScaler())]), numeric),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="constant", fill_value="Inconnu")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=100))]),
         categorical),
    ])
    model = Pipeline([("prep", prep), ("clf", LogisticRegression(max_iter=2000))])
    model.fit(X_train, y_train)
    return model


def to_lgbm_frame(X: pd.DataFrame, categorical: list[str]) -> pd.DataFrame:
    """LightGBM sait gérer directement les catégories et les valeurs manquantes."""
    X = X.copy()
    for c in categorical:
        X[c] = X[c].astype("category")
    return X


def train_lightgbm(X_train, y_train, categorical):
    """LightGBM : des centaines de petits arbres de décision combinés."""
    import lightgbm as lgb

    X_fit, X_val, y_fit, y_val = train_test_split(
        X_train, y_train, test_size=0.1, stratify=y_train, random_state=SEED)
    model = lgb.LGBMClassifier(
        n_estimators=2000, learning_rate=0.03, num_leaves=31, min_child_samples=100,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=1.0,
        random_state=SEED, verbose=-1,
    )
    model.fit(
        to_lgbm_frame(X_fit, categorical), y_fit,
        eval_set=[(to_lgbm_frame(X_val, categorical), y_val)], eval_metric="auc",
        callbacks=[lgb.early_stopping(100, verbose=False)],
    )
    return model


def gini(auc: float) -> float:
    return 2 * auc - 1


# --------------------------------------------------------------------------- seuil
def choose_threshold() -> float:
    """Seuil de refus qui minimise le coût attendu des erreurs.

    On refuse si  PD × coût(accepter un mauvais) > (1 − PD) × coût(refuser un bon)
    soit          PD > C_bon / (C_bon + C_mauvais)
    """
    return COST_REFUSE_GOOD / (COST_REFUSE_GOOD + COST_ACCEPT_BAD)


def decision_stats(y_true: np.ndarray, pd_score: np.ndarray, threshold: float) -> dict:
    refused = pd_score > threshold
    accepted = ~refused
    return {
        "taux_refus_pct": round(float(100 * refused.mean()), 1),
        "defauts_evites_pct": round(float(100 * (refused & (y_true == 1)).sum() / max(y_true.sum(), 1)), 1),
        "bons_clients_refuses_pct": round(float(100 * (refused & (y_true == 0)).sum() / max((y_true == 0).sum(), 1)), 1),
        "taux_defaut_acceptes_pct": round(float(100 * y_true[accepted].mean()), 2) if accepted.any() else None,
    }


# --------------------------------------------------------------------------- équité
def age_band(age: pd.Series) -> pd.Series:
    return pd.cut(age, [0, 30, 45, 60, 200], labels=["< 30 ans", "30-44 ans", "45-59 ans", "60 ans +"],
                  right=False).astype(str)


def fairness_table(groups: pd.Series, y_true: np.ndarray, pd_score: np.ndarray,
                   threshold: float) -> pd.DataFrame:
    """Pour chaque groupe : taux de défaut réel, taux de refus, qualité du modèle."""
    rows = []
    for g in sorted(groups.dropna().unique()):
        m = (groups == g).to_numpy()
        y, s = y_true[m], pd_score[m]
        rows.append({
            "groupe": g,
            "nb_clients": int(m.sum()),
            "taux_defaut_reel_pct": round(100 * y.mean(), 2),
            "pd_moyenne_pct": round(100 * s.mean(), 2),
            "taux_refus_pct": round(100 * (s > threshold).mean(), 1),
            "auc": round(roc_auc_score(y, s), 3) if 0 < y.sum() < len(y) else None,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- SHAP
def explain_with_shap(model, X_test_lgbm: pd.DataFrame, y_test, pd_test) -> tuple[pd.DataFrame, str]:
    """Importance globale des variables + explication de 3 clients."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap

    sample = X_test_lgbm.sample(min(5000, len(X_test_lgbm)), random_state=SEED)
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(sample)
    if isinstance(values, list):          # anciennes versions : une matrice par classe
        values = values[1]

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    shap.summary_plot(values, sample, show=False, max_display=15)
    plt.title("Variables qui font monter (rouge) ou baisser (bleu) le risque")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "shap_summary.png", dpi=150)
    plt.close()

    importance = (pd.DataFrame({"variable": sample.columns,
                                "impact_moyen": np.abs(values).mean(axis=0)})
                  .sort_values("impact_moyen", ascending=False).head(15)
                  .reset_index(drop=True))

    # 3 clients : risque faible, moyen, élevé
    order = np.argsort(pd_test)
    picks = {"faible": order[len(order) // 20], "moyen": order[len(order) // 2],
             "élevé": order[-len(order) // 50]}
    lines = []
    for label, pos in picks.items():
        row = X_test_lgbm.iloc[[pos]]
        contrib = explainer.shap_values(row)
        contrib = (contrib[1] if isinstance(contrib, list) else contrib)[0]
        top = np.argsort(-np.abs(contrib))[:3]
        lines.append(f"### Client à risque {label} : PD = {100 * pd_test[pos]:.1f} % "
                     f"(défaut réel : {'oui' if y_test[pos] == 1 else 'non'})")
        for j in top:
            sens = "augmente" if contrib[j] > 0 else "diminue"
            lines.append(f"- `{row.columns[j]}` = {row.iloc[0, j]} → {sens} le risque")
        lines.append("")
    return importance, "\n".join(lines)


# --------------------------------------------------------------------------- main
def main() -> None:
    print("1/7 Lecture de marts.client_features ...")
    df = load_features()
    numeric, categorical = split_columns(df)
    features = numeric + categorical
    print(f"    {len(df):,} clients, {len(features)} variables, {100 * df[TARGET].mean():.2f} % de défauts")

    print("2/7 Découpage 80 % entraînement / 20 % test ...")
    train_idx, test_idx = train_test_split(df.index, test_size=0.2, stratify=df[TARGET], random_state=SEED)
    X_train, X_test = df.loc[train_idx, features], df.loc[test_idx, features]
    y_train, y_test = df.loc[train_idx, TARGET].to_numpy(), df.loc[test_idx, TARGET].to_numpy()

    print("3/7 Régression logistique ...")
    logit = train_logistic(X_train, y_train, numeric, categorical)
    auc_logit = roc_auc_score(y_test, logit.predict_proba(X_test)[:, 1])
    print(f"    AUC = {auc_logit:.3f} | Gini = {gini(auc_logit):.3f}")

    print("4/7 LightGBM ...")
    lgbm = train_lightgbm(X_train, y_train, categorical)
    X_test_lgbm = to_lgbm_frame(X_test, categorical)
    pd_test = lgbm.predict_proba(X_test_lgbm)[:, 1]
    auc_lgbm = roc_auc_score(y_test, pd_test)
    print(f"    AUC = {auc_lgbm:.3f} | Gini = {gini(auc_lgbm):.3f} | {lgbm.best_iteration_} arbres")

    threshold = choose_threshold()
    decisions = decision_stats(y_test, pd_test, threshold)
    print(f"    Seuil de refus : PD > {100 * threshold:.1f} % -> {decisions}")

    print("5/7 Explication SHAP ...")
    importance, examples = explain_with_shap(lgbm, X_test_lgbm, y_test, pd_test)
    print(importance.head(10).to_string(index=False))

    print("6/7 Contrôle d'équité ...")
    test_df = df.loc[test_idx]
    fair_gender = fairness_table(test_df["gender"].reset_index(drop=True), y_test, pd_test, threshold)
    fair_age = fairness_table(age_band(test_df["age_years"]).reset_index(drop=True), y_test, pd_test, threshold)
    print(fair_gender.to_string(index=False))
    print(fair_age.to_string(index=False))

    print("7/7 Écriture des scores et des résultats ...")
    pd_all = lgbm.predict_proba(to_lgbm_frame(df[features], categorical))[:, 1]
    scores = pd.DataFrame({ID: df[ID], "pd": pd_all.round(6),
                           "in_test_set": df.index.isin(test_idx)})
    from creditlens.config import get_engine
    scores.to_sql("client_scores", get_engine(), schema="marts", if_exists="replace",
                  index=False, chunksize=20_000, method="multi")

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump({"model": lgbm, "features": features, "categorical": categorical,
                 "threshold": threshold}, MODEL_DIR / "pd_model.pkl")

    results = {
        "nb_clients": int(len(df)), "nb_variables": len(features),
        "taux_defaut_pct": round(float(100 * df[TARGET].mean()), 2),
        "logistic": {"auc": round(float(auc_logit), 4), "gini": round(float(gini(auc_logit)), 4)},
        "lightgbm": {"auc": round(float(auc_lgbm), 4), "gini": round(float(gini(auc_lgbm)), 4),
                     "nb_arbres": int(lgbm.best_iteration_)},
        "seuil_refus_pd": round(threshold, 4),
        "hypotheses_cout": {"accepter_un_mauvais": COST_ACCEPT_BAD, "refuser_un_bon": COST_REFUSE_GOOD},
        "decisions_test": decisions,
    }
    (DOCS_DIR / "model_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False),
                                                 encoding="utf-8")
    report = [
        "# Modèle de scoring — résultats", "",
        "| Modèle | AUC | Gini |", "|---|---:|---:|",
        f"| Régression logistique | {auc_logit:.3f} | {gini(auc_logit):.3f} |",
        f"| LightGBM | {auc_lgbm:.3f} | {gini(auc_lgbm):.3f} |", "",
        f"**Seuil de refus :** PD > {100 * threshold:.1f} % "
        f"(coût d'un mauvais client accepté = {COST_ACCEPT_BAD:.0%} du montant, "
        f"coût d'un bon client refusé = {COST_REFUSE_GOOD:.0%}).", "",
        "| Indicateur (jeu de test) | Valeur |", "|---|---:|",
        *[f"| {k} | {v} |" for k, v in decisions.items()], "",
        "## Variables les plus importantes (SHAP)", "",
        "![SHAP](figures/shap_summary.png)", "",
        importance.to_markdown(index=False, floatfmt=".4f"), "",
        "## Explication de 3 clients", "", examples,
        "## Contrôle d'équité (le sexe n'est pas une variable du modèle)", "",
        "### Par sexe", "", fair_gender.to_markdown(index=False), "",
        "### Par âge", "", fair_age.to_markdown(index=False), "",
    ]
    (DOCS_DIR / "model_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Terminé : docs/model_report.md, docs/model_results.json, docs/figures/shap_summary.png, "
          "marts.client_scores")


if __name__ == "__main__":
    main()
