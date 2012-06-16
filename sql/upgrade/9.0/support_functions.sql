/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
		' WHERE ' || lcol || ' = ' || quote_literal(lval)
	INTO nrows;
	
	IF nrows > 0 THEN
		RETURN true;
	ELSE 
		RAISE EXCEPTION '% is not a valid %',lval,lmessage;
	END IF;
END;
$f$;

DROP FUNCTION IF EXISTS add_column_if_not_exists ( text, text, text, boolean );

CREATE OR REPLACE FUNCTION add_column_if_not_exists (
	tablename text, columnname text, 
	datatype text, 
	nonnull boolean default false,
	defaultval text default '',
	constrainttext text default '' )
RETURNS boolean
LANGUAGE plpgsql 
AS $f$
BEGIN
-- support function for creating new columns idempotently
-- does not check data type for changes
-- allows constraints and defaults; beware of using
-- these against large tables!
-- if the column already exists, does not check for
-- the constraints and defaults

-- validate input
IF nonnull AND ( defaultval = '' ) THEN
	RAISE EXCEPTION 'for NOT NULL columns, you must add a default';
END IF;

IF defaultval <> '' THEN
	defaultval := ' DEFAULT ' || quote_literal(defaultval);
END IF;

-- check if the column already exists.
PERFORM 1 
FROM information_schema.columns
WHERE table_name = tablename
	AND column_name = columnname;
	
IF FOUND THEN
	RETURN FALSE;
END IF;

EXECUTE 'ALTER TABLE ' || tablename ||
	' ADD COLUMN ' || columnname ||
	' ' || datatype || defaultval;

IF nonnull THEN
	EXECUTE 'ALTER TABLE ' || tablename ||
		' ALTER COLUMN ' || columnname ||
		|| ' SET NOT NULL;';
END IF;

IF constrainttext <> '' THEn
	EXECUTE 'ALTER TABLE ' || tablename ||
		' ADD CONSTRAINT ' || constrainttext;
END IF;

RETURN TRUE;

END;$f$;




	
	