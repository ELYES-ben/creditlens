-- =====================================================================
-- 02_expected_loss.sql — perte attendue (Expected Loss) par client
--
--   EL = PD × LGD × EAD
--   PD  : probabilité de défaut       -> sortie du modèle (marts.client_scores)
--   LGD : part perdue en cas de défaut -> hypothèse 45 % (valeur de référence
--         de Bâle pour un crédit non garanti, approche fondation)
--   EAD : montant exposé au défaut     -> montant du crédit accordé
--         (Home Credit ne donne pas le capital restant dû)
--
-- Classes de risque A à E selon la PD (comme une notation interne de banque)
-- Cible : marts.fct_expected_loss
-- =====================================================================

DROP TABLE IF EXISTS marts.fct_expected_loss CASCADE;

CREATE TABLE marts.fct_expected_loss AS
SELECT
    f.client_id,
    f.is_default,
    s.in_test_set,
    f.contract_type,
    f.income_type,
    f.education,
    f.age_years,
    f.income,
    s.pd::numeric(10, 6)                         AS pd,   -- double -> numeric (pour ROUND)
    0.45                                         AS lgd,
    f.credit_amount                              AS ead,
    ROUND(s.pd::numeric * 0.45 * f.credit_amount, 2) AS expected_loss,
    CASE
        WHEN s.pd < 0.025 THEN 'A'      -- risque très faible
        WHEN s.pd < 0.05  THEN 'B'      -- risque faible
        WHEN s.pd < 0.10  THEN 'C'      -- risque moyen
        WHEN s.pd < 0.20  THEN 'D'      -- risque élevé
        ELSE                   'E'      -- risque très élevé
    END                                          AS risk_class
FROM marts.client_features f
JOIN marts.client_scores   s USING (client_id);

ALTER TABLE marts.fct_expected_loss ADD PRIMARY KEY (client_id);
CREATE INDEX ON marts.fct_expected_loss (risk_class);

COMMENT ON TABLE marts.fct_expected_loss IS
    'Perte attendue par client (EL = PD x LGD x EAD) et classe de risque A-E';
