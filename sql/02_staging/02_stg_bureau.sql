-- =====================================================================
-- 02_stg_bureau.sql — crédits du client dans D'AUTRES établissements
-- Source : raw.bureau   ->   Cible : staging.stg_bureau
-- Une ligne par crédit externe (un client peut en avoir plusieurs).
-- =====================================================================

DROP TABLE IF EXISTS staging.stg_bureau CASCADE;

CREATE TABLE staging.stg_bureau AS
SELECT
    sk_id_bureau::bigint                         AS bureau_credit_id,
    sk_id_curr::bigint                           AS client_id,
    credit_active                                AS credit_status,       -- Active, Closed, Sold, Bad debt
    credit_type,
    -days_credit::numeric::int                   AS days_since_opened,
    credit_day_overdue::numeric::int             AS days_overdue,
    amt_credit_sum::numeric                      AS credit_amount,
    COALESCE(amt_credit_sum_debt::numeric, 0)    AS remaining_debt,
    COALESCE(amt_credit_sum_overdue::numeric, 0) AS overdue_amount,
    cnt_credit_prolong::numeric::int             AS nb_prolongations,
    (credit_active = 'Bad debt')                 AS is_bad_debt
FROM raw.bureau;

ALTER TABLE staging.stg_bureau ADD PRIMARY KEY (bureau_credit_id);
CREATE INDEX ON staging.stg_bureau (client_id);
