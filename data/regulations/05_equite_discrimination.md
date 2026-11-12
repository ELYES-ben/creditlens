# Équité et non-discrimination dans le scoring de crédit

## Caractéristiques protégées
En France et dans l'Union européenne, il est interdit de refuser un crédit sur la base de caractéristiques protégées : sexe, âge, origine, religion, état de santé, situation de famille, etc. Ces variables ne doivent pas servir de critère de décision.

## Discrimination directe et indirecte
- **Discrimination directe** : utiliser explicitement une caractéristique protégée (par exemple refuser les femmes). Interdit.
- **Discrimination indirecte** : utiliser une variable apparemment neutre mais fortement corrélée à une caractéristique protégée, ce qui produit le même effet. À surveiller.

## Mesures d'équité
Pour vérifier qu'un modèle de scoring est équitable, on compare, entre les groupes (par exemple femmes et hommes) :
- le **taux de sélection** ou de refus (demographic parity) ;
- le **taux de vrais positifs** et de faux positifs (equalized odds) ;
- la **performance du modèle** (AUC) dans chaque groupe.

Un écart de taux de refus entre deux groupes n'est pas nécessairement une discrimination : il peut refléter une différence réelle de risque. Ce qui compte, c'est que le modèle soit aussi juste et aussi précis pour chaque groupe, et qu'il n'utilise pas la caractéristique protégée comme critère.

## Lien avec CreditLens
Le modèle n'utilise pas le sexe comme variable. Le contrôle d'équité compare les taux de défaut réels, les probabilités prédites et l'AUC par sexe et par tranche d'âge, pour détecter un éventuel traitement injuste.

Source : principes de non-discrimination (droit français et européen), littérature sur l'équité algorithmique (fairness).
