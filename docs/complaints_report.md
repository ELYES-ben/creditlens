# Réclamations clients : taxonomie normalisée par l'IA

**19,080,438 réclamations** (base publique CFPB, 2011–2026).
Un LLM local (`qwen2.5:3b`, via Ollama) a rangé les 838 catégories de réclamation les plus fréquentes dans 9 motifs métier : elles couvrent **100.0 %** des réclamations.

> Limite : depuis 2026 le CFPB ne publie plus le texte libre des réclamations. Le LLM classe donc les intitulés déclarés (produit, problème, détail), pas le récit du client.

## Motifs de réclamation

| motif                    |       nb |   part_pct |   gravite_moyenne |   reponse_dans_les_delais_pct |   dedommagement_pct |
|:-------------------------|---------:|-----------:|------------------:|------------------------------:|--------------------:|
| rapport_credit           | 15957360 |       83.6 |              1.09 |                          99.8 |                 0.2 |
| recouvrement             |  1228792 |        6.4 |              1.91 |                          96.8 |                 0.5 |
| erreur_compte            |   931323 |        4.9 |              1    |                          98.6 |                13.1 |
| service_client           |   291687 |        1.5 |              1.02 |                          96.5 |                 5.6 |
| credit_refus_conditions  |   208212 |        1.1 |              1.35 |                          97.6 |                 4.4 |
| difficulte_remboursement |   205647 |        1.1 |              1.28 |                          95.4 |                 2.6 |
| frais                    |   155080 |        0.8 |              1.11 |                          97.4 |                22.1 |
| fraude                   |   100312 |        0.5 |              2.47 |                          97.5 |                 6.7 |
| autre                    |     1747 |        0   |              2.71 |                          96.9 |                13.7 |

## Évolution par année (part de chaque motif, en %)

|   annee |   autre |   credit_refus_conditions |   difficulte_remboursement |   erreur_compte |   frais |   fraude |   rapport_credit |   recouvrement |   service_client |
|--------:|--------:|--------------------------:|---------------------------:|----------------:|--------:|---------:|-----------------:|---------------:|-----------------:|
|    2011 |     0   |                      13.4 |                        1.5 |            18.7 |    15.4 |      6   |              6.5 |           29.1 |              9.3 |
|    2012 |     0.1 |                      12.4 |                        5.3 |            31.9 |     7.2 |      1.4 |              5.7 |           32.3 |              3.8 |
|    2013 |     0   |                       9.6 |                        3.8 |            26.1 |     4.1 |      1.4 |             14.6 |           34.4 |              6   |
|    2014 |     0.1 |                       7.2 |                        3   |            21.6 |     3.7 |      2.2 |             20.2 |           31.6 |             10.4 |
|    2015 |     0.1 |                       8.6 |                        3.1 |            22.3 |     3.7 |      3   |             21.6 |           27.8 |              9.8 |
|    2016 |     0.1 |                       8.8 |                        3.5 |            22.5 |     4.1 |      3.1 |             24.8 |           24.2 |              9   |
|    2017 |     0   |                       4.8 |                        8.4 |            15.6 |     3.8 |      1.7 |             41.7 |           17.7 |              6.3 |
|    2018 |     0   |                       3.2 |                        6.6 |            15.3 |     3.1 |      1.4 |             48.7 |           16.7 |              5   |
|    2019 |     0   |                       3.1 |                        5   |            14.3 |     2.7 |      1.5 |             54.8 |           14.3 |              4.3 |
|    2020 |     0   |                       2.7 |                        2.6 |            10.5 |     1.7 |      1.1 |             67.6 |           10.9 |              2.8 |
|    2021 |     0   |                       2.7 |                        2.3 |            10.5 |     1.5 |      1.6 |             65.3 |           13   |              3.1 |
|    2022 |     0   |                       1.6 |                        1.6 |             7.5 |     1.1 |      1.7 |             78   |            6.6 |              1.8 |
|    2023 |     0   |                       1.2 |                        1.4 |             5.9 |     1.1 |      0.9 |             83.1 |            4.7 |              1.8 |
|    2024 |     0   |                       0.7 |                        0.7 |             3.3 |     0.6 |      0.3 |             87.7 |            5.4 |              1.3 |
|    2025 |     0   |                       0.4 |                        0.5 |             3.4 |     0.4 |      0.3 |             89.1 |            4.9 |              0.9 |
|    2026 |     0   |                       0.4 |                        0.5 |             2.2 |     0.4 |      0.2 |             91.8 |            4   |              0.6 |

## Nombre de réclamations par année

