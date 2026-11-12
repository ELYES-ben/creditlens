# IFRS 9 — provisionnement des pertes de crédit attendues

IFRS 9 est la norme comptable internationale qui régit le provisionnement du risque de crédit depuis 2018. Elle remplace IAS 39 et impose de provisionner les pertes **attendues** (et non plus seulement les pertes avérées).

## Les trois stages (étapes)
IFRS 9 classe chaque crédit en trois stages selon la dégradation de son risque depuis l'octroi :
- **Stage 1** : crédit sain, risque non dégradé. On provisionne la perte attendue à **12 mois**.
- **Stage 2** : augmentation significative du risque de crédit depuis l'origine (par exemple une forte hausse de la PD). On provisionne la perte attendue sur **toute la durée de vie** du crédit (lifetime).
- **Stage 3** : crédit en défaut. On provisionne la perte attendue à maturité, calculée sur l'encours net.

## Perte de crédit attendue (ECL)
La perte de crédit attendue (Expected Credit Loss) combine la probabilité de défaut (PD), la perte en cas de défaut (LGD) et l'exposition (EAD), pondérées par plusieurs scénarios économiques (forward-looking). C'est une différence majeure avec Bâle : IFRS 9 exige d'intégrer des prévisions macroéconomiques.

## Lien avec le scoring
Un modèle de probabilité de défaut, comme celui de CreditLens, fournit la PD utilisée pour classer les crédits en stages et calculer les provisions. La qualité de calibrage du modèle (la PD prédite doit correspondre au défaut réellement observé) est donc essentielle.

Source : IFRS Foundation, « IFRS 9 Financial Instruments », project summary, ifrs.org.
