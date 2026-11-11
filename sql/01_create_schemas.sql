-- =====================================================================
-- 01_create_schemas.sql
-- Crée les 3 couches de la base CreditLens
--   raw     : données sources brutes, jamais modifiées
--   staging : données nettoyées et typées
--   marts   : tables métier pour l'analyse, le dashboard et l'IA
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

COMMENT ON SCHEMA raw     IS 'Données sources brutes, jamais modifiées';
COMMENT ON SCHEMA staging IS 'Données nettoyées et typées';
COMMENT ON SCHEMA marts   IS 'Tables métier pour analyse, dashboard et IA';