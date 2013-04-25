CREATE OR REPLACE FUNCTION nonzero_string(citext) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$_$;


ALTER FUNCTION public.nonzero_string(citext) OWNER TO postgres;

--
-- Name: nonzero_string(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE OR REPLACE FUNCTION nonzero_string(text) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$_$;