|   annee |   autre |   credit_refus_conditions |   difficulte_remboursement |   erreur_compte |   frais |   fraude |   rapport_credit |   recouvrement |   service_client |   total |
|--------:|--------:|--------------------------:|---------------------------:|----------------:|--------:|---------:|-----------------:|---------------:|-----------------:|--------:|
|    2011 |       1 |                       339 |                         38 |             475 |     391 |      152 |              166 |            738 |              236 |    2536 |
|    2012 |      55 |                      8989 |                       3837 |           23095 |    5198 |      990 |             4101 |          23387 |             2716 |   72368 |
|    2013 |      52 |                     10391 |                       4122 |           28204 |    4433 |     1502 |            15783 |          37192 |             6535 |  108214 |
|    2014 |     119 |                     10960 |                       4625 |           33091 |    5596 |     3425 |            30845 |          48278 |            15969 |  152908 |
|    2015 |     138 |                     14439 |                       5213 |           37526 |    6184 |     5033 |            36382 |          46840 |            16517 |  168272 |
|    2016 |     177 |                     16752 |                       6761 |           42994 |    7911 |     5854 |            47418 |          46265 |            17160 |  191292 |
|    2017 |      73 |                     11584 |                      20341 |           37819 |    9158 |     4222 |           101199 |          43076 |            15272 |  242744 |
|    2018 |      41 |                      8179 |                      16853 |           39265 |    7982 |     3641 |           125209 |          42994 |            12961 |  257125 |
|    2019 |      70 |                      8592 |                      13784 |           39587 |    7539 |     4232 |           151849 |          39609 |            11971 |  277233 |
|    2020 |      78 |                     11966 |                      11496 |           46500 |    7730 |     4966 |           300332 |          48551 |            12586 |  444205 |
|    2021 |      73 |                     13346 |                      11159 |           51949 |    7627 |     7992 |           324059 |          64298 |            15429 |  495932 |
|    2022 |      77 |                     12694 |                      13069 |           60112 |    9079 |    13412 |           624142 |          53053 |            14601 |  800239 |
|    2023 |     134 |                     15122 |                      17685 |           76106 |   13641 |    11788 |          1073267 |          60782 |            23515 | 1292040 |
|    2024 |     175 |                     18492 |                      19582 |           90338 |   16058 |     7818 |          2398386 |         146593 |            36727 | 2734169 |
|    2025 |     237 |                     23420 |                      27027 |          185209 |   23075 |    13667 |          4851039 |         269130 |            50048 | 5442852 |
|    2026 |     247 |                     22947 |                      30055 |          139053 |   23478 |    11618 |          5873183 |         258006 |            39444 | 6398031 |

## Motifs par produit (% des réclamations du produit, 8 produits principaux)

| product                                                                      |   autre |   credit_refus_conditions |   difficulte_remboursement |   erreur_compte |   frais |   fraude |   rapport_credit |   recouvrement |   service_client |
|:-----------------------------------------------------------------------------|--------:|--------------------------:|---------------------------:|----------------:|--------:|---------:|-----------------:|---------------:|-----------------:|
| Checking or savings account                                                  |     0   |                       0   |                        0   |            89.9 |     5.4 |      1.7 |              0.5 |            0   |              2.5 |
| Credit card                                                                  |     0.2 |                      10.4 |                        1.9 |            26.2 |    14.3 |      2.8 |             20.1 |            0.5 |             23.5 |
| Credit card or prepaid card                                                  |     0.2 |                       4.6 |                        1.8 |            28   |    11.5 |      5.9 |             35.2 |            0   |             12.8 |
| Credit reporting or other personal consumer reports                          |     0   |                       0   |                        0   |             0   |     0   |      0   |            100   |            0   |              0   |
| Credit reporting, credit repair services, or other personal consumer reports |     0   |                       0   |                        0   |             0   |     0   |      0   |            100   |            0   |              0   |
| Debt collection                                                              |     0   |                       0   |                        0   |             0   |     0   |      1   |              0.4 |           89.9 |              8.7 |
| Money transfer, virtual currency, or money service                           |     0   |                       0   |                        0   |            58.9 |     4.9 |     24.7 |              0   |            0   |             11.5 |
| Mortgage                                                                     |     0   |                      16.6 |                       14.4 |            38.8 |     0.7 |      0   |              3   |           24.1 |              2.4 |

## Catégories graves les plus fréquentes (gravité 3)

- **recouvrement** — Took or threatened to take negative or legal action (118,412 réclamations) : Threats of negative action on credit, potentiellement causant une perte d'argent significative
- **fraude** — Getting a credit card (12,008 réclamations) : Crédit ou carte prépayée ouverte suite à fraude ou usurpation d'identité, potentiellement causant des préjudices graves
- **recouvrement** — Took or threatened to take negative or legal action (11,585 réclamations) : Threat to sue pour une dette très ancienne
- **fraude** — Identity theft / Fraud / Embezzlement (8,480 réclamations) : Fraude ou usurpation d'identité, risque de perte de biens immobiliers
- **recouvrement** — Took or threatened to take negative or legal action (7,808 réclamations) : Menaces de poursuite judiciaire sans notification préalable
- **fraude** — Opening an account (6,673 réclamations) : Fraudulent account opening led to identity theft and financial loss
- **fraude** — False statements or representation (6,523 réclamations) : Réclamation concernant des allégations de fraude impliquant des personnes imposées comme avocat, officier de police ou agent gouvernemental
- **recouvrement** — Took or threatened to take negative or legal action (5,416 réclamations) : Menaces ou saisie immobilière de la part de la banque

## Les 10 établissements les plus visés

| company                                |      nb |
|:---------------------------------------|--------:|
| TRANSUNION INTERMEDIATE HOLDINGS, INC. | 5278795 |
| EQUIFAX, INC.                          | 5071653 |
| Experian Information Solutions Inc.    | 4718920 |
| BANK OF AMERICA, NATIONAL ASSOCIATION  |  190572 |
| JPMORGAN CHASE & CO.                   |  179984 |
| WELLS FARGO & COMPANY                  |  178230 |
| CAPITAL ONE FINANCIAL CORPORATION      |  177678 |
| CITIBANK, N.A.                         |  145506 |
| SYNCHRONY FINANCIAL                    |   86106 |
| Resurgent Capital Services L.P.        |   74753 |
