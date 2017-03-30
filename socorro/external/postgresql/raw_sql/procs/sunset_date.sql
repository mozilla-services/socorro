CREATE OR REPLACE FUNCTION sunset_date(
    build_id numeric,
    build_type text
)
    RETURNS date
    LANGUAGE sql IMMUTABLE
AS $_$
-- Sets a sunset date for visibility
-- based on a build ID.
-- Current spec is 36 weeks for releases, 36 weeks for ESR
-- and 18 weeks for everything else.
select ( build_date($1) +
    case when lower($2) = 'release'
        then interval '36 weeks'
    when lower($2) = 'esr'
        then interval '36 weeks'
    else
        interval '18 weeks'
    end ) :: date
$_$;
