# Évaluation de l'agent text-to-SQL

**Fiabilité : 100 %** — 30 réponses correctes sur 30 questions-tests, avec le modèle local `qwen2.5:3b`.

Méthode : pour chaque question, le résultat de l'agent est comparé à celui d'une requête SQL de référence écrite à la main. Les chiffres attendus sont recalculés à chaque exécution (jamais écrits en dur).

| # | Question | Résultat |
|---|---|---|
| q01 | Combien de clients y a-t-il dans le portefeuille ? | ✅ |
| q02 | Quel est le taux de défaut global du portefeuille, en pourcentage ? | ✅ |
| q03 | Combien de clients ont fait défaut ? | ✅ |
| q04 | Combien de clients y a-t-il dans chaque classe de risque ? | ✅ |
| q05 | Quel est le taux de défaut des clients de moins de 30 ans, en pourcentage ? | ✅ |
| q06 | Quel est le revenu moyen des clients ? | ✅ |
| q07 | Combien y a-t-il de femmes et combien d'hommes ? | ✅ |
| q08 | Quel est le taux de défaut des femmes et celui des hommes, en pourcentage ? | ✅ |
| q09 | Quel est le montant moyen de crédit par type de contrat ? | ✅ |
| q10 | Quel est le taux de défaut par niveau d'études, en pourcentage ? | ✅ |
| q11 | Combien de clients sont dans la classe de risque E ? | ✅ |
| q12 | Quelle est la probabilité de défaut moyenne du portefeuille, en pourcentage ? | ✅ |
| q13 | Quelle est la perte attendue totale du portefeuille ? | ✅ |
| q14 | Quel est l'âge moyen des clients qui ont fait défaut ? | ✅ |
| q15 | Quel est le taux de défaut par type de revenu, en pourcentage ? | ✅ |
| q16 | Combien de clients ont déjà eu au moins une demande de crédit refusée par le passé ? | ✅ |
| q17 | Quel est le taux d'effort moyen (annuity_to_income) des clients ? | ✅ |
| q18 | Quel est le montant de crédit maximum accordé ? | ✅ |
| q19 | Quel est le taux de défaut des clients de la classe de risque D, en pourcentage ? | ✅ |
| q20 | Combien de clients ont un revenu supérieur à 200000 ? | ✅ |
| q21 | Quelle est la perte attendue moyenne par classe de risque ? | ✅ |
| q22 | Quel est le nombre moyen de crédits dans d'autres établissements (bureau_nb_credits) ? | ✅ |
| q23 | Quel est le taux de défaut des clients mariés, en pourcentage ? | ✅ |
| q24 | Quels sont les 5 types de logement et le nombre de clients pour chacun ? | ✅ |
| q25 | Quel est le revenu moyen des clients qui ont fait défaut et de ceux qui n'ont pas fait défaut ? | ✅ |
| q26 | Combien de clients ont une part d'échéances en retard (inst_late_share) supérieure à 0.2 ? | ✅ |
| q27 | Quel est le taux de défaut des clients ayant un taux d'effort supérieur à 0.3, en pourcentage ? | ✅ |
| q28 | Quelle est la probabilité de défaut moyenne par classe de risque, en pourcentage ? | ✅ |
| q29 | Combien de clients de moins de 25 ans ont fait défaut ? | ✅ |
| q30 | Quel est le montant de crédit moyen des clients de la classe de risque A ? | ✅ |
