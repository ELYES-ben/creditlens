-- =====================================================================
-- Q1. À quoi ressemble le portefeuille ?
-- Volume, montants prêtés et taux de défaut par type de contrat.
-- NB : Home Credit ne donne pas le capital restant dû ; on utilise le
-- montant accordé (credit_amount) comme mesure de l'exposition.
-- =====================================================================
WITH totals AS (
    SELECT COUNT(*) AS n_total, SUM(credit_amount) AS m_total
    FROM staging.stg_application
)
SELECT
    COALESCE(contract_type, 'TOTAL')                            AS contract_type,
    COUNT(*)                                                    AS nb_credits,
    ROUND(100.0 * COUNT(*) / MAX(t.n_total), 1)                 AS part_credits_pct,
    ROUND(SUM(credit_amount) / 1e6, 1)                          AS montant_total_m,
    ROUND(100.0 * SUM(credit_amount) / MAX(t.m_total), 1)       AS part_montant_pct,
    ROUND(AVG(credit_amount))                                   AS montant_moyen,
    ROUND(100.0 * AVG(is_default), 2)                           AS taux_defaut_pct
FROM staging.stg_application
CROSS JOIN totals t
GROUP BY ROLLUP (contract_type)          -- ROLLUP ajoute une ligne de total
ORDER BY contract_type NULLS LAST;
