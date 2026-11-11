-- =====================================================================
-- Q3. Le défaut augmente-t-il avec le taux d'effort ?
-- Taux d'effort = échéance / revenu (annuity_to_income).
-- NTILE(10) découpe les clients en 10 groupes de même taille (déciles).
-- =====================================================================
WITH deciles AS (
    SELECT
        is_default,
        annuity_to_income,
        NTILE(10) OVER (ORDER BY annuity_to_income) AS decile
    FROM staging.stg_application
    WHERE annuity_to_income IS NOT NULL
)
SELECT
    decile,
    COUNT(*)                                      AS nb_clients,
    ROUND(MIN(annuity_to_income), 3)              AS effort_min,
    ROUND(MAX(annuity_to_income), 3)              AS effort_max,
    ROUND(100.0 * AVG(is_default), 2)             AS taux_defaut_pct,
    -- écart par rapport au décile 1 (les clients les moins endettés)
    ROUND(100.0 * AVG(is_default)
          - FIRST_VALUE(100.0 * AVG(is_default)) OVER (ORDER BY decile), 2) AS ecart_vs_decile1_pts
FROM deciles
GROUP BY decile
ORDER BY decile;
