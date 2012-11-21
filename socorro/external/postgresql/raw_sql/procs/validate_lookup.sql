CREATE FUNCTION validate_lookup(ltable text, lcol text, lval text, lmessage text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
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
$$;


