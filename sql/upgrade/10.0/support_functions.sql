CREATE OR REPLACE FUNCTION nonzero_string (
	citext )
RETURNS boolean
LANGUAGE sql AS
$f$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$f$;

CREATE OR REPLACE FUNCTION nonzero_string (
	text )
RETURNS boolean
LANGUAGE sql AS
$f$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$f$;

CREATE OR REPLACE FUNCTION validate_lookup (
	ltable text, lcol text, lval text, lmessage text )
RETURNS boolean
LANGUAGE plpgsql AS
$f$
DECLARE nrows INT;
BEGIN
	EXECUTE 'SELECT 1 FROM ' || ltable ||
		' WHERE ' || lcol || ' = ' || quote_literal(lcol)
	INTO nrows;
	
	IF nrows > 0 THEN
		RETURN true;
	ELSE 
		RAISE EXCEPTION '% is not a valid %',lval,lmessage;
	END IF;
END;
$f$;
	