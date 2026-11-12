# Définitions : PD, LGD, EAD et perte attendue

## Probabilité de défaut (PD)
La PD est la probabilité qu'un emprunteur ne respecte pas ses obligations de remboursement sur un horizon donné, généralement 12 mois. Elle est comprise entre 0 et 1 (ou 0 % et 100 %). Un modèle de scoring estime la PD de chaque client à partir de ses caractéristiques.

## Perte en cas de défaut (LGD)
La LGD (Loss Given Default) est la part de l'exposition que la banque perd effectivement lorsqu'un client fait défaut, une fois pris en compte le recouvrement (vente de garanties, procédures). Une LGD de 45 % signifie que, sur 100 euros dus, la banque en récupère 55 et en perd 45. Pour un crédit non garanti, la LGD est élevée ; pour un crédit immobilier garanti par le bien, elle est plus faible.

## Exposition au moment du défaut (EAD)
L'EAD (Exposure At Default) est le montant que le client doit encore au moment où il fait défaut. Pour un prêt amortissable, c'est le capital restant dû. Pour une ligne de crédit renouvelable, on y ajoute une estimation du tirage supplémentaire avant le défaut.

## Perte attendue (EL)
La perte attendue combine les trois :

EL = PD × LGD × EAD

Exemple : PD = 8 %, LGD = 45 %, EAD = 15 000 € donne EL = 0,08 × 0,45 × 15 000 = 540 €. La banque prévoit donc, en moyenne, de perdre 540 € sur ce crédit, et provisionne ce montant.

## Indice de Gini et AUC
La qualité d'un modèle de PD se mesure par l'**AUC** (aire sous la courbe ROC), comprise entre 0,5 (hasard) et 1 (parfait), ou par l'**indice de Gini** = 2 × AUC − 1. Un bon modèle de crédit de détail a généralement un Gini entre 0,4 et 0,6.

Source : définitions standard du risque de crédit (Bâle III, documentation prudentielle).
