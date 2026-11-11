-- =====================================================================
-- Q5. Les 10 segments les plus risqués et leur poids dans le portefeuille
-- Segment = type de revenu × niveau d'études × tranche d'âge.
-- RANK() classe les segments ; on compare chaque segment à la moyenne.
-- =====================================================================
WITH seg AS (
    SELECT
        income_type,
        education,
        CASE WHEN age_years < 35 THEN 'moins de 35 ans'
             WHEN age_years < 50 THEN '35-49 ans'
             ELSE '50 ans et plus' END                  AS tranche_age,
        is_default,
        credit_amount
    FROM staging.stg_application
),
stats AS (
    SELECT
        income_type, education, tranche_age,
        COUNT(*)                                        AS nb_clients,
        AVG(is_default)                                 AS taux_defaut,
        SUM(credit_amount)                              AS montant
    FROM seg
    GROUP BY income_type, education, tranche_age
    HAVING COUNT(*) >= 30
),
ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY taux_defaut DESC)         AS rang,
        (SELECT AVG(is_default) FROM seg)               AS taux_moyen,
        SUM(montant) OVER ()                            AS montant_total
    FROM stats
)
SELECT
    rang,
    income_type,
    education,
    tranche_age,
    nb_clients,
    ROUND(100.0 * taux_defaut, 2)                       AS taux_defaut_pct,
    ROUND(taux_defaut / taux_moyen, 2)                  AS multiple_vs_moyenne,  -- 2.0 = deux fois plus risqué
    ROUND(100.0 * montant / montant_total, 2)           AS part_montant_pct
FROM ranked
WHERE rang <= 10
ORDER BY rang;
