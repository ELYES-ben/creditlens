# Détection de fraude — résultats

284,807 transactions, 492 fraudes. Apprentissage sur les 80 % premières transactions, test sur les 20 % suivantes.

| Modèle | Type | PR-AUC | ROC-AUC |
|---|---|---:|---:|
| Hasard | — | 0.0013 | 0.5 |
| Isolation Forest | non supervisé | 0.042 | 0.950 |
| LightGBM | supervisé | 0.775 | 0.983 |

## Si les analystes vérifient les transactions les plus suspectes (LightGBM)

|   alertes_pct |   nb_alertes |   fraudes_attrapees |   rappel_pct |   precision_pct |   montant_fraude_attrape_pct |
|--------------:|-------------:|--------------------:|-------------:|----------------:|-----------------------------:|
|           0.1 |           56 |                  53 |         70.7 |            94.6 |                         51.5 |
|           0.5 |          284 |                  64 |         85.3 |            22.5 |                         82.1 |
|           1   |          569 |                  65 |         86.7 |            11.4 |                         82.2 |

## Même chose avec Isolation Forest

|   alertes_pct |   nb_alertes |   fraudes_attrapees |   rappel_pct |   precision_pct |   montant_fraude_attrape_pct |
|--------------:|-------------:|--------------------:|-------------:|----------------:|-----------------------------:|
|           0.1 |           56 |                   0 |          0   |             0   |                          0   |
|           0.5 |          284 |                  16 |         21.3 |             5.6 |                         27.6 |
|           1   |          569 |                  36 |         48   |             6.3 |                         50.6 |

## Variables les plus utiles (LightGBM)

| variable   |   importance |
|:-----------|-------------:|
| V17        |       439881 |
| V12        |       145671 |
| V10        |        23379 |
| V4         |         9927 |
| V1         |         9023 |
| V8         |         7503 |
| V13        |         6280 |
| V14        |         6078 |
| V7         |         5092 |
| Amount     |         4844 |
