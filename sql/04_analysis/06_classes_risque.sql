-- =====================================================================
-- Q6. Les 5 classes de risque : combien de clients, quel risque, quelle perte ?
-- Le taux de défaut RÉEL est mesuré sur le jeu de test (clients jamais vus
-- par le modèle) : c'est la preuve que les classes sont bien ordonnées.
-- =====================================================================
WITH totals AS (
    SELECT SUM(ead) AS ead_total, SUM(expected_loss) AS el_total
    FROM marts.fct_expected_loss
)
SELECT
    risk_class                                                     AS classe,
    COUNT(*)                                                       AS nb_clients,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)             AS part_clients_pct,
    ROUND(100.0 * AVG(pd), 2)                                      AS pd_moyenne_pct,
    ROUND(100.0 * AVG(is_default) FILTER (WHERE in_test_set), 2)   AS defaut_reel_test_pct,
    ROUND(SUM(ead) / 1e6, 1)                                       AS exposition_m,
    ROUND(SUM(expected_loss) / 1e6, 1)                             AS perte_attendue_m,
    ROUND(100.0 * SUM(expected_loss) / MAX(t.el_total), 1)         AS part_perte_pct,
    ROUND(100.0 * SUM(expected_loss) / SUM(ead), 2)                AS perte_sur_exposition_pct
FROM marts.fct_expected_loss
CROSS JOIN totals t
GROUP BY risk_class
ORDER BY risk_class;
