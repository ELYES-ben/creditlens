-- =====================================================================
-- Q2. Quels profils de clients font le plus défaut ?
-- Taux de défaut par tranche d'âge, quintile de revenu, études, type de revenu.
-- Une seule requête, résultat en format long : (dimension, segment, ...).
-- =====================================================================
WITH base AS (
    SELECT
        is_default,
        credit_amount,
        CASE
            WHEN age_years < 25 THEN '1. moins de 25 ans'
            WHEN age_years < 35 THEN '2. 25-34 ans'
            WHEN age_years < 45 THEN '3. 35-44 ans'
            WHEN age_years < 55 THEN '4. 45-54 ans'
            ELSE                     '5. 55 ans et plus'
        END                                                    AS tranche_age,
        'Q' || NTILE(5) OVER (ORDER BY income)                 AS quintile_revenu,  -- Q1 = 20 % les plus modestes
        education,
        income_type
    FROM staging.stg_application
),
long AS (
    SELECT 'Âge'            AS dimension, tranche_age     AS segment, is_default, credit_amount FROM base
    UNION ALL
    SELECT 'Revenu',                      quintile_revenu,            is_default, credit_amount FROM base
    UNION ALL
    SELECT 'Études',                      education,                  is_default, credit_amount FROM base
    UNION ALL
    SELECT 'Type de revenu',              income_type,                is_default, credit_amount FROM base
)
SELECT
    dimension,
    segment,
    COUNT(*)                                   AS nb_clients,
    ROUND(100.0 * AVG(is_default), 2)          AS taux_defaut_pct,
    ROUND(SUM(credit_amount) / 1e6, 1)         AS montant_m
FROM long
GROUP BY dimension, segment
HAVING COUNT(*) >= 30                          -- ignore les segments trop petits pour conclure
ORDER BY dimension, segment;
