-- =====================================================================
-- Q7. Simulation de politique d'octroi : et si on refusait les classes à risque ?
--
-- Pour chaque politique (refuser E ; refuser D et E) :
--   - pertes évitées     = perte attendue des clients refusés
--   - marge perdue       = marge que les BONS clients refusés auraient rapportée
--                          (hypothèse : 10 % du montant × probabilité de rembourser)
--   - gain net           = pertes évitées − marge perdue
-- =====================================================================
WITH policies AS (
    SELECT 'Refuser la classe E'      AS politique, ARRAY['E']      AS classes_refusees
    UNION ALL
    SELECT 'Refuser les classes D et E',            ARRAY['D', 'E']
),
impact AS (
    SELECT
        p.politique,
        COUNT(*) FILTER (WHERE e.risk_class = ANY (p.classes_refusees))                    AS nb_refuses,
        SUM(e.expected_loss) FILTER (WHERE e.risk_class = ANY (p.classes_refusees))        AS pertes_evitees,
        SUM(0.10 * e.ead * (1 - e.pd)) FILTER (WHERE e.risk_class = ANY (p.classes_refusees)) AS marge_perdue,
        SUM(e.expected_loss)                                                               AS perte_totale,
        COUNT(*)                                                                           AS nb_total
    FROM policies p
    CROSS JOIN marts.fct_expected_loss e
    GROUP BY p.politique
)
SELECT
    politique,
    nb_refuses,
    ROUND(100.0 * nb_refuses / nb_total, 1)                     AS part_refusee_pct,
    ROUND(pertes_evitees / 1e6, 1)                              AS pertes_evitees_m,
    ROUND(100.0 * pertes_evitees / perte_totale, 1)             AS part_pertes_evitees_pct,
    ROUND(marge_perdue / 1e6, 1)                                AS marge_perdue_m,
    ROUND((pertes_evitees - marge_perdue) / 1e6, 1)             AS gain_net_m
FROM impact
ORDER BY nb_refuses;
