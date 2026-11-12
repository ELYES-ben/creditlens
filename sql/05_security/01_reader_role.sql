-- =====================================================================
-- 01_reader_role.sql — accès en LECTURE SEULE pour l'agent IA
--
-- 1. crée la vue marts.v_portefeuille : la « couche sémantique » de l'agent
--    (une seule table simple, avec des colonnes décrites en français)
-- 2. crée l'utilisateur creditlens_reader, qui ne peut QUE lire le schéma marts
--
-- Défense en profondeur : même si le LLM écrivait un DELETE ou un DROP,
-- PostgreSQL le refuserait, car cet utilisateur n'a aucun droit d'écriture.
--
-- À relancer si les tables marts sont reconstruites (la vue est alors supprimée).
-- =====================================================================

DROP VIEW IF EXISTS marts.v_portefeuille;

CREATE VIEW marts.v_portefeuille AS
SELECT
    f.client_id,
    f.is_default,
    f.gender,
    f.age_years,
    f.income,
    f.credit_amount,
    f.annuity,
    f.contract_type,
    f.income_type,
    f.education,
    f.family_status,
    f.housing_type,
    f.occupation,
    f.years_employed,
    f.credit_to_income,
    f.annuity_to_income,
    f.bureau_nb_credits,
    f.prev_nb_refused,
    f.inst_late_share,
    e.pd,
    e.risk_class,
    e.expected_loss
FROM marts.client_features f
JOIN marts.fct_expected_loss e USING (client_id);

COMMENT ON VIEW marts.v_portefeuille IS 'Portefeuille de crédits : une ligne par client (307 511 clients)';
COMMENT ON COLUMN marts.v_portefeuille.client_id        IS 'identifiant du client';
COMMENT ON COLUMN marts.v_portefeuille.is_default       IS '1 si le client a fait défaut (non remboursé), 0 sinon';
COMMENT ON COLUMN marts.v_portefeuille.gender           IS 'sexe : F ou M';
COMMENT ON COLUMN marts.v_portefeuille.age_years        IS 'âge en années';
COMMENT ON COLUMN marts.v_portefeuille.income           IS 'revenu annuel';
COMMENT ON COLUMN marts.v_portefeuille.credit_amount    IS 'montant du crédit accordé';
COMMENT ON COLUMN marts.v_portefeuille.annuity          IS 'montant de l''échéance';
COMMENT ON COLUMN marts.v_portefeuille.contract_type    IS 'type de contrat : Cash loans ou Revolving loans';
COMMENT ON COLUMN marts.v_portefeuille.income_type      IS 'type de revenu : Working, Commercial associate, Pensioner, State servant...';
COMMENT ON COLUMN marts.v_portefeuille.education        IS 'niveau d''études : Higher education, Secondary / secondary special, Incomplete higher, Lower secondary, Academic degree';
COMMENT ON COLUMN marts.v_portefeuille.family_status    IS 'situation familiale : Married, Single / not married, Civil marriage, Separated, Widow';
COMMENT ON COLUMN marts.v_portefeuille.housing_type     IS 'type de logement : House / apartment, With parents, Rented apartment...';
COMMENT ON COLUMN marts.v_portefeuille.occupation       IS 'profession (peut être vide)';
COMMENT ON COLUMN marts.v_portefeuille.years_employed   IS 'ancienneté dans l''emploi en années (vide si sans emploi ou retraité)';
COMMENT ON COLUMN marts.v_portefeuille.credit_to_income IS 'montant du crédit divisé par le revenu annuel';
COMMENT ON COLUMN marts.v_portefeuille.annuity_to_income IS 'taux d''effort : échéance divisée par le revenu (0.18 = 18 %)';
COMMENT ON COLUMN marts.v_portefeuille.bureau_nb_credits IS 'nombre de crédits du client dans d''autres établissements';
COMMENT ON COLUMN marts.v_portefeuille.prev_nb_refused  IS 'nombre de demandes de crédit refusées par le passé';
COMMENT ON COLUMN marts.v_portefeuille.inst_late_share  IS 'part des échéances passées payées en retard (0.1 = 10 %)';
COMMENT ON COLUMN marts.v_portefeuille.pd               IS 'probabilité de défaut estimée par le modèle (0.08 = 8 %)';
COMMENT ON COLUMN marts.v_portefeuille.risk_class       IS 'classe de risque de A (très faible) à E (très élevé)';
COMMENT ON COLUMN marts.v_portefeuille.expected_loss    IS 'perte attendue = pd x 45 % x montant du crédit';

-- Utilisateur en lecture seule (mot de passe local de développement, voir .env)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'creditlens_reader') THEN
        CREATE ROLE creditlens_reader LOGIN PASSWORD 'reader_local_only';
    END IF;
END
$$;

ALTER ROLE creditlens_reader SET default_transaction_read_only = on;   -- aucune écriture possible
ALTER ROLE creditlens_reader SET statement_timeout = '20s';            -- pas de requête interminable

GRANT USAGE ON SCHEMA marts TO creditlens_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO creditlens_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO creditlens_reader;
