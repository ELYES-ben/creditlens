"""Détection de fraude sur transactions par carte (jeu ULB / Kaggle « creditcardfraud »).

Données : data/raw/creditcard.csv — 284 807 transactions sur 2 jours, dont ~0,17 % de fraudes.
  Time   : secondes depuis la 1re transaction
  V1-V28 : variables anonymisées (déjà transformées par la banque, ACP)
  Amount : montant
  Class  : 1 = fraude

Deux approches comparées :
  1. Isolation Forest (NON supervisé) : repère les transactions « bizarres »
     sans connaître les fraudes à l'avance
  2. LightGBM (supervisé) : apprend à partir des fraudes connues

Découpage chronologique : on apprend sur les 80 % premières transactions et on teste
sur les 20 % suivantes (comme en vrai : on prédit le futur avec le passé).

Mesure : PR-AUC (précision-rappel). Avec 0,17 % de fraudes, l'exactitude ne veut rien
dire : un modèle qui dit « jamais de fraude » aurait 99,8 % d'exactitude.

Utilisation :  python -m creditlens.fraud.detect_fraud
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score

from creditlens.config import DOCS_DIR, RAW_DIR

SEED = 42
ALERT_BUDGETS = (0.001, 0.005, 0.01)   # part des transactions envoyées aux analystes


def load() -> pd.DataFrame:
    path = RAW_DIR / "creditcard.csv"
    if not path.exists():
        raise SystemExit(f"Fichier introuvable : {path}\n"
                         "Télécharge-le sur kaggle.com/datasets/mlg-ulb/creditcardfraud")
    return pd.read_csv(path).sort_values("Time").reset_index(drop=True)


def time_split(df: pd.DataFrame, share: float = 0.8):
    cut = int(len(df) * share)
    return df.iloc[:cut], df.iloc[cut:]


def features(df: pd.DataFrame) -> pd.DataFrame:
    X = df.drop(columns=["Class"]).copy()
    X["log_amount"] = np.log1p(X["Amount"])
    X["hour"] = (X["Time"] // 3600) % 24          # heure de la journée
    return X.drop(columns=["Time"])


def alert_table(y: np.ndarray, score: np.ndarray, amount: np.ndarray) -> list[dict]:
    """Si les analystes vérifient les X % de transactions les plus suspectes :
    quelle part des fraudes (en nombre et en montant) est attrapée ?"""
    order = np.argsort(-score)
    rows = []
    for budget in ALERT_BUDGETS:
        k = max(1, int(len(score) * budget))
        top = order[:k]
        caught = y[top] == 1
        rows.append({
            "alertes_pct": round(100 * budget, 1),
            "nb_alertes": k,
            "fraudes_attrapees": int(caught.sum()),
            "rappel_pct": round(100 * caught.sum() / max(y.sum(), 1), 1),
            "precision_pct": round(100 * caught.mean(), 1),
            "montant_fraude_attrape_pct": round(
                100 * amount[top][caught].sum() / max(amount[y == 1].sum(), 1e-9), 1),
        })
    return rows


def main() -> None:
    print("1/4 Lecture de creditcard.csv ...")
    df = load()
    train, test = time_split(df)
    X_train, X_test = features(train), features(test)
    y_train, y_test = train["Class"].to_numpy(), test["Class"].to_numpy()
    amount_test = test["Amount"].to_numpy()
    print(f"    {len(df):,} transactions | {int(df['Class'].sum())} fraudes "
          f"({100 * df['Class'].mean():.3f} %) | test : {int(y_test.sum())} fraudes")

    print("2/4 Isolation Forest (non supervisé) ...")
    iso = IsolationForest(n_estimators=300, contamination="auto", random_state=SEED, n_jobs=-1)
    iso.fit(X_train)
    iso_score = -iso.score_samples(X_test)       # plus c'est haut, plus c'est anormal
    iso_res = {"pr_auc": round(float(average_precision_score(y_test, iso_score)), 4),
               "roc_auc": round(float(roc_auc_score(y_test, iso_score)), 4)}
    print(f"    PR-AUC = {iso_res['pr_auc']:.3f} | ROC-AUC = {iso_res['roc_auc']:.3f}")

    print("3/4 LightGBM (supervisé) ...")
    import lightgbm as lgb
    cut = int(len(X_train) * 0.85)                # validation = fin de la période d'apprentissage
    model = lgb.LGBMClassifier(
        n_estimators=2000, learning_rate=0.02, num_leaves=31, min_child_samples=50,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.7,
        scale_pos_weight=5, random_state=SEED, verbose=-1,
    )
    model.fit(X_train.iloc[:cut], y_train[:cut],
              eval_set=[(X_train.iloc[cut:], y_train[cut:])], eval_metric="average_precision",
              callbacks=[lgb.early_stopping(200, verbose=False)])
    lgb_score = model.predict_proba(X_test)[:, 1]
    lgb_res = {"pr_auc": round(float(average_precision_score(y_test, lgb_score)), 4),
               "roc_auc": round(float(roc_auc_score(y_test, lgb_score)), 4),
               "nb_arbres": int(model.best_iteration_ or model.n_estimators)}
    print(f"    PR-AUC = {lgb_res['pr_auc']:.3f} | ROC-AUC = {lgb_res['roc_auc']:.3f}")

    print("4/4 Impact opérationnel (alertes envoyées aux analystes) ...")
    alerts_iso = alert_table(y_test, iso_score, amount_test)
    alerts_lgb = alert_table(y_test, lgb_score, amount_test)
    print("    LightGBM :")
    print(pd.DataFrame(alerts_lgb).to_string(index=False))
    print("    Isolation Forest :")
    print(pd.DataFrame(alerts_iso).to_string(index=False))

    importance = (pd.DataFrame({"variable": X_train.columns,
                                "importance": model.booster_.feature_importance("gain")})
                  .sort_values("importance", ascending=False).head(10))
    baseline = float(y_test.mean())
    results = {"nb_transactions": int(len(df)), "nb_fraudes": int(df["Class"].sum()),
               "taux_fraude_test_pct": round(100 * baseline, 3),
               "pr_auc_hasard": round(baseline, 4),
               "isolation_forest": iso_res, "lightgbm": lgb_res,
               "alertes_lightgbm": alerts_lgb, "alertes_isolation_forest": alerts_iso}
    (DOCS_DIR / "fraud_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False),
                                                 encoding="utf-8")
    report = [
        "# Détection de fraude — résultats", "",
        f"{len(df):,} transactions, {int(df['Class'].sum())} fraudes. "
        "Apprentissage sur les 80 % premières transactions, test sur les 20 % suivantes.", "",
        "| Modèle | Type | PR-AUC | ROC-AUC |", "|---|---|---:|---:|",
        f"| Hasard | — | {baseline:.4f} | 0.5 |",
        f"| Isolation Forest | non supervisé | {iso_res['pr_auc']:.3f} | {iso_res['roc_auc']:.3f} |",
        f"| LightGBM | supervisé | {lgb_res['pr_auc']:.3f} | {lgb_res['roc_auc']:.3f} |", "",
        "## Si les analystes vérifient les transactions les plus suspectes (LightGBM)", "",
        pd.DataFrame(alerts_lgb).to_markdown(index=False), "",
        "## Même chose avec Isolation Forest", "",
        pd.DataFrame(alerts_iso).to_markdown(index=False), "",
        "## Variables les plus utiles (LightGBM)", "",
        importance.to_markdown(index=False, floatfmt=".0f"), "",
    ]
    (DOCS_DIR / "fraud_report.md").write_text("\n".join(report), encoding="utf-8")
    print("Terminé : docs/fraud_report.md, docs/fraud_results.json")


if __name__ == "__main__":
    main()
