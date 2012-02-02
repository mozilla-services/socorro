\set ON_ERROR_STOP 1

ALTER TABLE reports_clean ADD architecture CITEXT;
ALTER TABLE reports_clean ADD cores INT;

