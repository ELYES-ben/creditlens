-- =====================================================================
-- 01_client_features.sql — table de variables pour le modèle de scoring
-- Une ligne par client : ses infos personnelles + le résumé de son historique
-- Sources : staging.stg_application, stg_bureau, stg_previous_application,
--           agg_client_installments
-- Cible   : marts.client_features
-- =====================================================================

DROP TABLE IF EXISTS marts.client_features CASCADE;

CREATE TABLE marts.client_features AS
WITH bureau AS (            -- crédits dans d'autres établissements
    SELECT
        client_id,
        COUNT(*)                                        AS bureau_nb_credits,
        SUM((credit_status = 'Active')::int)            AS bureau_nb_active,
        SUM(is_bad_debt::int)                           AS bureau_nb_bad_debt,
        SUM(remaining_debt)                             AS bureau_total_debt,
        SUM(overdue_amount)                             AS bureau_total_overdue,
        MAX(days_overdue)                               AS bureau_max_days_overdue,
        SUM(nb_prolongations)                           AS bureau_nb_prolongations
    FROM staging.stg_bureau
    GROUP BY client_id
),
previous AS (               -- anciennes demandes chez Home Credit
    SELECT
        client_id,
        COUNT(*)                                        AS prev_nb_applications,
        SUM(is_refused::int)                            AS prev_nb_refused,
        ROUND(AVG(is_refused::int), 4)                  AS prev_refused_share,
        ROUND(AVG(amount_requested))                    AS prev_avg_amount_requested
    FROM staging.stg_previous_application
    GROUP BY client_id
)
SELECT
    a.client_id,
    a.is_default,                                       -- la cible à prédire
    -- profil
    a.contract_type, a.gender, a.owns_car, a.owns_realty, a.nb_children, a.family_size,
    a.income_type, a.education, a.family_status, a.housing_type, a.occupation,
    a.organization_type, a.region_rating, a.region_population,
    a.age_years, a.years_employed, a.no_employment_flag,
    -- montants et ratios
    a.income, a.credit_amount, a.annuity, a.goods_price,
    a.credit_to_income, a.annuity_to_income, a.credit_term, a.credit_to_goods,
    -- scores externes (agences de crédit)
    a.ext_source_1, a.ext_source_2, a.ext_source_3,
    -- historique dans d'autres banques (0 si aucun crédit connu)
    COALESCE(b.bureau_nb_credits, 0)                    AS bureau_nb_credits,
    COALESCE(b.bureau_nb_active, 0)                     AS bureau_nb_active,
    COALESCE(b.bureau_nb_bad_debt, 0)                   AS bureau_nb_bad_debt,
    COALESCE(b.bureau_total_debt, 0)                    AS bureau_total_debt,
    COALESCE(b.bureau_total_overdue, 0)                 AS bureau_total_overdue,
    COALESCE(b.bureau_max_days_overdue, 0)              AS bureau_max_days_overdue,
    COALESCE(b.bureau_nb_prolongations, 0)              AS bureau_nb_prolongations,
    -- anciennes demandes
    COALESCE(p.prev_nb_applications, 0)                 AS prev_nb_applications,
    COALESCE(p.prev_nb_refused, 0)                      AS prev_nb_refused,
    p.prev_refused_share,
    p.prev_avg_amount_requested,
    -- comportement de remboursement (NULL = aucun historique)
    i.nb_installments                                   AS inst_nb_installments,
    i.late_share                                        AS inst_late_share,
    i.max_days_late                                     AS inst_max_days_late,
    i.avg_days_late                                     AS inst_avg_days_late,
    i.underpaid_share                                   AS inst_underpaid_share
FROM staging.stg_application a
LEFT JOIN bureau b                          USING (client_id)
LEFT JOIN previous p                        USING (client_id)
LEFT JOIN staging.agg_client_installments i USING (client_id);

ALTER TABLE marts.client_features ADD PRIMARY KEY (client_id);

COMMENT ON TABLE marts.client_features IS 'Une ligne par client : variables du modèle de scoring';
