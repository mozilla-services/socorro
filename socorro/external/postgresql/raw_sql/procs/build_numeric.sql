CREATE OR REPLACE FUNCTION build_numeric(character varying) RETURNS numeric
    LANGUAGE sql STRICT
    AS $_$
-- safely converts a build number to a numeric type
-- if the build is not a number, returns NULL
SELECT CASE WHEN $1 ~ $x$^\d+$$x$ THEN
	$1::numeric
ELSE
	NULL::numeric
END;$_$;


