-- =====================================================================
-- 04_stg_installments.sql — historique des remboursements
-- Source : raw.installments_payments
-- Cibles : staging.stg_installments          (une ligne par échéance)
--          staging.agg_client_installments   (une ligne par client)
-- =====================================================================

DROP TABLE IF EXISTS staging.stg_installments CASCADE;

CREATE TABLE staging.stg_installments AS
WITH typed AS (
    SELECT
        sk_id_prev::bigint                       AS previous_id,
        sk_id_curr::bigint                       AS client_id,
        num_instalment_number::numeric::int      AS installment_number,
        days_instalment::numeric                 AS due_day,              -- date prévue
        days_entry_payment::numeric              AS paid_day,             -- date réelle (NULL = pas payé)
        amt_instalment::numeric                  AS amount_due,
        amt_payment::numeric                     AS amount_paid
    FROM raw.installments_payments
)
SELECT
    *,
    GREATEST(paid_day - due_day, 0)              AS days_late,            -- 0 si payé à temps ou en avance
    (paid_day - due_day > 0)                     AS is_late,
    (amount_paid < amount_due - 0.01)            AS is_underpaid          -- tolérance d'un centime
FROM typed;

CREATE INDEX ON staging.stg_installments (client_id);

-- Résumé par client : sert à l'analyse (question 4) et au modèle (semaine 3)
DROP TABLE IF EXISTS staging.agg_client_installments CASCADE;

CREATE TABLE staging.agg_client_installments AS
SELECT
    client_id,
    COUNT(*)                                             AS nb_installments,
    ROUND(AVG(is_late::int), 4)                          AS late_share,         -- part d'échéances en retard
    MAX(days_late)                                       AS max_days_late,
    ROUND(AVG(days_late), 2)                             AS avg_days_late,
    ROUND(AVG(is_underpaid::int), 4)                     AS underpaid_share,
    SUM(amount_due)                                      AS total_due,
    SUM(amount_paid)                                     AS total_paid
FROM staging.stg_installments
GROUP BY client_id;

ALTER TABLE staging.agg_client_installments ADD PRIMARY KEY (client_id);
