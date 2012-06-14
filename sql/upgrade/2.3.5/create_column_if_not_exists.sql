/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

create or replace function add_column_if_not_exists (
	coltable text, colname text, declaration text,
	indexed boolean default false)
returns boolean
language plpgsql
as $f$
DECLARE dex INT := 1;
	scripts TEXT[] := '{}';
BEGIN
-- this function allows you to send an add column script to the backend 
-- multiple times without erroring.  it checks if the column is already
-- there and also optionally creates and index on it

	PERFORM 1 FROM information_schema.columns
	WHERE table_name = coltable
		AND column_name = colname;
	IF FOUND THEN
		RETURN TRUE;
	END IF;	
	
	scripts := string_to_array(declaration, ';');
	WHILE scripts[dex] IS NOT NULL LOOP
		EXECUTE scripts[dex];
		dex := dex + 1;
	END LOOP;

	IF indexed THEN
		EXECUTE 'CREATE INDEX ' || coltable || '_' || colname || 
			' ON ' || coltable || '(' || colname || ')';
	END IF;
	
	RETURN TRUE;
END;
$f$;