CREATE OR REPLACE FUNCTION sunset_date(
    build_id numeric,
    build_type text
)
    RETURNS date
    LANGUAGE sql IMMUTABLE
AS $_$
-- sets a sunset date for visibility
-- based on a build number
-- current spec is 18 weeks for releases
-- 9 weeks for everything else
select ( build_date($1) +
    case when lower($2) = 'release'
        then interval '18 weeks'
    when lower($2) = 'esr'
        then interval '18 weeks'
    else
        interval '9 weeks'
    end ) :: date
$_$;
