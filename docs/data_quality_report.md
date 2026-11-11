# Rapport qualité des données — CreditLens

Généré le 11/11/2026 sur le schéma `raw`.

## 1. Volumétrie

| Table | Lignes | Colonnes |
|---|---:|---:|
| application_test | 48 744 | 121 |
| application_train | 307 511 | 122 |
| bureau | 1 716 428 | 17 |
| bureau_balance | 27 299 925 | 3 |
| credit_card_balance | 3 840 312 | 23 |
| homecredit_columns_description | 219 | 5 |
| installments_payments | 13 605 401 | 8 |
| pos_cash_balance | 10 001 358 | 8 |
| previous_application | 1 670 214 | 37 |

## 2. Unicité des identifiants

| Table | Clé | Doublons |
|---|---|---:|
| application_train | sk_id_curr | 0 |
| bureau | sk_id_bureau | 0 |
| previous_application | sk_id_prev | 0 |

## 3. Intégrité : clients inconnus dans les tables liées

Lignes dont `sk_id_curr` n'existe pas dans `application_train` (normal en partie : Home Credit sépare les clients en train et test).

| Table | Lignes orphelines | Part |
|---|---:|---:|
| bureau | 251 103 | 14.63 % |
| previous_application | 256 513 | 15.36 % |
| installments_payments | 2 013 809 | 14.80 % |

## 4. Valeurs manquantes (application_train)

67 colonnes sur 122 ont des valeurs manquantes ; 41 en ont plus de 50 %.

| Colonne | Manquants | Part |
|---|---:|---:|
| commonarea_avg | 214 865 | 69.87 % |
| commonarea_mode | 214 865 | 69.87 % |
| commonarea_medi | 214 865 | 69.87 % |
| nonlivingapartments_avg | 213 514 | 69.43 % |
| nonlivingapartments_mode | 213 514 | 69.43 % |
| nonlivingapartments_medi | 213 514 | 69.43 % |
| fondkapremont_mode | 210 295 | 68.39 % |
| livingapartments_avg | 210 199 | 68.35 % |
| livingapartments_mode | 210 199 | 68.35 % |
| livingapartments_medi | 210 199 | 68.35 % |
| floorsmin_avg | 208 642 | 67.85 % |
| floorsmin_mode | 208 642 | 67.85 % |
| floorsmin_medi | 208 642 | 67.85 % |
| years_build_avg | 204 488 | 66.50 % |
| years_build_mode | 204 488 | 66.50 % |
| years_build_medi | 204 488 | 66.50 % |
| own_car_age | 202 929 | 65.99 % |
| landarea_avg | 182 590 | 59.38 % |
| landarea_mode | 182 590 | 59.38 % |
| landarea_medi | 182 590 | 59.38 % |
| basementarea_avg | 179 943 | 58.52 % |
| basementarea_mode | 179 943 | 58.52 % |
| basementarea_medi | 179 943 | 58.52 % |
| ext_source_1 | 173 378 | 56.38 % |
| nonlivingarea_avg | 169 682 | 55.18 % |

## 5. Anomalies métier

| Anomalie | Lignes | Part | Décision |
|---|---:|---:|---|
| DAYS_EMPLOYED = 365243 (code « sans emploi / retraité ») | 55 374 | 18.01 % | Remplacé par NULL + colonne `no_employment_flag` |
| CODE_GENDER = 'XNA' (sexe inconnu) | 4 | 0.00 % | Remplacé par NULL |
| ORGANIZATION_TYPE = 'XNA' | 55 374 | 18.01 % | Remplacé par NULL (mêmes clients que 365243) |
| NAME_FAMILY_STATUS = 'Unknown' | 2 | 0.00 % | Remplacé par NULL |
| Revenu > 10 M (valeur aberrante) | 3 | 0.00 % | Conservé, signalé par `income_outlier_flag` |
| Âge hors de 18-75 ans | 0 | 0.00 % | À vérifier si > 0 |
| AMT_ANNUITY manquant | 12 | 0.00 % | Ratios financiers à NULL pour ces clients |
