-- =====================================================================
-- 01_stg_application.sql — une ligne par client, typée et nettoyée
-- Source : raw.application_train   ->   Cible : staging.stg_application
--
-- Ce que fait ce script :
--   1. convertit le texte en vrais types (nombre, booléen)        ->  ::numeric, ::int
--   2. renomme les colonnes en noms clairs                          ->  AS ...
--   3. traite les anomalies connues (365243, 'XNA', revenus aberrants)
--   4. crée des variables utiles : âge, ancienneté, ratios financiers
-- =====================================================================

DROP TABLE IF EXISTS staging.stg_application CASCADE;

CREATE TABLE staging.stg_application AS
WITH typed AS (
    SELECT
        sk_id_curr::bigint                          AS client_id,
        target::smallint                            AS is_default,          -- 1 = défaut de remboursement
        name_contract_type                          AS contract_type,
        NULLIF(code_gender, 'XNA')                  AS gender,              -- 'XNA' = inconnu -> NULL
        (flag_own_car = 'Y')                        AS owns_car,
        (flag_own_realty = 'Y')                     AS owns_realty,
        cnt_children::numeric::int                  AS nb_children,
        cnt_fam_members::numeric::int               AS family_size,
        amt_income_total::numeric                   AS income,
        amt_credit::numeric                         AS credit_amount,
        amt_annuity::numeric                        AS annuity,
        amt_goods_price::numeric                    AS goods_price,
        name_income_type                            AS income_type,
        name_education_type                         AS education,
        NULLIF(name_family_status, 'Unknown')       AS family_status,
        name_housing_type                           AS housing_type,
        occupation_type                             AS occupation,
        NULLIF(organization_type, 'XNA')            AS organization_type,   -- 'XNA' = retraité / sans employeur
        region_rating_client::numeric::int          AS region_rating,       -- 1 = meilleure région, 3 = moins bonne
        region_population_relative::numeric         AS region_population,
        days_birth::numeric                         AS days_birth,
        days_employed::numeric                      AS days_employed,
        ext_source_1::numeric                       AS ext_source_1,
        ext_source_2::numeric                       AS ext_source_2,
        ext_source_3::numeric                       AS ext_source_3
    FROM raw.application_train
)
SELECT
    client_id,
    is_default,
    contract_type,
    gender,
    owns_car,
    owns_realty,
    nb_children,
    family_size,
    income,
    credit_amount,
    annuity,
    goods_price,
    income_type,
    education,
    family_status,
    housing_type,
    occupation,
    organization_type,
    region_rating,
    region_population,

    -- Âge : DAYS_BIRTH est un nombre de jours NÉGATIF avant la demande
    ROUND(-days_birth / 365.25, 1)                                  AS age_years,

    -- Ancienneté : 365243 n'est pas une durée réelle, c'est le code « sans emploi / retraité »
    CASE WHEN days_employed = 365243 THEN NULL
         ELSE ROUND(-days_employed / 365.25, 1) END                 AS years_employed,
    (days_employed = 365243)                                         AS no_employment_flag,

    ext_source_1,
    ext_source_2,
    ext_source_3,

    -- Revenu aberrant (ex. 117 M) : on le garde mais on le signale
    (income > 10000000)                                              AS income_outlier_flag,

    -- Ratios financiers (NULLIF évite la division par zéro)
    ROUND(credit_amount / NULLIF(income, 0), 3)                      AS credit_to_income,
    ROUND(annuity / NULLIF(income, 0), 4)                            AS annuity_to_income,   -- taux d'effort
    ROUND(credit_amount / NULLIF(annuity, 0), 1)                     AS credit_term,          -- nb d'échéances
    ROUND(credit_amount / NULLIF(goods_price, 0), 3)                 AS credit_to_goods
FROM typed;

ALTER TABLE staging.stg_application ADD PRIMARY KEY (client_id);

COMMENT ON TABLE staging.stg_application IS 'Une ligne par demande de prêt, typée et nettoyée (source : raw.application_train)';
