-- =====================================================================
-- 03_stg_previous_application.sql — anciennes demandes chez Home Credit
-- Source : raw.previous_application   ->   Cible : staging.stg_previous_application
-- =====================================================================

DROP TABLE IF EXISTS staging.stg_previous_application CASCADE;

CREATE TABLE staging.stg_previous_application AS
SELECT
    sk_id_prev::bigint                           AS previous_id,
    sk_id_curr::bigint                           AS client_id,
    name_contract_type                           AS contract_type,
    name_contract_status                         AS decision,            -- Approved, Refused, Canceled, Unused offer
    amt_application::numeric                     AS amount_requested,
    amt_credit::numeric                          AS amount_granted,
    amt_annuity::numeric                         AS annuity,
    cnt_payment::numeric::int                    AS nb_payments,
    -days_decision::numeric::int                 AS days_since_decision,
    -- 365243 = date non renseignée (même code que DAYS_EMPLOYED)
    NULLIF(days_first_due::numeric, 365243)      AS days_first_due,
    (name_contract_status = 'Refused')           AS is_refused
FROM raw.previous_application;

ALTER TABLE staging.stg_previous_application ADD PRIMARY KEY (previous_id);
CREATE INDEX ON staging.stg_previous_application (client_id);
