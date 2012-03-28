--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

--
-- Name: plperl; Type: PROCEDURAL LANGUAGE; Schema: -; Owner: postgres
--

CREATE OR REPLACE PROCEDURAL LANGUAGE plperl;


ALTER PROCEDURAL LANGUAGE plperl OWNER TO postgres;

--
-- Name: plpgsql; Type: PROCEDURAL LANGUAGE; Schema: -; Owner: postgres
--

CREATE OR REPLACE PROCEDURAL LANGUAGE plpgsql;


ALTER PROCEDURAL LANGUAGE plpgsql OWNER TO postgres;

SET search_path = public, pg_catalog;

--
-- Name: citext; Type: SHELL TYPE; Schema: public; Owner: postgres
--

CREATE TYPE citext;


--
-- Name: citextin(cstring); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citextin(cstring) RETURNS citext
    LANGUAGE internal IMMUTABLE STRICT
    AS $$textin$$;


ALTER FUNCTION public.citextin(cstring) OWNER TO postgres;

--
-- Name: citextout(citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citextout(citext) RETURNS cstring
    LANGUAGE internal IMMUTABLE STRICT
    AS $$textout$$;


ALTER FUNCTION public.citextout(citext) OWNER TO postgres;

--
-- Name: citextrecv(internal); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citextrecv(internal) RETURNS citext
    LANGUAGE internal STABLE STRICT
    AS $$textrecv$$;


ALTER FUNCTION public.citextrecv(internal) OWNER TO postgres;

--
-- Name: citextsend(citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citextsend(citext) RETURNS bytea
    LANGUAGE internal STABLE STRICT
    AS $$textsend$$;


ALTER FUNCTION public.citextsend(citext) OWNER TO postgres;

--
-- Name: citext; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE citext (
    INTERNALLENGTH = variable,
    INPUT = citextin,
    OUTPUT = citextout,
    RECEIVE = citextrecv,
    SEND = citextsend,
    CATEGORY = 'S',
    ALIGNMENT = int4,
    STORAGE = extended
);


ALTER TYPE public.citext OWNER TO postgres;

--
-- Name: major_version; Type: DOMAIN; Schema: public; Owner: breakpad_rw
--

CREATE DOMAIN major_version AS text
    CONSTRAINT major_version_check CHECK ((VALUE ~ '^\\d+\\.\\d+'::text));


ALTER DOMAIN public.major_version OWNER TO breakpad_rw;

--
-- Name: product_info_change; Type: TYPE; Schema: public; Owner: breakpad_rw
--

CREATE TYPE product_info_change AS (
    begin_date date,
    end_date date,
    featured boolean,
    crash_throttle numeric
);


ALTER TYPE public.product_info_change OWNER TO breakpad_rw;

--
-- Name: release_enum; Type: TYPE; Schema: public; Owner: breakpad_rw
--

CREATE TYPE release_enum AS ENUM (
    'major',
    'milestone',
    'development'
);


ALTER TYPE public.release_enum OWNER TO breakpad_rw;

--
-- Name: add_column_if_not_exists(text, text, text, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION add_column_if_not_exists(coltable text, colname text, declaration text, indexed boolean DEFAULT false) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION public.add_column_if_not_exists(coltable text, colname text, declaration text, indexed boolean) OWNER TO postgres;

--
-- Name: add_old_release(text, text, release_enum, date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION add_old_release(product_name text, new_version text, release_type release_enum DEFAULT 'major'::release_enum, release_date date DEFAULT ('now'::text)::date, is_featured boolean DEFAULT false) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE last_date DATE;
featured_count INT;
new_id INT;
BEGIN

IF release_type = 'major' THEN
last_date := release_date + ( 18 * 7 );
ELSE
last_date := release_date + ( 9 * 7 );
END IF;

IF is_featured THEN
-- check if we already have 4 featured
SELECT COUNT(*) INTO featured_count
FROM productdims JOIN product_visibility
ON productdims.id = product_visibility.productdims_id
WHERE featured
AND product = product_name
AND end_date >= current_date;

IF featured_count > 4 THEN
-- too many, drop one
UPDATE product_visibility
SET featured = false
WHERE productdims_id = (
SELECT id
FROM productdims
JOIN product_visibility viz2
ON productdims.id = viz2.productdims_id
WHERE product = product_name
AND featured
AND end_date >= current_date
ORDER BY viz2.end_date LIMIT 1
);
END IF;
END IF;

    -- now add it

    INSERT INTO productdims ( product, version, branch, release, version_sort )
    VALUES ( product_name, new_version, '2.2', release_type, old_version_sort(new_version) )
    RETURNING id
    INTO new_id;

    INSERT INTO product_visibility ( productdims_id, start_date, end_date,
    featured, throttle )
    VALUES ( new_id, release_date, last_date, is_featured, 100 );

    RETURN TRUE;

END; $$;


ALTER FUNCTION public.add_old_release(product_name text, new_version text, release_type release_enum, release_date date, is_featured boolean) OWNER TO postgres;

--
-- Name: aurora_or_nightly(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION aurora_or_nightly(version text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
-- figures out "aurora" or "nightly" from a version string
-- returns ERROR otherwise
SELECT CASE WHEN $1 LIKE '%a1' THEN 'nightly'
    WHEN $1 LIKE '%a2' THEN 'aurora'
    ELSE 'ERROR' END;
$_$;


ALTER FUNCTION public.aurora_or_nightly(version text) OWNER TO postgres;

--
-- Name: backfill_adu(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_adu(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- stored procudure to delete and replace one day of
-- product_adu, optionally only for a specific product
-- intended to be called by backfill_matviews

DELETE FROM product_adu
WHERE adu_date = updateday;

PERFORM update_adu(updateday);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_adu(updateday date) OWNER TO postgres;

--
-- Name: backfill_all_dups(timestamp without time zone, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_all_dups(start_date timestamp without time zone, end_date timestamp without time zone) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare this_time timestamp;
    dups_found int;
begin

this_time := start_date + interval '1 hour';

    create temporary table new_reports_duplicates (
        uuid text, duplicate_of text, date_processed timestamp )
        on commit drop;

-- fill in duplicates for one-hour windows
-- advancing in 30-minute increments
while this_time <= end_date loop

    dups_found := backfill_reports_duplicates( this_time - INTERVAL '1 hour', this_time);

    RAISE INFO '% duplicates found for %',dups_found,this_time;

    this_time := this_time + interval '30 minutes';

    -- analyze once per day, just to avoid bad query plans
    IF extract('hour' FROM this_time) = 2 THEN
        analyze reports_duplicates;
    END IF;

    truncate new_reports_duplicates;

end loop;

return true;
end; $$;


ALTER FUNCTION public.backfill_all_dups(start_date timestamp without time zone, end_date timestamp without time zone) OWNER TO postgres;

--
-- Name: backfill_correlations(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_correlations(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

PERFORM update_correlations(updateday, false);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_correlations(updateday date) OWNER TO postgres;

--
-- Name: backfill_daily_crashes(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_daily_crashes(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
BEGIN
-- VERSION 4
-- deletes and replaces daily_crashes for selected dates
-- now just nests a call to update_daily_crashes

DELETE FROM daily_crashes
WHERE adu_day = updateday;
PERFORM update_daily_crashes(updateday, false);

RETURN TRUE;

END;$$;


ALTER FUNCTION public.backfill_daily_crashes(updateday date) OWNER TO postgres;

--
-- Name: backfill_hang_report(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_hang_report(backfilldate date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- delete rows
DELETE FROM daily_hangs
WHERE report_date = backfilldate;

PERFORM update_hang_report(backfilldate, false);
RETURN TRUE;

END;
$$;


ALTER FUNCTION public.backfill_hang_report(backfilldate date) OWNER TO postgres;

--
-- Name: backfill_matviews(date, date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_matviews(firstday date, lastday date DEFAULT NULL::date, reportsclean boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
    AS $$
DECLARE thisday DATE := firstday;
    last_rc timestamptz;
    first_rc timestamptz;
    last_adu DATE;
BEGIN
-- this producedure is meant to be called manually
-- by administrators in order to clear and backfill
-- the various matviews in order to recalculate old
-- data which was erroneous.
-- it requires a start date, and optionally an end date
-- no longer takes a product parameter
-- optionally disable reports_clean backfill
-- since that takes a long time

-- set start date for r_c
first_rc := firstday AT TIME ZONE 'UTC';

-- check parameters
IF firstday > current_date OR lastday > current_date THEN
    RAISE EXCEPTION 'date parameter error: cannot backfill into the future';
END IF;

-- set optional end date
IF lastday IS NULL or lastday = current_date THEN
    last_rc := date_trunc('hour', now()) - INTERVAL '3 hours';
ELSE
    last_rc := ( lastday + 1 ) AT TIME ZONE 'UTC';
END IF;

-- check if lastday is after we have ADU;
-- if so, adjust lastday
SELECT max("date")
INTO last_adu
FROM raw_adu;

IF lastday > last_adu THEN
    RAISE INFO 'last day of backfill period is after final day of ADU.  adjusting last day to %',last_adu;
    lastday := last_adu;
END IF;

-- fill in products
PERFORM update_product_versions();

-- backfill reports_clean.  this takes a while
-- we provide a switch to disable it
IF reportsclean THEN
    RAISE INFO 'backfilling reports_clean';
    PERFORM backfill_reports_clean( first_rc, last_rc );
END IF;

-- loop through the days, backfilling one at a time
WHILE thisday <= lastday LOOP
    RAISE INFO 'backfilling other matviews for %',thisday;
    RAISE INFO 'adu';
    PERFORM backfill_adu(thisday);
    RAISE INFO 'tcbs';
    PERFORM backfill_tcbs(thisday);
    DROP TABLE IF EXISTS new_tcbs;
    RAISE INFO 'daily crashes';
    PERFORM backfill_daily_crashes(thisday);
    RAISE INFO 'signatures';
    PERFORM update_signatures(thisday, FALSE);
    DROP TABLE IF EXISTS new_signatures;
    RAISE INFO 'hang report';
    PERFORM backfill_hang_report(thisday);
    RAISE INFO 'nightly builds';
    PERFORM backfill_nightly_builds(thisday);


    thisday := thisday + 1;

END LOOP;

-- finally rank_compare and correlations, which don't need to be filled in for each day
RAISE INFO 'rank_compare';
PERFORM backfill_rank_compare(lastday);
RAISE INFO 'correlations';
PERFORM backfill_correlations(lastday);

RETURN true;
END; $$;


ALTER FUNCTION public.backfill_matviews(firstday date, lastday date, reportsclean boolean) OWNER TO postgres;

--
-- Name: backfill_nightly_builds(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_nightly_builds(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM nightly_builds WHERE report_date = updateday;
PERFORM update_nightly_builds(updateday, false);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_nightly_builds(updateday date) OWNER TO postgres;

--
-- Name: backfill_one_day(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_one_day() RETURNS text
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
declare datematch text;
  reppartition text;
  bkdate date;
begin

  SELECT last_date + 1 INTO bkdate
  FROM last_backfill_temp;

  IF bkdate > '2011-08-04' THEN
    RETURN 'done';
  END IF;

  datematch := to_char(bkdate, 'YYMMDD');

  create temporary table back_one_day
  on commit drop as
  select * from releasechannel_backfill
  where uuid LIKE ( '%' || datematch );

  create index back_one_day_idx ON back_one_day(uuid);

  raise info 'temp table created';

  select relname into reppartition
  from pg_stat_user_tables
  where relname like 'reports_2011%'
    and relname <= ( 'reports_20' || datematch )
  order by relname desc limit 1;

  raise info 'updating %',reppartition;

  EXECUTE 'UPDATE ' || reppartition || ' SET release_channel = back_one_day.release_channel
    FROM back_one_day WHERE back_one_day.uuid = ' || reppartition || '.uuid;';

  UPDATE last_backfill_temp SET last_date = bkdate;

  RETURN reppartition;

END; $$;


ALTER FUNCTION public.backfill_one_day() OWNER TO postgres;

--
-- Name: backfill_one_day(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_one_day(bkdate date) RETURNS text
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
declare datematch text;
  reppartition text;
begin

  IF bkdate > '2011-08-04' THEN
    RETURN 'done';
  END IF;

  datematch := to_char(bkdate, 'YYMMDD');

  create temporary table back_one_day
  on commit drop as
  select * from releasechannel_backfill
  where uuid LIKE ( '%' || datematch );

  create index back_one_day_idx ON back_one_day(uuid);

  raise info 'temp table created';

  select relname into reppartition
  from pg_stat_user_tables
  where relname like 'reports_2011%'
    and relname <= ( 'reports_20' || datematch )
  order by relname desc limit 1;

  raise info 'updating %',reppartition;

  EXECUTE 'UPDATE ' || reppartition || ' SET release_channel = back_one_day.release_channel
    FROM back_one_day WHERE back_one_day.uuid = ' || reppartition || '.uuid;';

  UPDATE last_backfill_temp SET last_date = bkdate;

  RETURN reppartition;

END; $$;


ALTER FUNCTION public.backfill_one_day(bkdate date) OWNER TO postgres;

--
-- Name: backfill_rank_compare(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_rank_compare(updateday date DEFAULT NULL::date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

PERFORM update_rank_compare(updateday, false);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_rank_compare(updateday date) OWNER TO postgres;

--
-- Name: backfill_reports_clean(timestamp with time zone, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_reports_clean(begin_time timestamp with time zone, end_time timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- administrative utility for backfilling reports_clean to the selected date
-- intended to be called on the command line
-- uses a larger cycle (6 hours) if we have to backfill several days of data
-- note that this takes timestamptz as parameters
-- otherwise call backfill_reports_clean_by_date.
DECLARE cyclesize INTERVAL := '1 hour';
    stop_time timestamptz;
    cur_time timestamptz := begin_time;
BEGIN
    IF ( COALESCE(end_time, now()) - begin_time ) > interval '15 hours' THEN
        cyclesize := '6 hours';
    END IF;

    IF stop_time IS NULL THEN
    -- if no end time supplied, then default to three hours ago
    -- on the hour
        stop_time := ( date_trunc('hour', now()) - interval '3 hours' );
    END IF;

    WHILE cur_time < stop_time LOOP
        IF cur_time + cyclesize > stop_time THEN
            cyclesize = stop_time - cur_time;
        END IF;

        RAISE INFO 'backfilling % of reports_clean starting at %',cyclesize,cur_time;

        DELETE FROM reports_clean
        WHERE date_processed >= cur_time
            AND date_processed < ( cur_time + cyclesize );

        DELETE FROM reports_user_info
        WHERE date_processed >= cur_time
            AND date_processed < ( cur_time + cyclesize );

        PERFORM update_reports_clean( cur_time, cyclesize, false );

        cur_time := cur_time + cyclesize;
    END LOOP;

    RETURN TRUE;
END;$$;


ALTER FUNCTION public.backfill_reports_clean(begin_time timestamp with time zone, end_time timestamp with time zone) OWNER TO postgres;

--
-- Name: backfill_reports_duplicates(timestamp without time zone, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_reports_duplicates(start_time timestamp without time zone, end_time timestamp without time zone) RETURNS integer
    LANGUAGE plpgsql
    SET work_mem TO '256MB'
    SET temp_buffers TO '128MB'
    AS $$
declare new_dups INT;
begin

-- create a temporary table with the new duplicates
-- for the hour
-- this query contains the duplicate-finding algorithm
-- so it will probably change frequently

insert into new_reports_duplicates
select follower.uuid as uuid,
    leader.uuid as duplicate_of,
    follower.date_processed
from
(
select uuid,
    install_age,
    uptime,
    client_crash_date,
    date_processed,
  first_value(uuid)
  over ( partition by
            product,
            version,
            build,
            signature,
            cpu_name,
            cpu_info,
            os_name,
            os_version,
            address,
            topmost_filenames,
            reason,
            app_notes,
            url
         order by
            client_crash_date,
            uuid
        ) as leader_uuid
   from reports
   where date_processed BETWEEN start_time AND end_time
 ) as follower
JOIN
  ( select uuid, install_age, uptime, client_crash_date
    FROM reports
    where date_processed BETWEEN start_time AND end_time ) as leader
  ON follower.leader_uuid = leader.uuid
WHERE ( same_time_fuzzy(leader.client_crash_date, follower.client_crash_date,
                  leader.uptime, follower.uptime)
          OR follower.uptime < 60
      )
  AND
    same_time_fuzzy(leader.client_crash_date, follower.client_crash_date,
                  leader.install_age, follower.install_age)
  AND follower.uuid <> leader.uuid;

-- insert a copy of the leaders

insert into new_reports_duplicates
select uuid, uuid, date_processed
from reports
where uuid IN ( select duplicate_of
    from new_reports_duplicates )
    and date_processed BETWEEN start_time AND end_time;

analyze new_reports_duplicates;

select count(*) into new_dups from new_reports_duplicates;

-- insert new duplicates into permanent table

insert into reports_duplicates (uuid, duplicate_of, date_processed )
select new_reports_duplicates.*
from new_reports_duplicates
    left outer join reports_duplicates USING (uuid)
where reports_duplicates.uuid IS NULL;

-- done return number of dups found and exit
RETURN new_dups;
end;$$;


ALTER FUNCTION public.backfill_reports_duplicates(start_time timestamp without time zone, end_time timestamp without time zone) OWNER TO postgres;

--
-- Name: backfill_signature_counts(date, date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_signature_counts(begindate date, enddate date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE thisdate DATE := begindate;
BEGIN

WHILE thisdate <= enddate LOOP

    RAISE INFO 'backfilling %',thisdate;

    DELETE FROM os_signature_counts WHERE report_date = thisdate;
    DELETE FROM product_signature_counts WHERE report_date = thisdate;
    DELETE FROM uptime_signature_counts WHERE report_date = thisdate;
    PERFORM update_os_signature_counts(thisdate, false);
    PERFORM update_product_signature_counts(thisdate, false);
    PERFORM update_uptime_signature_counts(thisdate, false);

    thisdate := thisdate + 1;

END LOOP;

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_signature_counts(begindate date, enddate date) OWNER TO postgres;

--
-- Name: backfill_tcbs(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_tcbs(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- function for administrative backfilling of TCBS
-- designed to be called by backfill_matviews
DELETE FROM tcbs WHERE report_date = updateday;
PERFORM update_tcbs(updateday, false);

RETURN TRUE;
END;$$;


ALTER FUNCTION public.backfill_tcbs(updateday date) OWNER TO postgres;

--
-- Name: build_date(numeric); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION build_date(build_id numeric) RETURNS date
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts build number to a date
SELECT to_date(substr( $1::text, 1, 8 ),'YYYYMMDD');
$_$;


ALTER FUNCTION public.build_date(build_id numeric) OWNER TO postgres;

--
-- Name: build_numeric(character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION build_numeric(character varying) RETURNS numeric
    LANGUAGE sql STRICT
    AS $_$
-- safely converts a build number to a numeric type
-- if the build is not a number, returns NULL
SELECT CASE WHEN $1 ~ $x$^\d+$$x$ THEN
    $1::numeric
ELSE
    NULL::numeric
END;$_$;


ALTER FUNCTION public.build_numeric(character varying) OWNER TO postgres;

--
-- Name: check_partitions(text[], integer); Type: FUNCTION; Schema: public; Owner: monitoring
--

CREATE FUNCTION check_partitions(tables text[], numpartitions integer, OUT result integer, OUT data text) RETURNS record
    LANGUAGE plpgsql
    AS $$
DECLARE cur_partition TEXT;
partcount INT;
msg TEXT := '';
thistable TEXT;
BEGIN

result := 0;
cur_partition := to_char(now(),'YYYYMMDD');
-- tables := ARRAY['reports','extensions','frames','plugin_reports'];

FOR thistable IN SELECT * FROM unnest(tables) LOOP

SELECT count(*) INTO partcount
FROM pg_stat_user_tables
WHERE relname LIKE ( thistable || '_%' )
AND relname > ( thistable || '_' || cur_partition );

--RAISE INFO '% : %',thistable,partcount;

IF partcount < numpartitions OR partcount IS NULL THEN
result := result + 1;
msg := msg || ' ' || thistable;
END IF;

END LOOP;

IF result > 0 THEN
data := 'Some tables have no future partitions:' || msg;
END IF;

RETURN;

END; $$;


ALTER FUNCTION public.check_partitions(tables text[], numpartitions integer, OUT result integer, OUT data text) OWNER TO monitoring;

--
-- Name: citext(character); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext(character) RETURNS citext
    LANGUAGE internal IMMUTABLE STRICT
    AS $$rtrim1$$;


ALTER FUNCTION public.citext(character) OWNER TO postgres;

--
-- Name: citext(boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext(boolean) RETURNS citext
    LANGUAGE internal IMMUTABLE STRICT
    AS $$booltext$$;


ALTER FUNCTION public.citext(boolean) OWNER TO postgres;

--
-- Name: citext(inet); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext(inet) RETURNS citext
    LANGUAGE internal IMMUTABLE STRICT
    AS $$network_show$$;


ALTER FUNCTION public.citext(inet) OWNER TO postgres;

--
-- Name: citext_cmp(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_cmp(citext, citext) RETURNS integer
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_cmp';


ALTER FUNCTION public.citext_cmp(citext, citext) OWNER TO postgres;

--
-- Name: citext_eq(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_eq(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_eq';


ALTER FUNCTION public.citext_eq(citext, citext) OWNER TO postgres;

--
-- Name: citext_ge(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_ge(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_ge';


ALTER FUNCTION public.citext_ge(citext, citext) OWNER TO postgres;

--
-- Name: citext_gt(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_gt(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_gt';


ALTER FUNCTION public.citext_gt(citext, citext) OWNER TO postgres;

--
-- Name: citext_hash(citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_hash(citext) RETURNS integer
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_hash';


ALTER FUNCTION public.citext_hash(citext) OWNER TO postgres;

--
-- Name: citext_larger(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_larger(citext, citext) RETURNS citext
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_larger';


ALTER FUNCTION public.citext_larger(citext, citext) OWNER TO postgres;

--
-- Name: citext_le(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_le(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_le';


ALTER FUNCTION public.citext_le(citext, citext) OWNER TO postgres;

--
-- Name: citext_lt(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_lt(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_lt';


ALTER FUNCTION public.citext_lt(citext, citext) OWNER TO postgres;

--
-- Name: citext_ne(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_ne(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_ne';


ALTER FUNCTION public.citext_ne(citext, citext) OWNER TO postgres;

--
-- Name: citext_smaller(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_smaller(citext, citext) RETURNS citext
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_smaller';


ALTER FUNCTION public.citext_smaller(citext, citext) OWNER TO postgres;

--
-- Name: content_count_state(integer, citext, integer); Type: FUNCTION; Schema: public; Owner: breakpad_rw
--

CREATE FUNCTION content_count_state(running_count integer, process_type citext, crash_count integer) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $_$
-- allows us to do a content crash count
-- horizontally as well as vertically on tcbs
SELECT CASE WHEN $2 = 'content' THEN
  coalesce($3,0) + $1
ELSE
  $1
END; $_$;


ALTER FUNCTION public.content_count_state(running_count integer, process_type citext, crash_count integer) OWNER TO breakpad_rw;

--
-- Name: create_os_version_string(citext, integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION create_os_version_string(osname citext, major integer, minor integer) RETURNS citext
    LANGUAGE plpgsql STABLE STRICT
    AS $$
DECLARE winversion CITEXT;
BEGIN
    -- small function which produces a user-friendly
    -- string for the operating system and version
    -- if windows, look it up in windows_versions
    IF osname = 'Windows' THEN
        SELECT windows_version_name INTO winversion
        FROM windows_versions
        WHERE major_version = major AND minor_version = minor;
        IF NOT FOUND THEN
            RETURN 'Windows Unknown';
        ELSE
            RETURN winversion;
        END IF;
    ELSEIF osname = 'Mac OS X' THEN
    -- if mac, then concatinate unless the numbers are impossible
        IF major BETWEEN 10 and 11 AND minor BETWEEN 0 and 20 THEN
            RETURN 'OS X ' || major || '.' || minor;
        ELSE
            RETURN 'OS X Unknown';
        END IF;
    ELSE
    -- for other oses, just use the OS name
        RETURN osname;
    END IF;
END; $$;


ALTER FUNCTION public.create_os_version_string(osname citext, major integer, minor integer) OWNER TO postgres;

--
-- Name: create_table_if_not_exists(text, text, text, text[]); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION create_table_if_not_exists(tablename text, declaration text, tableowner text DEFAULT ''::text, indexes text[] DEFAULT '{}'::text[]) RETURNS boolean
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


ALTER FUNCTION public.create_table_if_not_exists(tablename text, declaration text, tableowner text, indexes text[]) OWNER TO postgres;

--
-- Name: create_weekly_partition(citext, date, text, text, text[], text[], text[], boolean, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION create_weekly_partition(tablename citext, theweek date, partcol text DEFAULT 'date_processed'::text, tableowner text DEFAULT ''::text, uniques text[] DEFAULT '{}'::text[], indexes text[] DEFAULT '{}'::text[], fkeys text[] DEFAULT '{}'::text[], is_utc boolean DEFAULT false, timetype text DEFAULT 'TIMESTAMP'::text) RETURNS boolean
    LANGUAGE plpgsql
    AS $_$
DECLARE dex INT := 1;
    thispart TEXT;
    zonestring TEXT := '';
    fkstring TEXT;
BEGIN
-- this function allows you to create a new weekly partition
-- of an existing master table.  it checks if the table is already
-- there and also optionally sets the ownership
-- this version of the function also creates indexes from a list of fields
-- currently only handles single-column indexes and unique declarations
-- supports date, timestamp, timestamptz/utc through the various options

    thispart := tablename || '_' || to_char(theweek, 'YYYYMMDD');

    PERFORM 1 FROM pg_stat_user_tables
    WHERE relname = thispart;
    IF FOUND THEN
        RETURN TRUE;
    END IF;

    IF is_utc THEN
        timetype := ' TIMESTAMP';
        zonestring := ' AT TIME ZONE UTC ';
    END IF;

    EXECUTE 'CREATE TABLE ' || thispart || ' ( CONSTRAINT ' || thispart
        || '_date_check CHECK ( ' || partcol || ' BETWEEN '
        || timetype || ' ' || quote_literal(to_char(theweek, 'YYYY-MM-DD'))
        || ' AND ' || timetype || ' '
        || quote_literal(to_char(theweek + 7, 'YYYY-MM-DD'))
        || ' ) ) INHERITS ( ' || tablename || ');';

    IF tableowner <> '' THEN
        EXECUTE 'ALTER TABLE ' || thispart || ' OWNER TO ' || tableowner;
    END IF;

    dex := 1;
    WHILE uniques[dex] IS NOT NULL LOOP
        EXECUTE 'CREATE UNIQUE INDEX ' || thispart || '_'
        || regexp_replace(uniques[dex], $$[,\s]+$$, '_', 'g')
        || ' ON ' || thispart || '(' || uniques[dex] || ')';
        dex := dex + 1;
    END LOOP;

    dex := 1;
    WHILE indexes[dex] IS NOT NULL LOOP
        EXECUTE 'CREATE INDEX ' || thispart || '_'
        || regexp_replace(indexes[dex], $$[,\s]+$$, '_', 'g')
        || ' ON ' || thispart || '(' || indexes[dex] || ')';
        dex := dex + 1;
    END LOOP;

    dex := 1;
    WHILE fkeys[dex] IS NOT NULL LOOP
        fkstring := regexp_replace(fkeys[dex], 'WEEKNUM', to_char(theweek, 'YYYYMMDD'), 'g');
        EXECUTE 'ALTER TABLE ' || thispart || ' ADD CONSTRAINT '
            || thispart || '_fk_' || dex || ' FOREIGN KEY '
            || fkstring || ' ON DELETE CASCADE ON UPDATE CASCADE';
        dex := dex + 1;
    END LOOP;

    RETURN TRUE;
END;
$_$;


ALTER FUNCTION public.create_weekly_partition(tablename citext, theweek date, partcol text, tableowner text, uniques text[], indexes text[], fkeys text[], is_utc boolean, timetype text) OWNER TO postgres;

--
-- Name: daily_crash_code(text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION daily_crash_code(process_type text, hangid text) RETURNS character
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT CASE
    WHEN $1 ILIKE 'content' THEN 'T'
    WHEN ( $1 IS NULL OR $1 ILIKE 'browser' ) AND $2 IS NULL THEN 'C'
    WHEN ( $1 IS NULL OR $1 ILIKE 'browser' ) AND $2 IS NOT NULL THEN 'c'
    WHEN $1 ILIKE 'plugin' AND $2 IS NULL THEN 'P'
    WHEN $1 ILIKE 'plugin' AND $2 IS NOT NULL THEN 'p'
    ELSE 'C'
    END
$_$;


ALTER FUNCTION public.daily_crash_code(process_type text, hangid text) OWNER TO postgres;

--
-- Name: drop_old_partitions(text, date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION drop_old_partitions(mastername text, cutoffdate date) RETURNS boolean
    LANGUAGE plpgsql
    AS $_X$
DECLARE tabname TEXT;
    listnames TEXT;
BEGIN
listnames := $q$SELECT relname FROM pg_stat_user_tables
        WHERE relname LIKE '$q$ || mastername || $q$_%'
        AND relname < '$q$ || mastername || '_'
        || to_char(cutoffdate, 'YYYYMMDD') || $q$'$q$;

IF try_lock_table(mastername,'ACCESS EXCLUSIVE') THEN
    FOR tabname IN EXECUTE listnames LOOP

        EXECUTE 'DROP TABLE ' || tabname;

    END LOOP;
ELSE
    RAISE EXCEPTION 'Unable to lock table plugin_reports; try again later';
END IF;
RETURN TRUE;
END;
$_X$;


ALTER FUNCTION public.drop_old_partitions(mastername text, cutoffdate date) OWNER TO postgres;

--
-- Name: edit_product_info(integer, citext, text, text, date, date, boolean, numeric, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION edit_product_info(prod_id integer, prod_name citext, prod_version text, prod_channel text, begin_visibility date, end_visibility date, is_featured boolean, crash_throttle numeric, user_name text DEFAULT ''::text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE which_t text;
    new_id INT;
    oldrec product_info_change;
    newrec product_info_change;
-- this function allows the admin UI to edit product and version
-- information regardless of which table it appears in
-- currently editing the new products is limited to
-- visibility dates and featured because of the need to supply
-- build numbers, and that we're not sure it will ever
-- be required.
-- does not validate required fields or duplicates
-- trusting to the python code and table constraints to do that

-- will be phased out when we can ignore the old productdims

BEGIN

IF prod_id IS NULL THEN
-- new entry
-- adding rows is only allowed to the old table since the new
-- table is populated automatically
-- see if this is supposed to be in the new table and error out
    PERFORM 1
    FROM products
    WHERE product_name = prod_name
        AND major_version_sort(prod_version) >= major_version_sort(rapid_release_version);
    IF FOUND AND prod_version NOT LIKE '%a%' THEN
        RAISE EXCEPTION 'Product % version % will be automatically updated by the new system.  As such, you may not add this product & version manually.',prod_name,prod_version;
    ELSE

        INSERT INTO productdims ( product, version, branch, release )
        VALUES ( prod_name, prod_version, '2.2',
            CASE WHEN prod_channel ILIKE 'beta' THEN 'milestone'::release_enum
                WHEN prod_channel ILIKE 'aurora' THEN 'development'::release_enum
                WHEN prod_channel ILIKE 'nightly' THEN 'development'::release_enum
                ELSE 'major' END )
        RETURNING id
        INTO new_id;

        INSERT INTO product_visibility ( productdims_id, start_date, end_date, featured, throttle )
        VALUES ( new_id, begin_visibility, end_visibility, is_featured, crash_throttle );

    END IF;

ELSE

-- first, find out whether we're dealing with the old or new table
    SELECT which_table INTO which_t
    FROM product_info WHERE product_version_id = prod_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No product with that ID was found.  Database Error.';
    END IF;

    IF which_t = 'new' THEN
        -- note that changes to the product name or version will be ignored
        -- only changes to featured and visibility dates will be taken

        -- first we're going to log this since we've had some issues
        -- and we want to track updates
        INSERT INTO product_info_changelog (
            product_version_id, user_name, changed_on,
            oldrec, newrec )
        SELECT prod_id, user_name, now(),
            row( build_date, sunset_date,
                featured_version, throttle )::product_info_change,
            row( begin_visibility, end_visibility,
                is_featured, crash_throttle/100 )::product_info_change
        FROM product_versions JOIN product_release_channels
            ON product_versions.product_name = product_release_channels.product_name
            AND product_versions.build_type = product_release_channels.release_channel
        WHERE product_version_id = prod_id;

        -- then update
        UPDATE product_versions SET
            featured_version = is_featured,
            build_date = begin_visibility,
            sunset_date = end_visibility
        WHERE product_version_id = prod_id;

        UPDATE product_release_channels
        SET throttle = crash_throttle / 100
        WHERE product_name = prod_name
            AND release_channel = prod_channel;

        new_id := prod_id;
    ELSE
        UPDATE productdims SET
            product = prod_name,
            version = prod_version,
            release = ( CASE WHEN prod_channel ILIKE 'beta' THEN 'milestone'::release_enum
                WHEN prod_channel ILIKE 'aurora' THEN 'development'::release_enum
                WHEN prod_channel ILIKE 'nightly' THEN 'development'::release_enum
                ELSE 'major' END )
        WHERE id = prod_id;

        UPDATE product_visibility SET
            featured = is_featured,
            start_date = begin_visibility,
            end_date = end_visibility,
            throttle = crash_throttle
        WHERE productdims_id = prod_id;

        new_id := prod_id;
    END IF;
END IF;

RETURN new_id;
END; $$;


ALTER FUNCTION public.edit_product_info(prod_id integer, prod_name citext, prod_version text, prod_channel text, begin_visibility date, end_visibility date, is_featured boolean, crash_throttle numeric, user_name text) OWNER TO postgres;

--
-- Name: get_cores(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION get_cores(cpudetails text) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT substring($1 from $x$\| (\d+)$$x$)::INT;
$_$;


ALTER FUNCTION public.get_cores(cpudetails text) OWNER TO postgres;

--
-- Name: get_product_version_ids(citext, citext[]); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION get_product_version_ids(product citext, VARIADIC versions citext[]) RETURNS integer[]
    LANGUAGE sql
    AS $_$
SELECT array_agg(product_version_id)
FROM product_versions
    WHERE product_name = $1
    AND version_string = ANY ( $2 );
$_$;


ALTER FUNCTION public.get_product_version_ids(product citext, VARIADIC versions citext[]) OWNER TO postgres;

--
-- Name: initcap(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION initcap(text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT upper(substr($1,1,1)) || substr($1,2);
$_$;


ALTER FUNCTION public.initcap(text) OWNER TO postgres;

--
-- Name: last_record(text); Type: FUNCTION; Schema: public; Owner: monitoring
--

CREATE FUNCTION last_record(tablename text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
declare curdate timestamp;
  resdate timestamp;
  ressecs integer;
begin

CASE WHEN tablename = 'reports' THEN
  curdate:= now() - INTERVAL '3 days';
  EXECUTE 'SELECT max(date_processed)
  FROM reports
  WHERE date_processed > ' ||
        quote_literal(to_char(curdate, 'YYYY-MM-DD'))
        || ' and date_processed < ' ||
        quote_literal(to_char(curdate + INTERVAL '4 days','YYYY-MM-DD'))
    INTO resdate;
  IF resdate IS NULL THEN
     resdate := curdate;
  END IF;
WHEN tablename = 'top_crashes_by_signature' THEN
  SELECT max(window_end)
  INTO resdate
  FROM top_crashes_by_signature;
WHEN tablename = 'top_crashes_by_url' THEN
  SELECT max(window_end)
  INTO resdate
  FROM top_crashes_by_url;
ELSE
  resdate:= null;
END CASE;

ressecs := round(EXTRACT('epoch' FROM ( now() - resdate )))::INT;

RETURN ressecs;

END;$$;


ALTER FUNCTION public.last_record(tablename text) OWNER TO monitoring;

--
-- Name: log_priorityjobs(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION log_priorityjobs() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
declare arewelogging boolean;
begin
SELECT log_jobs INTO arewelogging
FROM priorityjobs_logging_switch;
IF arewelogging THEN
INSERT INTO priorityjobs_log VALUES ( NEW.uuid );
END IF;
RETURN NEW;
end; $$;


ALTER FUNCTION public.log_priorityjobs() OWNER TO postgres;

--
-- Name: major_version(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION major_version(version text) RETURNS major_version
    LANGUAGE sql IMMUTABLE
    AS $_$
-- turns a version string into a major version
-- i.e. "6.0a2" into "6.0"
SELECT substring($1 from $x$^(\d+.\d+)$x$)::major_version;
$_$;


ALTER FUNCTION public.major_version(version text) OWNER TO postgres;

--
-- Name: major_version_sort(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION major_version_sort(version text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts a major_version string into a padded,
-- sortable string
select version_sort_digit( substring($1 from $x$^(\d+)$x$) )
    || version_sort_digit( substring($1 from $x$^\d+\.(\d+)$x$) );
$_$;


ALTER FUNCTION public.major_version_sort(version text) OWNER TO postgres;

--
-- Name: old_version_sort(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION old_version_sort(vers text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT to_char( matched[1]::int, 'FM000' )
    || to_char( matched[2]::int, 'FM000' )
    || to_char( coalesce( matched[4]::int, 0 ), 'FM000' )
    || CASE WHEN matched[3] <> '' THEN 'b'
        WHEN matched[5] <> '' THEN 'b'
        ELSE 'z' END
    || '000'
FROM ( SELECT regexp_matches($1,
$x$^(\d+)[^\d]*\.(\d+)([a-z]?)[^\.]*(?:\.(\d+))?([a-z]?).*$$x$) as matched) as match
LIMIT 1;
$_$;


ALTER FUNCTION public.old_version_sort(vers text) OWNER TO postgres;

--
-- Name: pacific2ts(timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION pacific2ts(timestamp with time zone) RETURNS timestamp without time zone
    LANGUAGE sql STABLE
    SET "TimeZone" TO 'America/Los_Angeles'
    AS $_$
SELECT $1::timestamp;
$_$;


ALTER FUNCTION public.pacific2ts(timestamp with time zone) OWNER TO postgres;

--
-- Name: pg_stat_statements(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION pg_stat_statements(OUT userid oid, OUT dbid oid, OUT query text, OUT calls bigint, OUT total_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint) RETURNS SETOF record
    LANGUAGE c
    AS '$libdir/pg_stat_statements', 'pg_stat_statements';


ALTER FUNCTION public.pg_stat_statements(OUT userid oid, OUT dbid oid, OUT query text, OUT calls bigint, OUT total_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint) OWNER TO postgres;

--
-- Name: pg_stat_statements_reset(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION pg_stat_statements_reset() RETURNS void
    LANGUAGE c
    AS '$libdir/pg_stat_statements', 'pg_stat_statements_reset';


ALTER FUNCTION public.pg_stat_statements_reset() OWNER TO postgres;

--
-- Name: plugin_count_state(integer, citext, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION plugin_count_state(running_count integer, process_type citext, crash_count integer) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $_$
-- allows us to do a plugn count horizontally
-- as well as vertically on tcbs
SELECT CASE WHEN $2 = 'plugin' THEN
  coalesce($3,0) + $1
ELSE
  $1
END; $_$;


ALTER FUNCTION public.plugin_count_state(running_count integer, process_type citext, crash_count integer) OWNER TO postgres;

--
-- Name: product_version_sort_number(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION product_version_sort_number(sproduct text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- reorders the product-version list for a specific
-- product after an update
-- we just reorder the whole group rather than doing
-- something more fine-tuned because it's actually less
-- work for the database and more foolproof.

UPDATE productdims SET sort_key = new_sort
FROM  ( SELECT product, version,
row_number() over ( partition by product
order by sec1_num1 ASC NULLS FIRST,
sec1_string1 ASC NULLS LAST,
sec1_num2 ASC NULLS FIRST,
sec1_string2 ASC NULLS LAST,
sec1_num1 ASC NULLS FIRST,
sec1_string1 ASC NULLS LAST,
sec1_num2 ASC NULLS FIRST,
sec1_string2 ASC NULLS LAST,
sec1_num1 ASC NULLS FIRST,
sec1_string1 ASC NULLS LAST,
sec1_num2 ASC NULLS FIRST,
sec1_string2 ASC NULLS LAST,
extra ASC NULLS FIRST)
as new_sort
 FROM productdims_version_sort
 WHERE product = sproduct )
AS product_resort
WHERE productdims.product = product_resort.product
AND productdims.version = product_resort.version
AND ( sort_key <> new_sort OR sort_key IS NULL );

RETURN TRUE;
END;$$;


ALTER FUNCTION public.product_version_sort_number(sproduct text) OWNER TO postgres;

--
-- Name: regexp_matches(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_matches(citext, citext) RETURNS text[]
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_matches( $1::pg_catalog.text, $2::pg_catalog.text, 'i' );
$_$;


ALTER FUNCTION public.regexp_matches(citext, citext) OWNER TO postgres;

--
-- Name: regexp_matches(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_matches(citext, citext, text) RETURNS text[]
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_matches( $1::pg_catalog.text, $2::pg_catalog.text, CASE WHEN pg_catalog.strpos($3, 'c') = 0 THEN  $3 || 'i' ELSE $3 END );
$_$;


ALTER FUNCTION public.regexp_matches(citext, citext, text) OWNER TO postgres;

--
-- Name: regexp_replace(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_replace(citext, citext, text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_replace( $1::pg_catalog.text, $2::pg_catalog.text, $3, 'i');
$_$;


ALTER FUNCTION public.regexp_replace(citext, citext, text) OWNER TO postgres;

--
-- Name: regexp_replace(citext, citext, text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_replace(citext, citext, text, text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_replace( $1::pg_catalog.text, $2::pg_catalog.text, $3, CASE WHEN pg_catalog.strpos($4, 'c') = 0 THEN  $4 || 'i' ELSE $4 END);
$_$;


ALTER FUNCTION public.regexp_replace(citext, citext, text, text) OWNER TO postgres;

--
-- Name: regexp_split_to_array(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_split_to_array(citext, citext) RETURNS text[]
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_split_to_array( $1::pg_catalog.text, $2::pg_catalog.text, 'i' );
$_$;


ALTER FUNCTION public.regexp_split_to_array(citext, citext) OWNER TO postgres;

--
-- Name: regexp_split_to_array(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_split_to_array(citext, citext, text) RETURNS text[]
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_split_to_array( $1::pg_catalog.text, $2::pg_catalog.text, CASE WHEN pg_catalog.strpos($3, 'c') = 0 THEN  $3 || 'i' ELSE $3 END );
$_$;


ALTER FUNCTION public.regexp_split_to_array(citext, citext, text) OWNER TO postgres;

--
-- Name: regexp_split_to_table(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_split_to_table(citext, citext) RETURNS SETOF text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_split_to_table( $1::pg_catalog.text, $2::pg_catalog.text, 'i' );
$_$;


ALTER FUNCTION public.regexp_split_to_table(citext, citext) OWNER TO postgres;

--
-- Name: regexp_split_to_table(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_split_to_table(citext, citext, text) RETURNS SETOF text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_split_to_table( $1::pg_catalog.text, $2::pg_catalog.text, CASE WHEN pg_catalog.strpos($3, 'c') = 0 THEN  $3 || 'i' ELSE $3 END );
$_$;


ALTER FUNCTION public.regexp_split_to_table(citext, citext, text) OWNER TO postgres;

--
-- Name: replace(citext, citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION replace(citext, citext, citext) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_replace( $1::pg_catalog.text, pg_catalog.regexp_replace($2::pg_catalog.text, '([^a-zA-Z_0-9])', E'\\\\\\1', 'g'), $3::pg_catalog.text, 'gi' );
$_$;


ALTER FUNCTION public.replace(citext, citext, citext) OWNER TO postgres;

--
-- Name: reports_clean_done(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION reports_clean_done(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function checks that reports_clean has been updated
-- all the way to the last hour of the UTC day
BEGIN

PERFORM 1
    FROM reports_clean
    WHERE date_processed BETWEEN ( ( updateday::timestamp at time zone 'utc' ) + interval '23 hours' )
        AND ( ( updateday::timestamp at time zone 'utc' ) + interval '1 day' )
    LIMIT 1;
IF FOUND THEN
    RETURN TRUE;
ELSE
    RETURN FALSE;
END IF;
END; $$;


ALTER FUNCTION public.reports_clean_done(updateday date) OWNER TO postgres;

--
-- Name: reports_clean_weekly_partition(timestamp with time zone, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION reports_clean_weekly_partition(this_date timestamp with time zone, which_table text) RETURNS text
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
    AS $_$
-- this function, meant to be called internally
-- checks if the correct reports_clean or reports_user_info partition exists
-- otherwise it creates it
-- returns the name of the partition
declare this_part text;
    begin_week text;
    end_week text;
    rc_indexes text[];
    dex int := 1;
begin
    this_part := which_table || '_' || to_char(date_trunc('week', this_date), 'YYYYMMDD');
    begin_week := to_char(date_trunc('week', this_date), 'YYYY-MM-DD');
    end_week := to_char(date_trunc('week', this_date) + interval '1 week', 'YYYY-MM-DD');

    PERFORM 1
    FROM pg_stat_user_tables
    WHERE relname = this_part;
    IF FOUND THEN
        RETURN this_part;
    END IF;

    EXECUTE 'CREATE TABLE ' || this_part || $$
        ( CONSTRAINT date_processed_week CHECK ( date_processed >= '$$ || begin_week || $$'::timestamp AT TIME ZONE 'UTC'
            AND date_processed < '$$ || end_week || $$'::timestamp AT TIME ZONE 'UTC' ) )
        INHERITS ( $$ || which_table || $$ );$$;
    EXECUTE 'CREATE UNIQUE INDEX ' || this_part || '_uuid ON ' || this_part || '(uuid);';

    IF which_table = 'reports_clean' THEN

        rc_indexes := ARRAY[ 'date_processed', 'product_version_id', 'os_name', 'os_version_id',
            'signature_id', 'address_id', 'flash_version_id', 'hang_id', 'process_type', 'release_channel', 'domain_id' ];

        EXECUTE 'CREATE INDEX ' || this_part || '_sig_prod_date ON ' || this_part
            || '( signature_id, product_version_id, date_processed )';

        EXECUTE 'CREATE INDEX ' || this_part || '_arch_cores ON ' || this_part
            || '( architecture, cores )';

    ELSEIF which_table = 'reports_user_info' THEN

        rc_indexes := '{}';

    END IF;

    WHILE rc_indexes[dex] IS NOT NULL LOOP
        EXECUTE 'CREATE INDEX ' || this_part || '_' || rc_indexes[dex]
            || ' ON ' || this_part || '(' || rc_indexes[dex] || ');';
        dex := dex + 1;
    END LOOP;

    EXECUTE 'ALTER TABLE ' || this_part || ' OWNER TO breakpad_rw';

    RETURN this_part;
end;$_$;


ALTER FUNCTION public.reports_clean_weekly_partition(this_date timestamp with time zone, which_table text) OWNER TO postgres;

--
-- Name: same_time_fuzzy(timestamp with time zone, timestamp with time zone, integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION same_time_fuzzy(date1 timestamp with time zone, date2 timestamp with time zone, interval_secs1 integer, interval_secs2 integer) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT
-- return true if either interval is null
-- so we don't exclude crashes missing data
CASE WHEN $3 IS NULL THEN
    TRUE
WHEN $4 IS NULL THEN
    TRUE
-- otherwise check that the two timestamp deltas
-- and the two interval deltas are within 60 sec
-- of each other
ELSE
    (
        extract ('epoch' from ( $2 - $1 ) ) -
        ( $4 - $3 )
    ) BETWEEN -60 AND 60
END;
$_$;


ALTER FUNCTION public.same_time_fuzzy(date1 timestamp with time zone, date2 timestamp with time zone, interval_secs1 integer, interval_secs2 integer) OWNER TO postgres;

--
-- Name: split_part(citext, citext, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION split_part(citext, citext, integer) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT (pg_catalog.regexp_split_to_array( $1::pg_catalog.text, pg_catalog.regexp_replace($2::pg_catalog.text, '([^a-zA-Z_0-9])', E'\\\\\\1', 'g'), 'i'))[$3];
$_$;


ALTER FUNCTION public.split_part(citext, citext, integer) OWNER TO postgres;

--
-- Name: strpos(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION strpos(citext, citext) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.strpos( pg_catalog.lower( $1::pg_catalog.text ), pg_catalog.lower( $2::pg_catalog.text ) );
$_$;


ALTER FUNCTION public.strpos(citext, citext) OWNER TO postgres;

--
-- Name: sunset_date(numeric, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION sunset_date(build_id numeric, build_type citext) RETURNS date
    LANGUAGE sql IMMUTABLE
    AS $_$
-- sets a sunset date for visibility
-- based on a build number
-- current spec is 18 weeks for releases
-- 9 weeks for everything else
select ( build_date($1) +
    case when $2 = 'release'
        then interval '18 weeks'
    when $2 = 'ESR'
        then interval '18 weeks'
    else
        interval '9 weeks'
    end ) :: date
$_$;


ALTER FUNCTION public.sunset_date(build_id numeric, build_type citext) OWNER TO postgres;

--
-- Name: texticlike(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticlike(citext, citext) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticlike$$;


ALTER FUNCTION public.texticlike(citext, citext) OWNER TO postgres;

--
-- Name: texticlike(citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticlike(citext, text) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticlike$$;


ALTER FUNCTION public.texticlike(citext, text) OWNER TO postgres;

--
-- Name: texticnlike(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticnlike(citext, citext) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticnlike$$;


ALTER FUNCTION public.texticnlike(citext, citext) OWNER TO postgres;

--
-- Name: texticnlike(citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticnlike(citext, text) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticnlike$$;


ALTER FUNCTION public.texticnlike(citext, text) OWNER TO postgres;

--
-- Name: texticregexeq(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticregexeq(citext, citext) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticregexeq$$;


ALTER FUNCTION public.texticregexeq(citext, citext) OWNER TO postgres;

--
-- Name: texticregexeq(citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticregexeq(citext, text) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticregexeq$$;


ALTER FUNCTION public.texticregexeq(citext, text) OWNER TO postgres;

--
-- Name: texticregexne(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticregexne(citext, citext) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticregexne$$;


ALTER FUNCTION public.texticregexne(citext, citext) OWNER TO postgres;

--
-- Name: texticregexne(citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticregexne(citext, text) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticregexne$$;


ALTER FUNCTION public.texticregexne(citext, text) OWNER TO postgres;

--
-- Name: tokenize_version(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION tokenize_version(version text, OUT s1n1 integer, OUT s1s1 text, OUT s1n2 integer, OUT s1s2 text, OUT s2n1 integer, OUT s2s1 text, OUT s2n2 integer, OUT s2s2 text, OUT s3n1 integer, OUT s3s1 text, OUT s3n2 integer, OUT s3s2 text, OUT ext text) RETURNS record
    LANGUAGE plperl
    AS $_X$
    my $version = shift;
    my @parts = split /[.]/ => $version;
    my $extra;
    if (@parts > 3) {
        $extra = join '.', @parts[3..$#parts];
        @parts = @parts[0..2];
    }

    my @tokens;
    for my $part (@parts) {
        die "$version is not a valid toolkit version" unless $part =~ qr{\A
            ([-]?\d+)                    # number-a
            (?:
                ([-_a-zA-Z]+(?=-|\d|\z)) # string-b
                (?:
                    (-?\d+)              # number-c
                    (?:
                        ([^-*+\s]+)      # string-d
                    |\z)
                |\z)
            |\z)
        \z}x;
        push @tokens, $1, $2, $3, $4;
    }

    die "$version is not a valid toolkit version" unless @tokens;
    my @cols = qw(s1n1 s1s1 s1n2 s1s2 s2n1 s2s1 s2n2 s2s2 s3n1 s3s1 s3n2 s3s2 ext);
    return { ext => $extra, map { $cols[$_] => $tokens[$_] } 0..11 }
$_X$;


ALTER FUNCTION public.tokenize_version(version text, OUT s1n1 integer, OUT s1s1 text, OUT s1n2 integer, OUT s1s2 text, OUT s2n1 integer, OUT s2s1 text, OUT s2n2 integer, OUT s2s2 text, OUT s3n1 integer, OUT s3s1 text, OUT s3n2 integer, OUT s3s2 text, OUT ext text) OWNER TO postgres;

--
-- Name: transform_rules_insert_order(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION transform_rules_insert_order() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE order_num INT;
-- this trigger function makes sure that all rules have a unique order
-- within their category, and assigns an order number to new rules
BEGIN
    IF NEW.rule_order IS NULL or NEW.rule_order = 0 THEN
        -- no order supplied, add the rule to the end
        SELECT max(rule_order)
        INTO order_num
        FROM transform_rules
        WHERE category = NEW.category;

        NEW.rule_order := COALESCE(order_num, 0) + 1;
    ELSE
        -- check if there's already a gap there
        PERFORM rule_order
        FROM transform_rules
        WHERE category = NEW.category
            AND rule_order = NEW.rule_order;
        -- if not, then bump up
        IF FOUND THEN
            UPDATE transform_rules
            SET rule_order = rule_order + 1
            WHERE category = NEW.category
                AND rule_order = NEW.rule_order;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.transform_rules_insert_order() OWNER TO postgres;

--
-- Name: transform_rules_update_order(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION transform_rules_update_order() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- if we've changed the order number, or category reorder
    IF NEW.rule_order <> OLD.rule_order
        OR NEW.category <> OLD.category THEN

        -- insert a new gap
        UPDATE transform_rules
        SET rule_order = rule_order + 1
        WHERE category = NEW.category
            AND rule_order = NEW.rule_order
            AND transform_rule_id <> NEW.transform_rule_id;

    END IF;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.transform_rules_update_order() OWNER TO postgres;

--
-- Name: translate(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION translate(citext, citext, text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.translate( pg_catalog.translate( $1::pg_catalog.text, pg_catalog.lower($2::pg_catalog.text), $3), pg_catalog.upper($2::pg_catalog.text), $3);
$_$;


ALTER FUNCTION public.translate(citext, citext, text) OWNER TO postgres;

--
-- Name: try_lock_table(text, text, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION try_lock_table(tabname text, mode text DEFAULT 'EXCLUSIVE'::text, attempts integer DEFAULT 20) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function tries to lock a table
-- in a loop, retrying every 3 seconds for 20 tries
-- until it gets a lock
-- or gives up
-- returns true if the table is locked, false
-- if unable to lock
DECLARE loopno INT := 1;
BEGIN
    WHILE loopno < attempts LOOP
        BEGIN
            EXECUTE 'LOCK TABLE ' || tabname || ' IN ' || mode || ' MODE NOWAIT';
            RETURN TRUE;
        EXCEPTION
            WHEN LOCK_NOT_AVAILABLE THEN
                PERFORM pg_sleep(3);
                CONTINUE;
        END;
    END LOOP;
RETURN FALSE;
END;$$;


ALTER FUNCTION public.try_lock_table(tabname text, mode text, attempts integer) OWNER TO postgres;

--
-- Name: tstz_between(timestamp with time zone, date, date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION tstz_between(tstz timestamp with time zone, bdate date, fdate date) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT $1 >= ( $2::timestamp AT TIME ZONE 'UTC' )
    AND $1 < ( ( $3 + 1 )::timestamp AT TIME ZONE 'UTC' );
$_$;


ALTER FUNCTION public.tstz_between(tstz timestamp with time zone, bdate date, fdate date) OWNER TO postgres;

--
-- Name: update_adu(date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_adu(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
BEGIN
-- daily batch update procedure to update the
-- adu-product matview, used to power graphs
-- gets its data from raw_adu, which is populated
-- daily by metrics

-- check if raw_adu has been updated.  otherwise, abort.
PERFORM 1 FROM raw_adu
WHERE "date" = updateday
LIMIT 1;

IF NOT FOUND THEN
    IF checkdata THEN
        RAISE EXCEPTION 'raw_adu not updated for %',updateday;
    ELSE
        RETURN TRUE;
    END IF;
END IF;

-- check if ADU has already been run for the date
IF checkdata THEN
    PERFORM 1 FROM product_adu
    WHERE adu_date = updateday LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION 'update_adu has already been r
