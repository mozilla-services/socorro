CREATE OR REPLACE FUNCTION create_table_if_not_exists(tablename text, declaration text, tableowner text DEFAULT ''::text, indexes text[] DEFAULT '{}'::text[]) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE dex INT := 1;
	scripts TEXT[] := '{}';
	indexname TEXT;
BEGIN
-- this function allows you to send a create table script to the backend 
-- multiple times without erroring.  it checks if the table is already
-- there and also optionally sets the ownership
-- this version of the function also creates indexes from a list of fields
	PERFORM 1 FROM pg_stat_user_tables
	WHERE relname = tablename;
	IF FOUND THEN
		RETURN TRUE;
	ELSE
		scripts := string_to_array(declaration, ';');
		WHILE scripts[dex] IS NOT NULL LOOP
			EXECUTE scripts[dex];
			dex := dex + 1;
		END LOOP;
	END IF;
	
	IF tableowner <> '' THEN
		EXECUTE 'ALTER TABLE ' || tablename || ' OWNER TO ' || tableowner;
	END IF;
	
	dex := 1;
	
	WHILE indexes[dex] IS NOT NULL LOOP
		indexname := replace( indexes[dex], ',', '_' );
		indexname := replace ( indexname, ' ', '' );
		EXECUTE 'CREATE INDEX ' || tablename || '_' || indexname || 
			' ON ' || tablename || '(' || indexes[dex] || ')';
		dex := dex + 1;
	END LOOP;
	
	EXECUTE 'ANALYZE ' || tablename;
	
	RETURN TRUE;
END;
$$;


