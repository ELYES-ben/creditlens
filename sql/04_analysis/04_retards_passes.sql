-- =====================================================================
-- Q4. Les retards de paiement passés annoncent-ils le défaut ?
-- On relie chaque client à son historique de remboursement chez Home Credit.
-- LEFT JOIN : on garde aussi les clients SANS historique (nouveaux clients).
-- =====================================================================
WITH clients AS (
    SELECT
        a.is_default,
        CASE
            WHEN h.client_id IS NULL      THEN '0. aucun historique'
            WHEN h.late_share = 0         THEN '1. jamais en retard'
            WHEN h.late_share < 0.05      THEN '2. moins de 5 % en retard'
            WHEN h.late_share < 0.20      THEN '3. 5 à 20 % en retard'
            ELSE                               '4. plus de 20 % en retard'
        END AS historique
    FROM staging.stg_application a
    LEFT JOIN staging.agg_client_installments h USING (client_id)
)
SELECT
    historique,
    COUNT(*)                                       AS nb_clients,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS part_clients_pct,
    ROUND(100.0 * AVG(is_default), 2)              AS taux_defaut_pct
FROM clients
GROUP BY historique
ORDER BY historique;
