CREATE FUNCTION is_rapid_beta(channel citext, repversion text, rbetaversion text) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT $1 = 'beta' AND major_version_sort($2) >= major_version_sort($3);
$_$;


