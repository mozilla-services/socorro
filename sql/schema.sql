-- This Source Code Form is subject to the terms of the Mozilla Public
-- License, v. 2.0. If a copy of the MPL was not distributed with this
-- file, You can obtain one at http://mozilla.org/MPL/2.0/.
--
-- PostgreSQL database dump
--

-- Dumped from database version 9.0.8
-- Dumped by pg_dump version 9.0.8
-- Started on 2012-07-25 14:19:19 PDT

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

--
-- TOC entry 1421 (class 0 OID 0)
-- Name: citext; Type: SHELL TYPE; Schema: public; Owner: postgres
--

CREATE TYPE citext;


--
-- TOC entry 279 (class 1255 OID 80989)
-- Dependencies: 7 1421
-- Name: citextin(cstring); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citextin(cstring) RETURNS citext
    LANGUAGE internal IMMUTABLE STRICT
    AS $$textin$$;


ALTER FUNCTION public.citextin(cstring) OWNER TO postgres;

--
-- TOC entry 280 (class 1255 OID 80990)
-- Dependencies: 7 1421
-- Name: citextout(citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citextout(citext) RETURNS cstring
    LANGUAGE internal IMMUTABLE STRICT
    AS $$textout$$;


ALTER FUNCTION public.citextout(citext) OWNER TO postgres;

--
-- TOC entry 281 (class 1255 OID 80991)
-- Dependencies: 7 1421
-- Name: citextrecv(internal); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citextrecv(internal) RETURNS citext
    LANGUAGE internal STABLE STRICT
    AS $$textrecv$$;


ALTER FUNCTION public.citextrecv(internal) OWNER TO postgres;

--
-- TOC entry 282 (class 1255 OID 80992)
-- Dependencies: 7 1421
-- Name: citextsend(citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citextsend(citext) RETURNS bytea
    LANGUAGE internal STABLE STRICT
    AS $$textsend$$;


ALTER FUNCTION public.citextsend(citext) OWNER TO postgres;

--
-- TOC entry 1420 (class 1247 OID 80988)
-- Dependencies: 282 7 279 280 281
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
-- TOC entry 1424 (class 1247 OID 80994)
-- Dependencies: 1425 7
-- Name: major_version; Type: DOMAIN; Schema: public; Owner: breakpad_rw
--

CREATE DOMAIN major_version AS text
	CONSTRAINT major_version_check CHECK ((VALUE ~ '^\\d+\\.\\d+'::text));


ALTER DOMAIN public.major_version OWNER TO breakpad_rw;

--
-- TOC entry 1426 (class 1247 OID 80998)
-- Dependencies: 7 146
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
-- TOC entry 1429 (class 1247 OID 81000)
-- Dependencies: 7
-- Name: release_enum; Type: TYPE; Schema: public; Owner: breakpad_rw
--

CREATE TYPE release_enum AS ENUM (
    'major',
    'milestone',
    'development'
);


ALTER TYPE public.release_enum OWNER TO breakpad_rw;

--
-- TOC entry 283 (class 1255 OID 81004)
-- Dependencies: 1826 7
-- Name: add_column_if_not_exists(text, text, text, boolean, text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION add_column_if_not_exists(tablename text, columnname text, datatype text, nonnull boolean DEFAULT false, defaultval text DEFAULT ''::text, constrainttext text DEFAULT ''::text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
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

END;$$;


ALTER FUNCTION public.add_column_if_not_exists(tablename text, columnname text, datatype text, nonnull boolean, defaultval text, constrainttext text) OWNER TO postgres;

--
-- TOC entry 1131 (class 1255 OID 89100)
-- Dependencies: 1420 1826 7 1420 1420 1420
-- Name: add_new_release(citext, citext, citext, numeric, citext, integer, text, boolean, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION add_new_release(product citext, version citext, release_channel citext, build_id numeric, platform citext, beta_number integer DEFAULT NULL::integer, repository text DEFAULT 'release'::text, update_products boolean DEFAULT false, ignore_duplicates boolean DEFAULT false) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE rname citext;
BEGIN
-- adds a new release to the releases_raw table
-- to be picked up by update_products later
-- does some light format validation

-- check for NULLs, blanks
IF NOT ( nonzero_string(product) AND nonzero_string(version)
	AND nonzero_string(release_channel) and nonzero_string(platform)
	AND build_id IS NOT NULL ) THEN
	RAISE EXCEPTION 'product, version, release_channel, platform and build ID are all required';
END IF;

-- product
-- what we get could be a product name or a release name.  depending, we want to insert the
-- release name
SELECT release_name INTO rname
FROM products WHERE release_name = product;
IF rname IS NULL THEN
	SELECT release_name INTO rname
	FROM products WHERE product_name = product;
	IF rname IS NULL THEN
		RAISE EXCEPTION 'You must supply a valid product or product release name';
	END IF;
END IF;

--validate channel
PERFORM validate_lookup('release_channels','release_channel',release_channel,'release channel');
--validate build
IF NOT ( build_date(build_id) BETWEEN '2005-01-01'
	AND (current_date + INTERVAL '1 month') ) THEN
	RAISE EXCEPTION 'invalid buildid';
END IF;

--add row
--duplicate check will occur in the EXECEPTION section
INSERT INTO releases_raw (
	product_name, version, platform, build_id,
	build_type, beta_number, repository )
VALUES ( rname, version, platform, build_id,
	release_channel, beta_number, repository );

--call update_products, if desired
IF update_products THEN
	PERFORM update_product_versions();
END IF;

--return
RETURN TRUE;

--exception clause, mainly catches duplicate rows.
EXCEPTION
	WHEN UNIQUE_VIOLATION THEN
		IF ignore_duplicates THEN
			RETURN FALSE;
		ELSE
			RAISE EXCEPTION 'the release you have entered is already present in he database';
		END IF;
END;$$;


ALTER FUNCTION public.add_new_release(product citext, version citext, release_channel citext, build_id numeric, platform citext, beta_number integer, repository text, update_products boolean, ignore_duplicates boolean) OWNER TO postgres;

--
-- TOC entry 284 (class 1255 OID 81006)
-- Dependencies: 1429 7 1826 1429
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
-- TOC entry 285 (class 1255 OID 81007)
-- Dependencies: 7
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
-- TOC entry 291 (class 1255 OID 81008)
-- Dependencies: 7 1826
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

PERFORM update_adu(updateday, false);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_adu(updateday date) OWNER TO postgres;

--
-- TOC entry 286 (class 1255 OID 81009)
-- Dependencies: 1826 7
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
-- TOC entry 505 (class 1255 OID 84554)
-- Dependencies: 1826 7
-- Name: backfill_build_adu(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_build_adu(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM build_adu WHERE adu_date = updateday;
PERFORM update_build_adu(updateday, false);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_build_adu(updateday date) OWNER TO postgres;

--
-- TOC entry 287 (class 1255 OID 81010)
-- Dependencies: 1826 7
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
-- TOC entry 526 (class 1255 OID 84595)
-- Dependencies: 7 1826
-- Name: backfill_crashes_by_user(date, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_crashes_by_user(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM crashes_by_user WHERE report_date = updateday;
PERFORM update_crashes_by_user(updateday, false, check_period);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_crashes_by_user(updateday date, check_period interval) OWNER TO postgres;

--
-- TOC entry 528 (class 1255 OID 84615)
-- Dependencies: 7 1826
-- Name: backfill_crashes_by_user_build(date, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_crashes_by_user_build(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM crashes_by_user_build WHERE report_date = updateday;
PERFORM update_crashes_by_user_build(updateday, false, check_period);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_crashes_by_user_build(updateday date, check_period interval) OWNER TO postgres;

--
-- TOC entry 288 (class 1255 OID 81011)
-- Dependencies: 1826 7
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
-- TOC entry 289 (class 1255 OID 81012)
-- Dependencies: 7 1826
-- Name: backfill_explosiveness(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_explosiveness(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

PERFORM update_explosiveness(updateday, false);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_explosiveness(updateday date) OWNER TO postgres;

--
-- TOC entry 290 (class 1255 OID 81013)
-- Dependencies: 7 1826
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
-- TOC entry 530 (class 1255 OID 84632)
-- Dependencies: 7 1826
-- Name: backfill_home_page_graph(date, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_home_page_graph(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM home_page_graph WHERE report_date = updateday;
PERFORM update_home_page_graph(updateday, false, check_period);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_home_page_graph(updateday date, check_period interval) OWNER TO postgres;

--
-- TOC entry 535 (class 1255 OID 84646)
-- Dependencies: 1826 7
-- Name: backfill_home_page_graph_build(date, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_home_page_graph_build(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

DELETE FROM home_page_graph_build WHERE report_date = updateday;
PERFORM update_home_page_graph_build(updateday, false, check_period);

RETURN TRUE;
END; $$;


ALTER FUNCTION public.backfill_home_page_graph_build(updateday date, check_period interval) OWNER TO postgres;

--
-- TOC entry 312 (class 1255 OID 81014)
-- Dependencies: 1826 7
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
-- TOC entry 313 (class 1255 OID 81015)
-- Dependencies: 1826 7
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
-- TOC entry 314 (class 1255 OID 81016)
-- Dependencies: 7 1826
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
-- TOC entry 315 (class 1255 OID 81017)
-- Dependencies: 1826 7
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
-- TOC entry 316 (class 1255 OID 81018)
-- Dependencies: 7 1826
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
-- TOC entry 317 (class 1255 OID 81019)
-- Dependencies: 7 1826
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
-- TOC entry 318 (class 1255 OID 81020)
-- Dependencies: 7 1826
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
-- TOC entry 319 (class 1255 OID 81021)
-- Dependencies: 1826 7
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
-- TOC entry 523 (class 1255 OID 84543)
-- Dependencies: 7 1826
-- Name: backfill_tcbs(date, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_tcbs(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- function for administrative backfilling of TCBS
-- designed to be called by backfill_matviews
DELETE FROM tcbs WHERE report_date = updateday;
PERFORM update_tcbs(updateday, false, check_period);

RETURN TRUE;
END;$$;


ALTER FUNCTION public.backfill_tcbs(updateday date, check_period interval) OWNER TO postgres;

--
-- TOC entry 524 (class 1255 OID 84544)
-- Dependencies: 1826 7
-- Name: backfill_tcbs_build(date, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION backfill_tcbs_build(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- function for administrative backfilling of TCBS
-- designed to be called by backfill_matviews
DELETE FROM tcbs_build WHERE report_date = updateday;
PERFORM update_tcbs_build(updateday, false, check_period);

RETURN TRUE;
END;$$;


ALTER FUNCTION public.backfill_tcbs_build(updateday date, check_period interval) OWNER TO postgres;

--
-- TOC entry 320 (class 1255 OID 81023)
-- Dependencies: 7
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
-- TOC entry 321 (class 1255 OID 81024)
-- Dependencies: 7
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
-- TOC entry 322 (class 1255 OID 81025)
-- Dependencies: 7 1826
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
-- TOC entry 323 (class 1255 OID 81026)
-- Dependencies: 1420 7
-- Name: citext(character); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext(character) RETURNS citext
    LANGUAGE internal IMMUTABLE STRICT
    AS $$rtrim1$$;


ALTER FUNCTION public.citext(character) OWNER TO postgres;

--
-- TOC entry 324 (class 1255 OID 81027)
-- Dependencies: 1420 7
-- Name: citext(boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext(boolean) RETURNS citext
    LANGUAGE internal IMMUTABLE STRICT
    AS $$booltext$$;


ALTER FUNCTION public.citext(boolean) OWNER TO postgres;

--
-- TOC entry 325 (class 1255 OID 81028)
-- Dependencies: 1420 7
-- Name: citext(inet); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext(inet) RETURNS citext
    LANGUAGE internal IMMUTABLE STRICT
    AS $$network_show$$;


ALTER FUNCTION public.citext(inet) OWNER TO postgres;

--
-- TOC entry 326 (class 1255 OID 81029)
-- Dependencies: 1420 1420 7
-- Name: citext_cmp(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_cmp(citext, citext) RETURNS integer
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_cmp';


ALTER FUNCTION public.citext_cmp(citext, citext) OWNER TO postgres;

--
-- TOC entry 327 (class 1255 OID 81030)
-- Dependencies: 1420 1420 7
-- Name: citext_eq(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_eq(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_eq';


ALTER FUNCTION public.citext_eq(citext, citext) OWNER TO postgres;

--
-- TOC entry 328 (class 1255 OID 81031)
-- Dependencies: 7 1420 1420
-- Name: citext_ge(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_ge(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_ge';


ALTER FUNCTION public.citext_ge(citext, citext) OWNER TO postgres;

--
-- TOC entry 329 (class 1255 OID 81032)
-- Dependencies: 7 1420 1420
-- Name: citext_gt(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_gt(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_gt';


ALTER FUNCTION public.citext_gt(citext, citext) OWNER TO postgres;

--
-- TOC entry 330 (class 1255 OID 81033)
-- Dependencies: 1420 7
-- Name: citext_hash(citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_hash(citext) RETURNS integer
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_hash';


ALTER FUNCTION public.citext_hash(citext) OWNER TO postgres;

--
-- TOC entry 331 (class 1255 OID 81034)
-- Dependencies: 1420 1420 1420 7
-- Name: citext_larger(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_larger(citext, citext) RETURNS citext
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_larger';


ALTER FUNCTION public.citext_larger(citext, citext) OWNER TO postgres;

--
-- TOC entry 332 (class 1255 OID 81035)
-- Dependencies: 1420 1420 7
-- Name: citext_le(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_le(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_le';


ALTER FUNCTION public.citext_le(citext, citext) OWNER TO postgres;

--
-- TOC entry 333 (class 1255 OID 81036)
-- Dependencies: 1420 1420 7
-- Name: citext_lt(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_lt(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_lt';


ALTER FUNCTION public.citext_lt(citext, citext) OWNER TO postgres;

--
-- TOC entry 334 (class 1255 OID 81037)
-- Dependencies: 7 1420 1420
-- Name: citext_ne(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_ne(citext, citext) RETURNS boolean
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_ne';


ALTER FUNCTION public.citext_ne(citext, citext) OWNER TO postgres;

--
-- TOC entry 335 (class 1255 OID 81038)
-- Dependencies: 1420 7 1420 1420
-- Name: citext_smaller(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION citext_smaller(citext, citext) RETURNS citext
    LANGUAGE c IMMUTABLE STRICT
    AS '$libdir/citext', 'citext_smaller';


ALTER FUNCTION public.citext_smaller(citext, citext) OWNER TO postgres;

--
-- TOC entry 346 (class 1255 OID 81039)
-- Dependencies: 1420 7
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
-- TOC entry 521 (class 1255 OID 84484)
-- Dependencies: 7
-- Name: crash_hadu(bigint, bigint, numeric); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION crash_hadu(crashes bigint, adu bigint, throttle numeric DEFAULT 1.0) RETURNS numeric
    LANGUAGE sql
    AS $_$
SELECT CASE WHEN $2 = 0 THEN 0::numeric
ELSE
	round( ( $1 * 100::numeric / $2 ) / $3, 3)
END;
$_$;


ALTER FUNCTION public.crash_hadu(crashes bigint, adu bigint, throttle numeric) OWNER TO postgres;

--
-- TOC entry 522 (class 1255 OID 84485)
-- Dependencies: 7
-- Name: crash_hadu(bigint, numeric, numeric); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION crash_hadu(crashes bigint, adu numeric, throttle numeric DEFAULT 1.0) RETURNS numeric
    LANGUAGE sql
    AS $_$
SELECT CASE WHEN $2 = 0 THEN 0::numeric
ELSE
	round( ( $1 * 100::numeric / $2 ) / $3, 3)
END;
$_$;


ALTER FUNCTION public.crash_hadu(crashes bigint, adu numeric, throttle numeric) OWNER TO postgres;

--
-- TOC entry 347 (class 1255 OID 81040)
-- Dependencies: 7 1826 1420 1420
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
-- TOC entry 348 (class 1255 OID 81041)
-- Dependencies: 7 1826
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
-- TOC entry 365 (class 1255 OID 81042)
-- Dependencies: 7 1826 1420
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
-- TOC entry 366 (class 1255 OID 81043)
-- Dependencies: 1826 7
-- Name: crontabber_nodelete(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION crontabber_nodelete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN

	RAISE EXCEPTION 'you are not allowed to add or delete records from the crontabber table';

END;
$$;


ALTER FUNCTION public.crontabber_nodelete() OWNER TO postgres;

--
-- TOC entry 367 (class 1255 OID 81044)
-- Dependencies: 1826 7
-- Name: crontabber_timestamp(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION crontabber_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
	
	NEW.last_updated = now();
	RETURN NEW;
	
END; $$;


ALTER FUNCTION public.crontabber_timestamp() OWNER TO postgres;

--
-- TOC entry 368 (class 1255 OID 81045)
-- Dependencies: 7
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
-- TOC entry 369 (class 1255 OID 81046)
-- Dependencies: 1826 7
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
-- TOC entry 370 (class 1255 OID 81047)
-- Dependencies: 1826 1420 7
-- Name: edit_featured_versions(citext, text[]); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION edit_featured_versions(product citext, VARIADIC featured_versions text[]) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function allows admins to change the featured versions
-- for a particular product
BEGIN

--check required parameters
IF NOT ( nonzero_string(product) AND nonzero_string(featured_versions[1]) ) THEN
	RAISE EXCEPTION 'a product name and at least one version are required';
END IF;

--check that all versions are not expired
PERFORM 1 FROM product_versions
WHERE product_name = product
  AND version_string = ANY ( featured_versions )
  AND sunset_date < current_date;
IF FOUND THEN
	RAISE EXCEPTION 'one or more of the versions you have selected is already expired';
END IF;

--Remove disfeatured versions
UPDATE product_versions SET featured_version = false
WHERE featured_version
	AND product_name = product
	AND NOT ( version_string = ANY( featured_versions ) );
	
--feature new versions
UPDATE product_versions SET featured_version = true
WHERE version_string = ANY ( featured_versions )
	AND product_name = product
	AND NOT featured_version;

RETURN TRUE;

END;$$;


ALTER FUNCTION public.edit_featured_versions(product citext, VARIADIC featured_versions text[]) OWNER TO postgres;

--
-- TOC entry 378 (class 1255 OID 81048)
-- Dependencies: 1826 1420 7
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
-- TOC entry 379 (class 1255 OID 81051)
-- Dependencies: 7
-- Name: get_cores(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION get_cores(cpudetails text) RETURNS integer
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT substring($1 from $x$\| (\d+)$$x$)::INT;
$_$;


ALTER FUNCTION public.get_cores(cpudetails text) OWNER TO postgres;

--
-- TOC entry 380 (class 1255 OID 81052)
-- Dependencies: 1420 1422 7
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
-- TOC entry 381 (class 1255 OID 81053)
-- Dependencies: 7
-- Name: initcap(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION initcap(text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT upper(substr($1,1,1)) || substr($1,2);
$_$;


ALTER FUNCTION public.initcap(text) OWNER TO postgres;

--
-- TOC entry 517 (class 1255 OID 84486)
-- Dependencies: 7 1420
-- Name: is_rapid_beta(citext, text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION is_rapid_beta(channel citext, repversion text, rbetaversion text) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT $1 = 'beta' AND major_version_sort($2) >= major_version_sort($3);
$_$;


ALTER FUNCTION public.is_rapid_beta(channel citext, repversion text, rbetaversion text) OWNER TO postgres;

--
-- TOC entry 382 (class 1255 OID 81054)
-- Dependencies: 1826 7
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
-- TOC entry 383 (class 1255 OID 81055)
-- Dependencies: 1826 7
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
-- TOC entry 384 (class 1255 OID 81056)
-- Dependencies: 1424 7
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
-- TOC entry 385 (class 1255 OID 81057)
-- Dependencies: 7
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
-- TOC entry 386 (class 1255 OID 81058)
-- Dependencies: 1420 7
-- Name: nonzero_string(citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION nonzero_string(citext) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$_$;


ALTER FUNCTION public.nonzero_string(citext) OWNER TO postgres;

--
-- TOC entry 387 (class 1255 OID 81059)
-- Dependencies: 7
-- Name: nonzero_string(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION nonzero_string(text) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT btrim($1) <> '' AND $1 IS NOT NULL;
$_$;


ALTER FUNCTION public.nonzero_string(text) OWNER TO postgres;

--
-- TOC entry 388 (class 1255 OID 81060)
-- Dependencies: 7
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
-- TOC entry 389 (class 1255 OID 81061)
-- Dependencies: 7
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
-- TOC entry 390 (class 1255 OID 81062)
-- Dependencies: 7
-- Name: pg_stat_statements(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION pg_stat_statements(OUT userid oid, OUT dbid oid, OUT query text, OUT calls bigint, OUT total_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint) RETURNS SETOF record
    LANGUAGE c
    AS '$libdir/pg_stat_statements', 'pg_stat_statements';


ALTER FUNCTION public.pg_stat_statements(OUT userid oid, OUT dbid oid, OUT query text, OUT calls bigint, OUT total_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint) OWNER TO postgres;

--
-- TOC entry 518 (class 1255 OID 81063)
-- Dependencies: 7
-- Name: pg_stat_statements_reset(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION pg_stat_statements_reset() RETURNS void
    LANGUAGE c
    AS '$libdir/pg_stat_statements', 'pg_stat_statements_reset';


ALTER FUNCTION public.pg_stat_statements_reset() OWNER TO postgres;

--
-- TOC entry 391 (class 1255 OID 81064)
-- Dependencies: 1420 7
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
-- TOC entry 392 (class 1255 OID 81065)
-- Dependencies: 1826 7
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
-- TOC entry 393 (class 1255 OID 81066)
-- Dependencies: 1420 1420 7
-- Name: regexp_matches(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_matches(citext, citext) RETURNS text[]
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_matches( $1::pg_catalog.text, $2::pg_catalog.text, 'i' );
$_$;


ALTER FUNCTION public.regexp_matches(citext, citext) OWNER TO postgres;

--
-- TOC entry 394 (class 1255 OID 81067)
-- Dependencies: 1420 1420 7
-- Name: regexp_matches(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_matches(citext, citext, text) RETURNS text[]
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_matches( $1::pg_catalog.text, $2::pg_catalog.text, CASE WHEN pg_catalog.strpos($3, 'c') = 0 THEN  $3 || 'i' ELSE $3 END );
$_$;


ALTER FUNCTION public.regexp_matches(citext, citext, text) OWNER TO postgres;

--
-- TOC entry 395 (class 1255 OID 81068)
-- Dependencies: 1420 1420 7
-- Name: regexp_replace(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_replace(citext, citext, text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_replace( $1::pg_catalog.text, $2::pg_catalog.text, $3, 'i');
$_$;


ALTER FUNCTION public.regexp_replace(citext, citext, text) OWNER TO postgres;

--
-- TOC entry 396 (class 1255 OID 81069)
-- Dependencies: 1420 1420 7
-- Name: regexp_replace(citext, citext, text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_replace(citext, citext, text, text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_replace( $1::pg_catalog.text, $2::pg_catalog.text, $3, CASE WHEN pg_catalog.strpos($4, 'c') = 0 THEN  $4 || 'i' ELSE $4 END);
$_$;


ALTER FUNCTION public.regexp_replace(citext, citext, text, text) OWNER TO postgres;

--
-- TOC entry 397 (class 1255 OID 81070)
-- Dependencies: 1420 1420 7
-- Name: regexp_split_to_array(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_split_to_array(citext, citext) RETURNS text[]
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_split_to_array( $1::pg_catalog.text, $2::pg_catalog.text, 'i' );
$_$;


ALTER FUNCTION public.regexp_split_to_array(citext, citext) OWNER TO postgres;

--
-- TOC entry 398 (class 1255 OID 81071)
-- Dependencies: 1420 1420 7
-- Name: regexp_split_to_array(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_split_to_array(citext, citext, text) RETURNS text[]
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_split_to_array( $1::pg_catalog.text, $2::pg_catalog.text, CASE WHEN pg_catalog.strpos($3, 'c') = 0 THEN  $3 || 'i' ELSE $3 END );
$_$;


ALTER FUNCTION public.regexp_split_to_array(citext, citext, text) OWNER TO postgres;

--
-- TOC entry 399 (class 1255 OID 81072)
-- Dependencies: 1420 1420 7
-- Name: regexp_split_to_table(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_split_to_table(citext, citext) RETURNS SETOF text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_split_to_table( $1::pg_catalog.text, $2::pg_catalog.text, 'i' );
$_$;


ALTER FUNCTION public.regexp_split_to_table(citext, citext) OWNER TO postgres;

--
-- TOC entry 400 (class 1255 OID 81073)
-- Dependencies: 7 1420 1420
-- Name: regexp_split_to_table(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION regexp_split_to_table(citext, citext, text) RETURNS SETOF text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_split_to_table( $1::pg_catalog.text, $2::pg_catalog.text, CASE WHEN pg_catalog.strpos($3, 'c') = 0 THEN  $3 || 'i' ELSE $3 END );
$_$;


ALTER FUNCTION public.regexp_split_to_table(citext, citext, text) OWNER TO postgres;

--
-- TOC entry 401 (class 1255 OID 81074)
-- Dependencies: 1420 7 1420 1420
-- Name: replace(citext, citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION replace(citext, citext, citext) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.regexp_replace( $1::pg_catalog.text, pg_catalog.regexp_replace($2::pg_catalog.text, '([^a-zA-Z_0-9])', E'\\\\\\1', 'g'), $3::pg_catalog.text, 'gi' );
$_$;


ALTER FUNCTION public.replace(citext, citext, citext) OWNER TO postgres;

--
-- TOC entry 520 (class 1255 OID 84483)
-- Dependencies: 1826 7
-- Name: reports_clean_done(date, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION reports_clean_done(updateday date, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function checks that reports_clean has been updated
-- all the way to the last hour of the UTC day
BEGIN

PERFORM 1
    FROM reports_clean
    WHERE date_processed BETWEEN ( ( updateday::timestamp at time zone 'utc' )
            +  ( interval '24 hours' - check_period ) )
        AND ( ( updateday::timestamp at time zone 'utc' ) + interval '1 day' )
    LIMIT 1;
IF FOUND THEN
    RETURN TRUE;
ELSE
    RETURN FALSE;
END IF;
END; $$;


ALTER FUNCTION public.reports_clean_done(updateday date, check_period interval) OWNER TO postgres;

--
-- TOC entry 402 (class 1255 OID 81076)
-- Dependencies: 7 1826
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
-- TOC entry 403 (class 1255 OID 81077)
-- Dependencies: 7
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
-- TOC entry 1132 (class 1255 OID 89101)
-- Dependencies: 7
-- Name: socorro_db_data_refresh(timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION socorro_db_data_refresh(refreshtime timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS timestamp with time zone
    LANGUAGE sql
    AS $_$
UPDATE socorro_db_version SET refreshed_at = COALESCE($1, now())
RETURNING refreshed_at;
$_$;


ALTER FUNCTION public.socorro_db_data_refresh(refreshtime timestamp with time zone) OWNER TO postgres;

--
-- TOC entry 404 (class 1255 OID 81078)
-- Dependencies: 7 1420 1420
-- Name: split_part(citext, citext, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION split_part(citext, citext, integer) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT (pg_catalog.regexp_split_to_array( $1::pg_catalog.text, pg_catalog.regexp_replace($2::pg_catalog.text, '([^a-zA-Z_0-9])', E'\\\\\\1', 'g'), 'i'))[$3];
$_$;


ALTER FUNCTION public.split_part(citext, citext, integer) OWNER TO postgres;

--
-- TOC entry 405 (class 1255 OID 81079)
-- Dependencies: 1420 7 1420
-- Name: strpos(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION strpos(citext, citext) RETURNS integer
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.strpos( pg_catalog.lower( $1::pg_catalog.text ), pg_catalog.lower( $2::pg_catalog.text ) );
$_$;


ALTER FUNCTION public.strpos(citext, citext) OWNER TO postgres;

--
-- TOC entry 406 (class 1255 OID 81080)
-- Dependencies: 1420 7
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
-- TOC entry 407 (class 1255 OID 81081)
-- Dependencies: 1420 1420 7
-- Name: texticlike(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticlike(citext, citext) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticlike$$;


ALTER FUNCTION public.texticlike(citext, citext) OWNER TO postgres;

--
-- TOC entry 408 (class 1255 OID 81082)
-- Dependencies: 7 1420
-- Name: texticlike(citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticlike(citext, text) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticlike$$;


ALTER FUNCTION public.texticlike(citext, text) OWNER TO postgres;

--
-- TOC entry 409 (class 1255 OID 81083)
-- Dependencies: 7 1420 1420
-- Name: texticnlike(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticnlike(citext, citext) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticnlike$$;


ALTER FUNCTION public.texticnlike(citext, citext) OWNER TO postgres;

--
-- TOC entry 410 (class 1255 OID 81084)
-- Dependencies: 7 1420
-- Name: texticnlike(citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticnlike(citext, text) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticnlike$$;


ALTER FUNCTION public.texticnlike(citext, text) OWNER TO postgres;

--
-- TOC entry 411 (class 1255 OID 81085)
-- Dependencies: 7 1420 1420
-- Name: texticregexeq(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticregexeq(citext, citext) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticregexeq$$;


ALTER FUNCTION public.texticregexeq(citext, citext) OWNER TO postgres;

--
-- TOC entry 412 (class 1255 OID 81086)
-- Dependencies: 7 1420
-- Name: texticregexeq(citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticregexeq(citext, text) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticregexeq$$;


ALTER FUNCTION public.texticregexeq(citext, text) OWNER TO postgres;

--
-- TOC entry 413 (class 1255 OID 81087)
-- Dependencies: 7 1420 1420
-- Name: texticregexne(citext, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticregexne(citext, citext) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticregexne$$;


ALTER FUNCTION public.texticregexne(citext, citext) OWNER TO postgres;

--
-- TOC entry 414 (class 1255 OID 81088)
-- Dependencies: 7 1420
-- Name: texticregexne(citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION texticregexne(citext, text) RETURNS boolean
    LANGUAGE internal IMMUTABLE STRICT
    AS $$texticregexne$$;


ALTER FUNCTION public.texticregexne(citext, text) OWNER TO postgres;

--
-- TOC entry 519 (class 1255 OID 84482)
-- Dependencies: 1424 7
-- Name: to_major_version(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION to_major_version(version text) RETURNS major_version
    LANGUAGE sql IMMUTABLE
    AS $_$
-- turns a version string into a major version
-- i.e. "6.0a2" into "6.0"
SELECT substring($1 from $x$^(\d+\.\d+)$x$)::major_version;
$_$;


ALTER FUNCTION public.to_major_version(version text) OWNER TO postgres;

--
-- TOC entry 431 (class 1255 OID 81090)
-- Dependencies: 7 1826
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
-- TOC entry 432 (class 1255 OID 81091)
-- Dependencies: 7 1826
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
-- TOC entry 433 (class 1255 OID 81092)
-- Dependencies: 7 1420 1420
-- Name: translate(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION translate(citext, citext, text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.translate( pg_catalog.translate( $1::pg_catalog.text, pg_catalog.lower($2::pg_catalog.text), $3), pg_catalog.upper($2::pg_catalog.text), $3);
$_$;


ALTER FUNCTION public.translate(citext, citext, text) OWNER TO postgres;

--
-- TOC entry 434 (class 1255 OID 81093)
-- Dependencies: 7 1826
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
-- TOC entry 435 (class 1255 OID 81094)
-- Dependencies: 7
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
-- TOC entry 450 (class 1255 OID 81095)
-- Dependencies: 1826 7
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
		RETURN FALSE;
	END IF;
END IF;

-- check if ADU has already been run for the date
PERFORM 1 FROM product_adu
WHERE adu_date = updateday LIMIT 1;
IF FOUND THEN
  IF checkdata THEN
	  RAISE NOTICE 'update_adu has already been run for %', updateday;
  END IF;
  RETURN FALSE;
END IF;

-- insert releases
-- note that we're now matching against product_guids were we can
-- and that we need to strip the {} out of the guids

INSERT INTO product_adu ( product_version_id, os_name,
		adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
	updateday,
	coalesce(sum(adu_count), 0)
FROM product_versions
	LEFT OUTER JOIN (
		SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
			as product_name, raw_adu.product_version::citext as product_version,
			raw_adu.build_channel::citext as build_channel,
			raw_adu.adu_count,
			os_name_matches.os_name
		FROM raw_adu
		LEFT OUTER JOIN product_productid_map as prodmap
			ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
		LEFT OUTER JOIN os_name_matches
    		ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
		WHERE raw_adu.date = updateday
		) as prod_adu
		ON product_versions.product_name = prod_adu.product_name
		AND product_versions.version_string = prod_adu.product_version
		AND product_versions.build_type = prod_adu.build_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type IN ('release','nightly','aurora')
GROUP BY product_version_id, os;

-- insert ESRs
-- need a separate query here because the ESR version number doesn't match

INSERT INTO product_adu ( product_version_id, os_name,
		adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
	updateday,
	coalesce(sum(adu_count), 0)
FROM product_versions
	LEFT OUTER JOIN (
		SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
			as product_name, raw_adu.product_version::citext as product_version,
			raw_adu.build_channel::citext as build_channel,
			raw_adu.adu_count,
			os_name_matches.os_name
		FROM raw_adu
		LEFT OUTER JOIN product_productid_map as prodmap
			ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
		LEFT OUTER JOIN os_name_matches
    		ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
		WHERE raw_adu.date = updateday
			and raw_adu.build_channel ILIKE 'esr'
		) as prod_adu
		ON product_versions.product_name = prod_adu.product_name
		AND product_versions.version_string
			=  ( prod_adu.product_version || 'esr' )
		AND product_versions.build_type = prod_adu.build_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'ESR'
GROUP BY product_version_id, os;

-- insert betas

INSERT INTO product_adu ( product_version_id, os_name,
		adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
	updateday,
	coalesce(sum(adu_count), 0)
FROM product_versions
    JOIN products USING ( product_name )
	LEFT OUTER JOIN (
		SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
			as product_name, raw_adu.product_version::citext as product_version,
			raw_adu.build_channel::citext as build_channel,
			raw_adu.adu_count,
			os_name_matches.os_name,
			build_numeric(raw_adu.build) as build_id
		FROM raw_adu
		LEFT OUTER JOIN product_productid_map as prodmap
			ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
		LEFT OUTER JOIN os_name_matches
    		ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
		WHERE raw_adu.date = updateday
			AND raw_adu.build_channel = 'beta'
		) as prod_adu
		ON product_versions.product_name = prod_adu.product_name
		AND product_versions.release_version = prod_adu.product_version
		AND product_versions.build_type = prod_adu.build_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'Beta'
        AND EXISTS ( SELECT 1
            FROM product_version_builds
            WHERE product_versions.product_version_id = product_version_builds.product_version_id
              AND product_version_builds.build_id = prod_adu.build_id
            )
GROUP BY product_version_id, os;


RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_adu(updateday date, checkdata boolean) OWNER TO postgres;

--
-- TOC entry 543 (class 1255 OID 84553)
-- Dependencies: 1826 7
-- Name: update_build_adu(date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_build_adu(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM build_adu
    WHERE adu_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'build_adu has already been run for %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if raw_adu is available
PERFORM 1 FROM raw_adu
WHERE "date" = updateday
LIMIT 1;
IF NOT FOUND THEN
    IF checkdata THEN
        RAISE EXCEPTION 'raw_adu has not been updated for %',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- insert nightly, aurora
-- only 7 days of data after each build

INSERT INTO build_adu ( product_version_id, os_name,
        adu_date, build_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    bdate,
    coalesce(sum(adu_count), 0)
FROM product_versions
    JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            build_date(build_numeric(raw_adu.build)) as bdate,
            os_name_matches.os_name
        FROM raw_adu
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adu.date = updateday
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.version_string = prod_adu.product_version
        AND product_versions.build_type = prod_adu.build_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type IN ('release','nightly','aurora')
        AND bdate is not null
        AND updateday <= ( bdate + 6 )
GROUP BY product_version_id, os, bdate;

-- insert betas
-- rapid beta parent entries only
-- only 7 days of data after each build

INSERT INTO build_adu ( product_version_id, os_name,
        adu_date, build_date, adu_count )
SELECT rapid_beta_id, coalesce(os_name,'Unknown') as os,
    updateday,
    bdate,
    coalesce(sum(adu_count), 0)
FROM product_versions
    JOIN products USING ( product_name )
    JOIN (
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            os_name_matches.os_name,
            build_numeric(raw_adu.build) as build_id,
            build_date(build_numeric(raw_adu.build)) as bdate
        FROM raw_adu
        LEFT OUTER JOIN product_productid_map as prodmap
            ON raw_adu.product_guid = btrim(prodmap.productid, '{}')
        LEFT OUTER JOIN os_name_matches
            ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
        WHERE raw_adu.date = updateday
            AND raw_adu.build_channel = 'beta'
        ) as prod_adu
        ON product_versions.product_name = prod_adu.product_name
        AND product_versions.release_version = prod_adu.product_version
        AND product_versions.build_type = prod_adu.build_channel
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'Beta'
        AND EXISTS ( SELECT 1
            FROM product_version_builds
            WHERE product_versions.product_version_id = product_version_builds.product_version_id
              AND product_version_builds.build_id = prod_adu.build_id
            )
        AND bdate is not null
        AND rapid_beta_id IS NOT NULL
        AND updateday <= ( bdate + 6 )
GROUP BY rapid_beta_id, os, bdate;

RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_build_adu(updateday date, checkdata boolean) OWNER TO postgres;

--
-- TOC entry 449 (class 1255 OID 81096)
-- Dependencies: 1826 7
-- Name: update_correlations(date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_correlations(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates daily matviews
-- for some of the correlation reports
-- depends on reports_clean

-- no need to check if we've been run, since the correlations
-- only hold the last day of data

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

-- clear the correlations list
-- can't use TRUNCATE here because of locking
DELETE FROM correlations;

--create the correlations list
INSERT INTO correlations ( signature_id, product_version_id,
	os_name, reason_id, crash_count )
SELECT signature_id, product_version_id,
	os_name, reason_id, count(*)
FROM reports_clean
	JOIN product_versions USING ( product_version_id )
WHERE updateday BETWEEN build_date and sunset_date
	and utc_day_is(date_processed, updateday)
GROUP BY product_version_id, os_name, reason_id, signature_id
ORDER BY product_version_id, os_name, reason_id, signature_id;

ANALYZE correlations;

-- create list of UUID-report_id correspondences for the day
CREATE TEMPORARY TABLE uuid_repid
AS
SELECT uuid, id as report_id
FROM reports
WHERE utc_day_is(date_processed, updateday)
ORDER BY uuid, report_id;
CREATE INDEX uuid_repid_key on uuid_repid(uuid, report_id);
ANALYZE uuid_repid;

--create the correlation-addons list
INSERT INTO correlation_addons (
	correlation_id, addon_key, addon_version, crash_count )
SELECT correlation_id, extension_id, extension_version, count(*)
FROM correlations 
	JOIN reports_clean 
		USING ( product_version_id, os_name, reason_id, signature_id )
	JOIN uuid_repid 
		USING ( uuid )
	JOIN extensions 
		USING ( report_id )
	JOIN product_versions 
		USING ( product_version_id )
WHERE utc_day_is(reports_clean.date_processed, updateday)
	AND utc_day_is(extensions.date_processed, updateday)
	AND updateday BETWEEN build_date AND sunset_date
GROUP BY correlation_id, extension_id, extension_version;

ANALYZE correlation_addons;

--create correlations-cores list
INSERT INTO correlation_cores (
	correlation_id, architecture, cores, crash_count )
SELECT correlation_id, architecture, cores, count(*)
FROM correlations 
	JOIN reports_clean 
		USING ( product_version_id, os_name, reason_id, signature_id )
	JOIN product_versions 
		USING ( product_version_id )
WHERE utc_day_is(reports_clean.date_processed, updateday)
	AND updateday BETWEEN build_date AND sunset_date
	AND architecture <> '' AND cores >= 0
GROUP BY correlation_id, architecture, cores;

ANALYZE correlation_cores;

RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_correlations(updateday date, checkdata boolean) OWNER TO postgres;

--
-- TOC entry 525 (class 1255 OID 84594)
-- Dependencies: 1826 7
-- Name: update_crashes_by_user(date, boolean, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_crashes_by_user(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN
-- this function populates a daily matview
-- for general statistics of crashes by user
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM crashes_by_user
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'crashes_by_user has already been run for %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM product_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'product_adu has not been updated for %', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
INSERT INTO crashes_by_user
    ( product_version_id, report_date,
      report_count, adu,
      os_short_name, crash_type_id )
SELECT product_version_id, updateday,
    report_count, adu_sum,
    os_short_name, crash_type_id
FROM ( select product_version_id,
            count(*) as report_count,
            os_name, os_short_name, crash_type_id
      from reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      	JOIN os_names USING ( os_name )
      WHERE
          utc_day_is(date_processed, updateday)
          -- only keep accumulating data for a year
          AND build_date >= ( current_date - interval '1 year' )
      GROUP BY product_version_id, os_name, os_short_name, crash_type_id
      	) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name
        from product_adu
        where adu_date = updateday
        group by product_version_id, os_name ) as sum_adu
      USING ( product_version_id, os_name )
      JOIN product_versions USING ( product_version_id )
ORDER BY product_version_id;

-- insert records for the rapid beta parent entries
INSERT INTO crashes_by_user
    ( product_version_id, report_date,
      report_count, adu,
      os_short_name, crash_type_id )
SELECT product_versions.rapid_beta_id, updateday,
	sum(report_count), sum(adu),
	os_short_name, crash_type_id
FROM crashes_by_user
	JOIN product_versions USING ( product_version_id )
WHERE rapid_beta_id IS NOT NULL
	AND report_date = updateday
GROUP BY rapid_beta_id, os_short_name, crash_type_id;

RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_crashes_by_user(updateday date, checkdata boolean, check_period interval) OWNER TO postgres;

--
-- TOC entry 527 (class 1255 OID 84614)
-- Dependencies: 7 1826
-- Name: update_crashes_by_user_build(date, boolean, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_crashes_by_user_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN
-- this function populates a daily matview
-- for general statistics of crashes by user
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM crashes_by_user_build
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'crashes_by_user_build has already been run for %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM build_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'build_adu has not been updated for %', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
-- first, nightly and aurora are fairly straightforwards

INSERT INTO crashes_by_user_build
    ( product_version_id, report_date,
      build_date, report_count, adu,
      os_short_name, crash_type_id )
SELECT product_version_id, updateday,
    count_reports.build_date, report_count, adu_sum,
    os_short_name, crash_type_id
FROM ( select product_version_id,
            count(*) as report_count,
            os_name, os_short_name, crash_type_id,
            build_date(build) as build_date
      from reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      	JOIN os_names USING ( os_name )
      WHERE
          utc_day_is(date_processed, updateday)
          -- only accumulate data for each build for 7 days after build
          AND updateday <= ( build_date(build) + 6 )
          AND reports_clean.release_channel IN ( 'nightly','aurora' )
      GROUP BY product_version_id, os_name, os_short_name, crash_type_id,
      	build_date(build)
      	) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name, build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, os_name, build_date ) as sum_adu
      USING ( product_version_id, os_name, build_date )
      JOIN product_versions USING ( product_version_id )
ORDER BY product_version_id;

-- rapid beta needs to be inserted with the productid of the
-- parent beta product_version instead of its
-- own product_version_id.

INSERT INTO crashes_by_user_build
    ( product_version_id, report_date,
      build_date, report_count, adu,
      os_short_name, crash_type_id )
SELECT rapid_beta_id, updateday,
    count_reports.build_date, report_count, adu_sum,
    os_short_name, crash_type_id
FROM ( select rapid_beta_id AS product_version_id,
            count(*) as report_count,
            os_name, os_short_name, crash_type_id,
            build_date(build) as build_date
      from reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      	JOIN os_names USING ( os_name )
      WHERE
          utc_day_is(date_processed, updateday)
          -- only accumulate data for each build for 7 days after build
          AND updateday <= ( build_date(build) + 6 )
          AND reports_clean.release_channel = 'beta'
          AND product_versions.rapid_beta_id IS NOT NULL
      GROUP BY rapid_beta_id, os_name, os_short_name, crash_type_id,
      	build_date(build)
      	) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        os_name, build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, os_name, build_date ) as sum_adu
      USING ( product_version_id, os_name, build_date )
      JOIN product_versions USING ( product_version_id )
ORDER BY product_version_id;


RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_crashes_by_user_build(updateday date, checkdata boolean, check_period interval) OWNER TO postgres;

--
-- TOC entry 463 (class 1255 OID 81097)
-- Dependencies: 7 1826
-- Name: update_daily_crashes(date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_daily_crashes(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
BEGIN
-- update the daily crashes summary matview
-- VERSION 4
-- updates daily_crashes for new products using reports_clean
-- instead of using reports

-- apologies for badly written SQL, didn't want to rewrite it all from scratch

-- note: we are currently excluding crashes which are missing an OS_Name from the count

-- check if we've already been run
IF checkdata THEN
	PERFORM 1 FROM daily_crashes
	WHERE adu_day = updateday LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'daily_crashes has already been run for %', updateday;
	END IF;
END IF;

-- check if reports_clean is updated
IF NOT reports_clean_done(updateday) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

-- insert old browser crashes
-- for most crashes
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code, p.id,
	substring(r.os_name, 1, 3) AS os_short_name,
	updateday
FROM product_visibility cfg
JOIN productdims p on cfg.productdims_id = p.id
JOIN reports r on p.product = r.product AND p.version = r.version
WHERE NOT cfg.ignore AND
	date_processed >= ( updateday::timestamptz )
		AND date_processed < ( updateday + 1 )::timestamptz
	AND updateday BETWEEN cfg.start_date and cfg.end_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
GROUP BY p.id, crash_code, os_short_name;

 -- insert HANGS_NORMALIZED from old data
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, p.id AS prod_id, substring(r.os_name, 1, 3) AS os_short_name
		   FROM product_visibility cfg
		   JOIN productdims p on cfg.productdims_id = p.id
		   JOIN reports r on p.product = r.product AND p.version = r.version
		   WHERE NOT cfg.ignore AND
			date_processed >= ( updateday::timestamptz )
				AND date_processed < ( updateday + 1 )::timestamptz
				AND updateday BETWEEN cfg.start_date and cfg.end_date
				AND hangid IS NOT NULL
                AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

-- insert crash counts for new products
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hang_id) as crash_code,
	product_version_id, 
	initcap(os_short_name),
	updateday
FROM reports_clean JOIN product_versions USING (product_version_id)
	JOIN os_names USING (os_name)
WHERE utc_day_is(date_processed, updateday)
	AND updateday BETWEEN product_versions.build_date and sunset_date
GROUP BY product_version_id, crash_code, os_short_name;

-- insert normalized hangs for new products
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(DISTINCT hang_id) as count, 'H', 
	product_version_id, initcap(os_short_name),
	updateday
FROM product_versions
	JOIN reports_clean USING ( product_version_id )
	JOIN os_names USING (os_name)
	WHERE utc_day_is(date_processed, updateday)
		AND updateday BETWEEN product_versions.build_date and sunset_date
GROUP BY product_version_id, os_short_name;

ANALYZE daily_crashes;

RETURN TRUE;

END;$$;


ALTER FUNCTION public.update_daily_crashes(updateday date, checkdata boolean) OWNER TO postgres;

--
-- TOC entry 464 (class 1255 OID 81098)
-- Dependencies: 1826 7
-- Name: update_explosiveness(date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_explosiveness(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
-- set stats parameters per Kairo
DECLARE 
	-- minimum crashes/mil.adu to show up
	minrate INT := 10;	
	-- minimum comparitor figures if there are no
	-- or very few proir crashes to smooth curves
	-- mostly corresponds to Kairo "clampperadu"
	mindiv_one INT := 30;
	mindiv_three INT := 15;
	mes_edate DATE;
	mes_b3date DATE;
	comp_e1date DATE;
	comp_e3date DATE;
	comp_bdate DATE;
BEGIN
-- this function populates a daily matview
-- for explosiveness
-- depends on tcbs and product_adu

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM explosiveness
	WHERE last_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE INFO 'explosiveness has already been run for %.',updateday;
	END IF;
END IF;

-- check if product_adu and tcbs are updated
PERFORM 1
FROM tcbs JOIN product_adu
   ON tcbs.report_date = product_adu.adu_date
WHERE tcbs.report_date = updateday
LIMIT 1;

IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Either product_adu or tcbs have not been updated to the end of %',updateday;
	ELSE
		RAISE NOTICE 'Either product_adu or tcbs has not been updated, skipping.';
		RETURN TRUE;
	END IF;
END IF;

-- compute dates 
-- note that dates are inclusive
-- last date of measured period
mes_edate := updateday;
-- first date of the measured period for 3-day
mes_b3date := updateday - 2;
-- last date of the comparison period for 1-day
comp_e1date := updateday - 1;
-- last date of the comparison period for 3-day
comp_e3date := mes_b3date - 1;
-- first date of the comparison period
comp_bdate := mes_edate - 9;

-- create temp table with all of the crash_madus for each
-- day, including zeroes
CREATE TEMPORARY TABLE crash_madu
ON COMMIT DROP
AS 
WITH crashdates AS (
	SELECT report_date::DATE as report_date
	FROM generate_series(comp_bdate, mes_edate, INTERVAL '1 day')
		AS gs(report_date)
),
adusum AS (
	SELECT adu_date, sum(adu_count) as adu_count,
		( mindiv_one * 1000000::numeric / sum(adu_count)) as mindivisor,
		product_version_id
	FROM product_adu
	WHERE adu_date BETWEEN comp_bdate and mes_edate
		AND adu_count > 0
	GROUP BY adu_date, product_version_id 
),
reportsum AS (
	SELECT report_date, sum(report_count) as report_count,
		product_version_id, signature_id
	FROM tcbs
	WHERE report_date BETWEEN comp_bdate and mes_edate
	GROUP BY report_date, product_version_id, signature_id
),
crash_madu_raw AS (
	SELECT ( report_count * 1000000::numeric ) / adu_count AS crash_madu,
		reportsum.product_version_id, reportsum.signature_id, 
		report_date, mindivisor
	FROM adusum JOIN reportsum
		ON adu_date = report_date
		AND adusum.product_version_id = reportsum.product_version_id
),
product_sigs AS (
	SELECT DISTINCT product_version_id, signature_id
	FROM crash_madu_raw
)
SELECT crashdates.report_date, 
	coalesce(crash_madu, 0) as crash_madu,
	product_sigs.product_version_id, product_sigs.signature_id,
	COALESCE(crash_madu_raw.mindivisor, 0) as mindivisor
FROM crashdates CROSS JOIN product_sigs
	LEFT OUTER JOIN crash_madu_raw
	ON crashdates.report_date = crash_madu_raw.report_date
		AND product_sigs.product_version_id = crash_madu_raw.product_version_id
		AND product_sigs.signature_id = crash_madu_raw.signature_id;

-- create crosstab with days1-10
-- create the multiplier table

CREATE TEMPORARY TABLE xtab_mult
ON COMMIT DROP
AS
SELECT report_date,
	( case when report_date = mes_edate THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day0,
	( case when report_date = ( mes_edate - 1 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day1,
	( case when report_date = ( mes_edate - 2 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day2,
	( case when report_date = ( mes_edate - 3 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day3,
	( case when report_date = ( mes_edate - 4 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day4,
	( case when report_date = ( mes_edate - 5 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day5,
	( case when report_date = ( mes_edate - 6 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day6,
	( case when report_date = ( mes_edate - 7 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day7,
	( case when report_date = ( mes_edate - 8 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day8,
	( case when report_date = ( mes_edate - 9 ) THEN 1::NUMERIC ELSE 0::NUMERIC END ) as day9
	FROM generate_series(comp_bdate, mes_edate, INTERVAL '1 day')
		AS gs(report_date);

-- create the crosstab
CREATE TEMPORARY TABLE crash_xtab
ON COMMIT DROP
AS
SELECT product_version_id, signature_id,
	round(SUM ( crash_madu * day0 ),2) AS day0,
	round(SUM ( crash_madu * day1 ),2) AS day1,
	round(SUM ( crash_madu * day2 ),2) AS day2,
	round(SUM ( crash_madu * day3 ),2) AS day3,
	round(SUM ( crash_madu * day4 ),2) AS day4,
	round(SUM ( crash_madu * day5 ),2) AS day5,
	round(SUM ( crash_madu * day6 ),2) AS day6,
	round(SUM ( crash_madu * day7 ),2) AS day7,
	round(SUM ( crash_madu * day8 ),2) AS day8,
	round(SUM ( crash_madu * day9 ),2) AS day9
FROM xtab_mult
	JOIN crash_madu USING (report_date)
GROUP BY product_version_id, signature_id;

-- create oneday temp table
CREATE TEMPORARY TABLE explosive_oneday
ON COMMIT DROP
AS 
WITH sum1day AS ( 
	SELECT product_version_id, signature_id, crash_madu as sum1day,
		mindivisor
	FROM crash_madu
	WHERE report_date = mes_edate
	AND crash_madu > 10
),
agg9day AS (
	SELECT product_version_id, signature_id,
		AVG(crash_madu) AS avg9day,
		MAX(crash_madu) as max9day
	FROM crash_madu
	WHERE report_date BETWEEN comp_bdate and comp_e1date
	GROUP BY product_version_id, signature_id
)
SELECT sum1day.signature_id,
	sum1day.product_version_id ,
	round (
		( sum1day.sum1day - coalesce(agg9day.avg9day,0) ) 
			/
		GREATEST ( agg9day.max9day - agg9day.avg9day, sum1day.mindivisor )
		, 2 )
	as explosive_1day,
	round(sum1day,2) as oneday_rate
FROM sum1day 
	LEFT OUTER JOIN agg9day USING ( signature_id, product_version_id )
WHERE sum1day.sum1day IS NOT NULL;
	
ANALYZE explosive_oneday;

-- create threeday temp table
CREATE TEMPORARY TABLE explosive_threeday
ON COMMIT DROP
AS
WITH avg3day AS ( 
	SELECT product_version_id, signature_id, 
        AVG(crash_madu) as avg3day,
		AVG(mindivisor) as mindivisor
	FROM crash_madu
	WHERE report_date BETWEEN mes_b3date and mes_edate
	GROUP BY product_version_id, signature_id
	HAVING AVG(crash_madu) > 10
),
agg7day AS (
	SELECT product_version_id, signature_id,
		SUM(crash_madu)/7 AS avg7day,
		COALESCE(STDDEV(crash_madu),0) AS sdv7day
	FROM crash_madu
	WHERE report_date BETWEEN comp_bdate and comp_e3date
	GROUP BY product_version_id, signature_id
)
SELECT avg3day.signature_id,
	avg3day.product_version_id ,
	round (
		( avg3day - coalesce(avg7day,0) ) 
			/
		GREATEST ( sdv7day, avg3day.mindivisor )
		, 2 )
	as explosive_3day,
	round(avg3day, 2) as threeday_rate
FROM avg3day LEFT OUTER JOIN agg7day 
	USING ( signature_id, product_version_id );
	
ANALYZE explosive_threeday;
	
-- truncate explosiveness
DELETE FROM explosiveness;

-- merge the two tables and insert
INSERT INTO explosiveness (
	last_date, signature_id, product_version_id, 
	oneday, threeday, 
	day0, day1, day2, day3, day4,
	day5, day6, day7, day8, day9)
SELECT updateday, signature_id, product_version_id, 
	explosive_1day, explosive_3day,
	day0, day1, day2, day3, day4,
	day5, day6, day7, day8, day9
FROM crash_xtab 
	LEFT OUTER JOIN explosive_oneday
	USING ( signature_id, product_version_id )
	LEFT OUTER JOIN explosive_threeday
	USING ( signature_id, product_version_id )
WHERE explosive_1day IS NOT NULL or explosive_3day IS NOT NULL
ORDER BY product_version_id;
	
RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_explosiveness(updateday date, checkdata boolean) OWNER TO postgres;

--
-- TOC entry 465 (class 1255 OID 81101)
-- Dependencies: 1826 7
-- Name: update_final_betas(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_final_betas(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
	RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_final_betas(updateday date) OWNER TO postgres;

--
-- TOC entry 466 (class 1255 OID 81102)
-- Dependencies: 7 1826
-- Name: update_hang_report(date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_hang_report(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
    AS $$
BEGIN

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

-- check if we already have hang data
PERFORM 1 FROM daily_hangs
WHERE report_date = updateday LIMIT 1;
IF FOUND THEN
	RAISE EXCEPTION 'it appears that hang_report has already been run for %.  If you are backfilling, use backfill_hang_report instead.',updateday;
END IF;

-- insert data
-- note that we need to group on the plugin here and
-- take min() of all of the browser crash data.  this is a sloppy
-- approach but works because the only reason for more than one 
-- browser crash in a hang group is duplicate crash data
INSERT INTO daily_hangs ( uuid, plugin_uuid, report_date,
	product_version_id, browser_signature_id, plugin_signature_id,
	hang_id, flash_version_id, duplicates, url )
SELECT
    min(browser.uuid) ,
    plugin.uuid,
    updateday as report_date,
    min(browser.product_version_id),
    min(browser.signature_id),
    plugin.signature_id AS plugin_signature_id,
    plugin.hang_id,
    plugin.flash_version_id,
    nullif(array_agg(browser.duplicate_of) 
    	|| COALESCE(ARRAY[plugin.duplicate_of], '{}'),'{NULL}'),
    min(browser_info.url)
FROM reports_clean AS browser
    JOIN reports_clean AS plugin ON plugin.hang_id = browser.hang_id
    LEFT OUTER JOIN reports_user_info AS browser_info ON browser.uuid = browser_info.uuid
    JOIN signatures AS sig_browser
        ON sig_browser.signature_id = browser.signature_id
WHERE sig_browser.signature LIKE 'hang | %'
    AND browser.hang_id != ''
    AND browser.process_type = 'browser'
    AND plugin.process_type = 'plugin'
    AND utc_day_near(browser.date_processed, updateday)
    AND utc_day_is(plugin.date_processed, updateday)
    AND utc_day_is(browser_info.date_processed, updateday)
GROUP BY plugin.uuid, plugin.signature_id, plugin.hang_id, plugin.flash_version_id,
	plugin.duplicate_of;
    
ANALYZE daily_hangs;
RETURN TRUE;
END;$$;


ALTER FUNCTION public.update_hang_report(updateday date, checkdata boolean) OWNER TO postgres;

--
-- TOC entry 529 (class 1255 OID 84631)
-- Dependencies: 7 1826
-- Name: update_home_page_graph(date, boolean, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_home_page_graph(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM home_page_graph
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'home_page_graph has already been run for %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM product_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'product_adu has not been updated for %', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records
INSERT INTO home_page_graph
    ( product_version_id, report_date,
      report_count, adu, crash_hadu )
SELECT product_version_id, updateday,
    report_count, adu_sum,
    crash_hadu(report_count, adu_sum, throttle)
FROM ( select product_version_id,
            count(*) as report_count
      from reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      WHERE
          utc_day_is(date_processed, updateday)
          -- exclude browser hangs from total counts
          AND crash_types.include_agg
          AND updateday BETWEEN build_date AND sunset_date
      group by product_version_id ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum
        from product_adu
        where adu_date = updateday
        group by product_version_id ) as sum_adu
      USING ( product_version_id )
      JOIN product_versions USING ( product_version_id )
      JOIN product_release_channels ON
          product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
WHERE sunset_date > ( current_date - interval '1 year' )
ORDER BY product_version_id;

-- insert summary records for rapid_beta parents
INSERT INTO home_page_graph
    ( product_version_id, report_date,
      report_count, adu, crash_hadu )
SELECT rapid_beta_id, updateday,
    sum(report_count), sum(adu),
    crash_hadu(sum(report_count), sum(adu))
FROM home_page_graph
	JOIN product_versions USING ( product_version_id )
WHERE rapid_beta_id IS NOT NULL
	AND report_date = updateday
GROUP BY rapid_beta_id, updateday;

RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_home_page_graph(updateday date, checkdata boolean, check_period interval) OWNER TO postgres;

--
-- TOC entry 534 (class 1255 OID 84645)
-- Dependencies: 1826 7
-- Name: update_home_page_graph_build(date, boolean, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_home_page_graph_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM home_page_graph_build
    WHERE report_date = updateday
    LIMIT 1;
    IF FOUND THEN
        RAISE NOTICE 'home_page_graph_build has already been run for %.',updateday;
        RETURN FALSE;
    END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
    IF checkdata THEN
        RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
    ELSE
        RETURN FALSE;
    END IF;
END IF;

-- check for product_adu

PERFORM 1 FROM build_adu
WHERE adu_date = updateday
LIMIT 1;
IF NOT FOUND THEN
  IF checkdata THEN
    RAISE EXCEPTION 'build_adu has not been updated for %', updateday;
  ELSE
    RETURN FALSE;
  END IF;
END IF;

-- now insert the new records for nightly and aurora

INSERT INTO home_page_graph_build
    ( product_version_id, build_date, report_date,
      report_count, adu )
SELECT product_version_id, count_reports.build_date, updateday,
    report_count, adu_sum
FROM ( select product_version_id,
            count(*) as report_count,
            build_date(build) as build_date
      FROM reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      WHERE
          utc_day_is(date_processed, updateday)
          -- only 7 days of each build
          AND build_date(build) >= ( updateday - 6 )
          -- exclude browser hangs from total counts
          AND crash_types.include_agg
          -- only visible products
          AND updateday BETWEEN product_versions.build_date AND product_versions.sunset_date
          -- aurora, nightly, and rapid beta only
          AND reports_clean.release_channel IN ( 'nightly','aurora' )
      group by product_version_id, build_date(build) ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, build_date ) as sum_adu
      USING ( product_version_id, build_date )
      JOIN product_versions USING ( product_version_id )
      JOIN product_release_channels ON
          product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
ORDER BY product_version_id;

-- insert records for the "parent" rapid beta

INSERT INTO home_page_graph_build
    ( product_version_id, build_date, report_date,
      report_count, adu )
SELECT product_version_id, count_reports.build_date, updateday,
    report_count, adu_sum
FROM ( select rapid_beta_id AS product_version_id,
            count(*) as report_count,
            build_date(build) as build_date
      FROM reports_clean
      	JOIN product_versions USING ( product_version_id )
      	JOIN products USING ( product_name )
      	JOIN crash_types ON
      		reports_clean.process_type = crash_types.process_type
      		AND ( reports_clean.hang_id IS NOT NULL ) = crash_types.has_hang_id
      WHERE
          utc_day_is(date_processed, updateday)
          -- only 7 days of each build
          AND build_date(build) >= ( updateday - 6 )
          -- exclude browser hangs from total counts
          AND crash_types.include_agg
          -- only visible products
          AND updateday BETWEEN product_versions.build_date AND product_versions.sunset_date
          -- aurora, nightly, and rapid beta only
          AND reports_clean.release_channel = 'beta'
          AND rapid_beta_id IS NOT NULL
      group by rapid_beta_id, build_date(build) ) as count_reports
      JOIN
    ( select product_version_id,
        sum(adu_count) as adu_sum,
        build_date
        from build_adu
        where adu_date = updateday
        group by product_version_id, build_date ) as sum_adu
      USING ( product_version_id, build_date )
      JOIN product_versions USING ( product_version_id )
      JOIN product_release_channels ON
          product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
ORDER BY product_version_id;


RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_home_page_graph_build(updateday date, checkdata boolean, check_period interval) OWNER TO postgres;

--
-- TOC entry 467 (class 1255 OID 81103)
-- Dependencies: 7 1826
-- Name: update_lookup_new_reports(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_lookup_new_reports(column_name text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare table_name text;
	insert_query text;
begin
	IF column_name LIKE '%s' THEN
		table_name := column_name || 'es';
	ELSE
		table_name := column_name || 's';
	END IF;
	
	insert_query := '
		insert into ' || table_name || ' ( ' || column_name || ', first_seen )
		select newrecords.* from ( 
			select ' || column_name || '::citext as col,
				min(date_processed) as first_report
			from new_reports
			group by col ) as newrecords
		left join ' || table_name || ' as lookuplist
			on newrecords.col = lookuplist.' || column_name || '
		where lookuplist.' || column_name || ' IS NULL;';
	
	execute insert_query;
	
	RETURN true;
end; $$;


ALTER FUNCTION public.update_lookup_new_reports(column_name text) OWNER TO postgres;

--
-- TOC entry 468 (class 1255 OID 81104)
-- Dependencies: 7 1826
-- Name: update_nightly_builds(date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_nightly_builds(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
	PERFORM 1 FROM nightly_builds
	WHERE report_date = updateday
	LIMIT 1;
	IF FOUND THEN
		RAISE EXCEPTION 'nightly_builds has already been run for %.',updateday;
	END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

-- now insert the new records
-- this should be some appropriate query, this simple group by
-- is just provided as an example
INSERT INTO nightly_builds (
	product_version_id, build_date, report_date,
	days_out, report_count )
SELECT product_version_id, 
	build_date(reports_clean.build) as build_date, 
	date_processed::date as report_date,
	date_processed::date 
		- build_date(reports_clean.build) as days_out,
	count(*)
FROM reports_clean
	join product_versions using (product_version_id)
	join product_version_builds using (product_version_id)
WHERE 
	reports_clean.build = product_version_builds.build_id
	and reports_clean.release_channel IN ( 'nightly', 'aurora' )
	and date_processed::date 
		- build_date(reports_clean.build) <= 14
	and tstz_between(date_processed, build_date, sunset_date)
	and utc_day_is(date_processed,updateday)
GROUP BY product_version_id, product_name, version_string,
	build_date(build), date_processed::date
ORDER BY product_version_id, build_date, days_out;

RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_nightly_builds(updateday date, checkdata boolean) OWNER TO postgres;

--
-- TOC entry 469 (class 1255 OID 81105)
-- Dependencies: 1826 7
-- Name: update_os_versions(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_os_versions(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET "TimeZone" TO 'UTC'
    AS $_$
BEGIN
-- function for daily batch update of os_version information
-- pulls new data out of reports
-- errors if no data found

create temporary table new_os
on commit drop as
select os_name, os_version
from reports
where date_processed >= updateday
	and date_processed <= ( updateday + 1 )
group by os_name, os_version;

PERFORM 1 FROM new_os LIMIT 1;
IF NOT FOUND THEN
	RAISE EXCEPTION 'No OS data found for date %',updateday;
END IF;

create temporary table os_versions_temp
on commit drop as
select os_name_matches.os_name,
	substring(os_version from $x$^(\d+)$x$)::int as major_version,
	substring(os_version from $x$^\d+\.(\d+)$x$)::int as minor_version
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and substring(os_version from $x$^\d+\.(\d+)$x$)::numeric < 1000;

insert into os_versions_temp
select os_name_matches.os_name,
	substring(os_version from $x$^(\d+)$x$)::int,
	0
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and ( substring(os_version from $x$^\d+\.(\d+)$x$)::numeric >= 1000
		or os_version !~ $x$^\d+\.(\d+)$x$ );

insert into os_versions_temp
select os_name_matches.os_name,
	0,
	0
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version !~ $x$^\d+$x$
	or substring(os_version from $x$^(\d+)$x$)::numeric >= 1000
	or os_version is null;

insert into os_versions ( os_name, major_version, minor_version, os_version_string )
select os_name, major_version, minor_version,
	create_os_version_string( os_name, major_version, minor_version )
from (
select distinct os_name, major_version, minor_version
from os_versions_temp ) as os_rollup
left outer join os_versions
	USING ( os_name, major_version, minor_version )
where  os_versions.os_name is null;

RETURN true;
END; $_$;


ALTER FUNCTION public.update_os_versions(updateday date) OWNER TO postgres;

--
-- TOC entry 470 (class 1255 OID 81106)
-- Dependencies: 7 1826
-- Name: update_os_versions_new_reports(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_os_versions_new_reports() RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $_$
BEGIN
-- function for updating list of oses and versions
-- intended to be called internally by update_reports_clean.

create temporary table new_os
on commit drop as
select os_name, os_version
from new_reports
group by os_name, os_version;

create temporary table os_versions_temp
on commit drop as
select os_name_matches.os_name,
	substring(os_version from $x$^(\d+)$x$)::int as major_version,
	substring(os_version from $x$^\d+\.(\d+)$x$)::int as minor_version
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and substring(os_version from $x$^\d+\.(\d+)$x$)::numeric < 1000;

insert into os_versions_temp
select os_name_matches.os_name,
	substring(os_version from $x$^(\d+)$x$)::int,
	0
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and ( substring(os_version from $x$^\d+\.(\d+)$x$)::numeric >= 1000
		or os_version !~ $x$^\d+\.(\d+)$x$ );

insert into os_versions_temp
select os_name_matches.os_name,
	0,
	0
from new_os join os_name_matches
	ON new_os.os_name ILIKE match_string
where os_version !~ $x$^\d+$x$
	or substring(os_version from $x$^(\d+)$x$)::numeric >= 1000
	or os_version is null;

insert into os_versions ( os_name, major_version, minor_version, os_version_string )
select os_name, major_version, minor_version,
	create_os_version_string( os_name, major_version, minor_version )
from (
select distinct os_name, major_version, minor_version
from os_versions_temp ) as os_rollup
left outer join os_versions
	USING ( os_name, major_version, minor_version )
where  os_versions.os_name is null;

drop table new_os;
drop table os_versions_temp;

RETURN true;
END; $_$;


ALTER FUNCTION public.update_os_versions_new_reports() OWNER TO postgres;

--
-- TOC entry 483 (class 1255 OID 81107)
-- Dependencies: 7 1826
-- Name: update_product_versions(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_product_versions() RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET maintenance_work_mem TO '512MB'
    AS $$
BEGIN
-- daily batch update function for new products and versions
-- reads data from releases_raw, cleans it
-- and puts data corresponding to the new versions into
-- product_versions and related tables

-- is cumulative and can be run repeatedly without issues
-- now covers FennecAndroid and ESR releases
-- now only compares releases from the last 30 days
-- now restricts to only the canonical "repositories"
-- now covers webRT
-- now covers rapid betas, but no more final betas

-- create temporary table, required because
-- all of the special cases

create temporary table releases_recent
on commit drop
as
select COALESCE ( specials.product_name, products.product_name )
		AS product_name,
	releases_raw.version,
	releases_raw.beta_number,
	releases_raw.build_id,
	releases_raw.build_type,
	releases_raw.platform,
	( major_version_sort(version) >= major_version_sort(rapid_release_version) ) as is_rapid,
    is_rapid_beta(build_type, version, rapid_beta_version) as is_rapid_beta,
	releases_raw.repository
from releases_raw
	JOIN products ON releases_raw.product_name = products.release_name
	JOIN release_repositories ON releases_raw.repository = release_repositories.repository
	LEFT OUTER JOIN special_product_platforms AS specials
		ON releases_raw.platform::citext = specials.platform
		AND releases_raw.product_name = specials.release_name
		AND releases_raw.repository = specials.repository
		AND releases_raw.build_type = specials.release_channel
		AND major_version_sort(version) >= major_version_sort(min_version)
where build_date(build_id) > ( current_date - 30 )
	AND version_matches_channel(releases_raw.version, releases_raw.build_type);

--fix ESR versions

UPDATE releases_recent
SET build_type = 'ESR'
WHERE build_type ILIKE 'Release'
	AND version ILIKE '%esr';

-- insert WebRT "releases", which are copies of Firefox releases
-- insert them only if the FF release is greater than the first
-- release for WebRT

INSERT INTO releases_recent
SELECT 'WebappRuntime',
	version, beta_number, build_id,
	build_type, platform,
	is_rapid, is_rapid_beta, repository
FROM releases_recent
	JOIN products
		ON products.product_name = 'WebappRuntime'
WHERE releases_recent.product_name = 'Firefox'
	AND major_version_sort(releases_recent.version)
		>= major_version_sort(products.rapid_release_version);

-- now put it in product_versions
-- first releases, aurora and nightly and non-rapid betas

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type,
    has_builds )
select releases_recent.product_name,
	to_major_version(version),
	version,
	version_string(version, releases_recent.beta_number),
	releases_recent.beta_number,
	version_sort(version, releases_recent.beta_number),
	build_date(min(build_id)),
	sunset_date(min(build_id), releases_recent.build_type ),
	releases_recent.build_type::citext,
	( releases_recent.build_type IN ('aurora', 'nightly') )
from releases_recent
	left outer join product_versions ON
		( releases_recent.product_name = product_versions.product_name
			AND releases_recent.version = product_versions.release_version
			AND releases_recent.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
where is_rapid
    AND product_versions.product_name IS NULL
    AND NOT releases_recent.is_rapid_beta
group by releases_recent.product_name, version,
	releases_recent.beta_number,
	releases_recent.build_type::citext;

-- insert rapid betas "parent" products
-- these will have a product, but no builds

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type,
    is_rapid_beta,
    has_builds )
select products.product_name,
    to_major_version(version),
    version,
    version || 'b',
    0,
    version_sort(version, 0),
    build_date(min(build_id)),
    sunset_date(min(build_id), 'beta' ),
    'beta',
    TRUE,
    TRUE
from releases_recent
    join products ON releases_recent.product_name = products.release_name
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND product_versions.beta_number = 0 )
where is_rapid
    and releases_recent.is_rapid_beta
group by products.product_name, version;

-- finally, add individual betas for rapid_betas
-- these need to get linked to their master rapid_beta

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type,
    rapid_beta_id )
select products.product_name,
    to_major_version(version),
    version,
    version_string(version, releases_recent.beta_number),
    releases_recent.beta_number,
    version_sort(version, releases_recent.beta_number),
    build_date(min(build_id)),
    rapid_parent.sunset_date,
    'beta',
	rapid_parent.product_version_id
from releases_recent
    join products ON releases_recent.product_name = products.release_name
    left outer join product_versions ON
        ( releases_recent.product_name = product_versions.product_name
            AND releases_recent.version = product_versions.release_version
            AND product_versions.beta_number = releases_recent.beta_number )
    join product_versions as rapid_parent ON
    	releases_recent.version = rapid_parent.release_version
    	and rapid_parent.is_rapid_beta
where is_rapid
    and releases_recent.is_rapid_beta
group by products.product_name, version, rapid_parent.product_version_id,
	releases_recent.beta_number, rapid_parent.sunset_date;

-- add build ids
-- note that rapid beta parent records will have no buildids of their own

insert into product_version_builds
select distinct product_versions.product_version_id,
		releases_recent.build_id,
		releases_recent.platform,
		releases_recent.repository
from releases_recent
	join product_versions
		ON releases_recent.product_name = product_versions.product_name
		AND releases_recent.version = product_versions.release_version
		AND releases_recent.build_type = product_versions.build_type
		AND ( releases_recent.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
	left outer join product_version_builds ON
		product_versions.product_version_id = product_version_builds.product_version_id
		AND releases_recent.build_id = product_version_builds.build_id
		AND releases_recent.platform = product_version_builds.platform
where product_version_builds.product_version_id is null;

drop table releases_recent;

return true;
end; $$;


ALTER FUNCTION public.update_product_versions() OWNER TO postgres;

--
-- TOC entry 482 (class 1255 OID 81108)
-- Dependencies: 7 1826
-- Name: update_rank_compare(date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_rank_compare(updateday date DEFAULT NULL::date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this function populates a daily matview
-- for rankings of signatures on TCBS
-- depends on the new reports_clean

-- run for yesterday if not set
updateday := COALESCE(updateday, ( CURRENT_DATE -1 ));

-- don't care if we've been run
-- since there's no historical data

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN TRUE;
	END IF;
END IF;

-- obtain a lock on the matview so that we can TRUNCATE
IF NOT try_lock_table('rank_compare', 'ACCESS EXCLUSIVE') THEN
	RAISE EXCEPTION 'unable to lock the rank_compare table for update.';
END IF;

-- create temporary table with totals from reports_clean

CREATE TEMPORARY TABLE prod_sig_counts 
AS SELECT product_version_id, signature_id, count(*) as report_count
FROM reports_clean
WHERE utc_day_is(date_processed, updateday)
GROUP BY product_version_id, signature_id;

-- truncate rank_compare since we don't need the old data

TRUNCATE rank_compare CASCADE;

-- now insert the new records
INSERT INTO rank_compare (
	product_version_id, signature_id,
	rank_days,
	report_count,
	total_reports, 
	rank_report_count,
	percent_of_total)
SELECT product_version_id, signature_id,
	1, 
	report_count,
	total_count,
	count_rank,
	round(( report_count::numeric / total_count ),5)
FROM (
	SELECT product_version_id, signature_id,
		report_count,
		sum(report_count) over (partition by product_version_id) as total_count,
		dense_rank() over (partition by product_version_id 
							order by report_count desc) as count_rank
	FROM prod_sig_counts
) as initrank;

RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_rank_compare(updateday date, checkdata boolean) OWNER TO postgres;

--
-- TOC entry 536 (class 1255 OID 84658)
-- Dependencies: 1826 7
-- Name: update_reports_clean(timestamp with time zone, interval, boolean, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_reports_clean(fromtime timestamp with time zone, fortime interval DEFAULT '01:00:00'::interval, checkdata boolean DEFAULT true, analyze_it boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET maintenance_work_mem TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $_$
declare rc_part TEXT;
	rui_part TEXT;
	newfortime INTERVAL;
begin
-- this function creates a reports_clean fact table and all associated dimensions
-- intended to be run hourly for a target time three hours ago or so
-- eventually to be replaced by code for the processors to run

-- VERSION: 7
-- now includes support for rapid betas, camino transition

-- accepts a timestamptz, so be careful that the calling script is sending
-- something appropriate

-- since we do allow dynamic timestamps, check if we split over a week
-- boundary.  if so, call self recursively for the first half of the period

IF ( week_begins_utc(fromtime) <>
	week_begins_utc( fromtime + fortime - interval '1 second' ) ) THEN
	PERFORM update_reports_clean( fromtime,
		( week_begins_utc( fromtime + fortime ) - fromtime ), checkdata );
	newfortime := ( fromtime + fortime ) - week_begins_utc( fromtime + fortime );
	fromtime := week_begins_utc( fromtime + fortime );
	fortime := newfortime;
END IF;

-- prevent calling for a period of more than one day

IF fortime > INTERVAL '1 day' THEN
	RAISE EXCEPTION 'you may not execute this function on more than one day of data';
END IF;

-- create a temporary table from the hour of reports you want to
-- process.  generally this will be from 3-4 hours ago to
-- avoid missing reports

-- RULE: replace NULL reason, address, flash_version, os_name with "Unknown"
-- RULE: replace NULL signature, url with ''
-- pre-cleaning: replace NULL product, version with ''
-- RULE: extract number of cores from cpu_info
-- RULE: convert all reference list TEXT values to CITEXT except Signature

create temporary table new_reports
on commit drop
as select uuid,
	date_processed,
	client_crash_date,
	uptime,
	install_age,
	build,
	COALESCE(signature, '')::text as signature,
	COALESCE(reason, 'Unknown')::citext as reason,
	COALESCE(address, 'Unknown')::citext as address,
	COALESCE(flash_version, 'Unknown')::citext as flash_version,
	COALESCE(product, '')::citext as product,
	COALESCE(version, '')::citext as version,
	COALESCE(os_name, 'Unknown')::citext as os_name,
	os_version::citext as os_version,
	coalesce(process_type, 'Browser') as process_type,
	COALESCE(url2domain(url),'') as domain,
	email, user_comments, url, app_notes,
	release_channel, hangid as hang_id,
	cpu_name as architecture,
	get_cores(cpu_info) as cores
from reports
where date_processed >= fromtime and date_processed < ( fromtime + fortime )
	and completed_datetime is not null;

-- check for no data

PERFORM 1 FROM new_reports
LIMIT 1;
IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'no report data found for period %',fromtime;
	ELSE
		DROP TABLE new_reports;
		RETURN TRUE;
	END IF;
END IF;

create index new_reports_uuid on new_reports(uuid);
create index new_reports_signature on new_reports(signature);
create index new_reports_address on new_reports(address);
create index new_reports_domain on new_reports(domain);
create index new_reports_reason on new_reports(reason);
analyze new_reports;

-- trim reports_bad to 2 days of data
DELETE FROM reports_bad
WHERE date_processed < ( now() - interval '2 days' );

-- delete any reports which were already processed
delete from new_reports
using reports_clean
where new_reports.uuid = reports_clean.uuid
and reports_clean.date_processed between ( fromtime - interval '1 day' )
and ( fromtime + fortime + interval '1 day' );

-- RULE: strip leading "0.0.0 Linux" from Linux version strings
UPDATE new_reports
SET os_version = regexp_replace(os_version, $x$[0\.]+\s+Linux\s+$x$, '')
WHERE os_version LIKE '%0.0.0%'
	AND os_name ILIKE 'Linux%';

-- RULE: IF camino, SET release_channel for camino 2.1
-- camino 2.2 will have release_channel properly set

UPDATE reports_clean_buffer
SET release_channel = 'release'
WHERE product ilike 'camino'
	AND version like '2.1%'
	AND version not like '%pre%';

UPDATE reports_clean_buffer
SET release_channel = 'beta'
WHERE product ilike 'camino'
	AND version like '2.1%'
	AND version like '%pre%';

-- insert signatures into signature list
insert into signatures ( signature, first_report, first_build )
select newsigs.* from (
	select signature::citext as signature,
		min(date_processed) as first_report,
		min(build_numeric(build)) as first_build
	from new_reports
	group by signature::citext ) as newsigs
left join signatures
	on newsigs.signature = signatures.signature
where signatures.signature IS NULL;

-- insert oses into os list

PERFORM update_os_versions_new_reports();

-- insert reasons into reason list

PERFORM update_lookup_new_reports('reason');

-- insert addresses into address list

PERFORM update_lookup_new_reports('address');

-- insert flash_versions into flash version list

PERFORM update_lookup_new_reports('flash_version');

-- insert domains into the domain list

PERFORM update_lookup_new_reports('domain');

-- do not update reports_duplicates
-- this procedure assumes that it has already been run
-- later reports_duplicates will become a callable function from this function
-- maybe

-- create empty reports_clean_buffer
create temporary table reports_clean_buffer
(
uuid text not null primary key,
date_processed timestamptz not null,
client_crash_date timestamptz,
product_version_id int,
build numeric,
signature_id int,
install_age interval,
uptime interval,
reason_id int,
address_id int,
os_name citext,
os_version_id int,
major_version int,
minor_version int,
hang_id text,
flash_version_id int,
process_type citext,
release_channel citext,
duplicate_of text,
domain_id int,
architecture citext,
cores int
) on commit drop ;

-- populate the new buffer with uuid, date_processed,
-- client_crash_date, build, install_time, uptime,
-- hang_id, duplicate_of, reason, address, flash_version,
-- release_channel

-- RULE: convert install_age, uptime to INTERVAL
-- RULE: convert reason, address, flash_version, URL domain to lookup list ID
-- RULE: add possible duplicate UUID link
-- RULE: convert release_channel to canonical release_channel based on
--	channel match list

INSERT INTO reports_clean_buffer
SELECT new_reports.uuid,
	new_reports.date_processed,
	client_crash_date,
	0,
	build_numeric(build),
	signatures.signature_id,
	install_age * interval '1 second',
	uptime * interval '1 second',
	reasons.reason_id,
	addresses.address_id,
	NULL, NULL, 0, 0,
	hang_id,
	flash_versions.flash_version_id,
	process_type,
	release_channel_matches.release_channel,
	reports_duplicates.duplicate_of,
	domains.domain_id,
	architecture,
	cores
FROM new_reports
LEFT OUTER JOIN release_channel_matches ON new_reports.release_channel ILIKE release_channel_matches.match_string
LEFT OUTER JOIN signatures ON new_reports.signature = signatures.signature
LEFT OUTER JOIN reasons ON new_reports.reason = reasons.reason
LEFT OUTER JOIN addresses ON new_reports.address = addresses.address
LEFT OUTER JOIN flash_versions ON new_reports.flash_version = flash_versions.flash_version
LEFT OUTER JOIN reports_duplicates ON new_reports.uuid = reports_duplicates.uuid
	AND reports_duplicates.date_processed BETWEEN (fromtime - interval '1 day') AND (fromtime + interval '1 day' )
LEFT OUTER JOIN domains ON new_reports.domain = domains.domain
ORDER BY new_reports.uuid;

ANALYZE reports_clean_buffer;

-- populate product_version

	-- RULE: populate releases/aurora/nightlies based on matching product name
	-- and version with release_version

UPDATE reports_clean_buffer
SET product_version_id = product_versions.product_version_id
FROM product_versions, new_reports
WHERE reports_clean_buffer.uuid = new_reports.uuid
	AND new_reports.product = product_versions.product_name
	AND new_reports.version = product_versions.release_version
	AND reports_clean_buffer.release_channel = product_versions.build_type
	AND reports_clean_buffer.release_channel <> 'beta';

	-- RULE: populate betas based on matching product_name, version with
	-- release_version, and build number.

UPDATE reports_clean_buffer
SET product_version_id = product_versions.product_version_id
FROM product_versions JOIN product_version_builds USING (product_version_id), new_reports
WHERE reports_clean_buffer.uuid = new_reports.uuid
	AND new_reports.product = product_versions.product_name
	AND new_reports.version = product_versions.release_version
	AND reports_clean_buffer.release_channel = product_versions.build_type
	AND reports_clean_buffer.build = product_version_builds.build_id
	AND reports_clean_buffer.release_channel = 'beta';

-- populate os_name and os_version

-- RULE: set os_name based on name matching strings

UPDATE reports_clean_buffer SET os_name = os_name_matches.os_name
FROM new_reports, os_name_matches
WHERE reports_clean_buffer.uuid = new_reports.uuid
	AND new_reports.os_name ILIKE os_name_matches.match_string;

-- RULE: if os_name isn't recognized, set major and minor versions to 0.
UPDATE reports_clean_buffer SET os_name = 'Unknown',
	major_version = 0, minor_version = 0
WHERE os_name IS NULL OR os_name NOT IN ( SELECT os_name FROM os_names );

-- RULE: set minor_version based on parsing the os_version string
-- for a second decimal between 0 and 1000 if os_name is not Unknown
UPDATE reports_clean_buffer
SET minor_version = substring(os_version from $x$^\d+\.(\d+)$x$)::int
FROM new_reports
WHERE new_reports.uuid = reports_clean_buffer.uuid
	and os_version ~ $x$^\d+$x$
	and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
	and substring(os_version from $x$^\d+\.(\d+)$x$)::numeric < 1000
	and reports_clean_buffer.os_name <> 'Unknown';

-- RULE: set major_version based on parsing the os_vesion string
-- for a number between 0 and 1000, but there's no minor version
UPDATE reports_clean_buffer
SET major_version = substring(os_version from $x$^(\d+)$x$)::int
FROM new_reports
WHERE new_reports.uuid = reports_clean_buffer.uuid
	AND os_version ~ $x$^\d+$x$
		and substring(os_version from $x$^(\d+)$x$)::numeric < 1000
		and reports_clean_buffer.major_version = 0
		and reports_clean_buffer.os_name <> 'Unknown';

UPDATE reports_clean_buffer
SET os_version_id = os_versions.os_version_id
FROM os_versions
WHERE reports_clean_buffer.os_name = os_versions.os_name
	AND reports_clean_buffer.major_version = os_versions.major_version
	AND reports_clean_buffer.minor_version = os_versions.minor_version;

-- copy to reports_bad and delete bad reports
-- RULE: currently we purge reports which have any of the following
-- missing or invalid: product_version, release_channel, os_name

INSERT INTO reports_bad ( uuid, date_processed )
SELECT uuid, date_processed
FROM reports_clean_buffer
WHERE product_version_id = 0
	OR release_channel IS NULL
	OR signature_id IS NULL;

DELETE FROM reports_clean_buffer
WHERE product_version_id = 0
	OR release_channel IS NULL
	OR signature_id IS NULL;

-- check if the right reports_clean partition exists, or create it

rc_part := reports_clean_weekly_partition(fromtime, 'reports_clean');

-- check if the right reports_user_info partition exists, or create it

rui_part := reports_clean_weekly_partition(fromtime, 'reports_user_info');

-- copy to reports_clean

EXECUTE 'INSERT INTO ' || rc_part || '
	( uuid, date_processed, client_crash_date, product_version_id,
	  build, signature_id, install_age, uptime,
reason_id, address_id, os_name, os_version_id,
hang_id, flash_version_id, process_type, release_channel,
duplicate_of, domain_id, architecture, cores )
SELECT uuid, date_processed, client_crash_date, product_version_id,
	  build, signature_id, install_age, uptime,
reason_id, address_id, os_name, os_version_id,
hang_id, flash_version_id, process_type, release_channel,
duplicate_of, domain_id, architecture, cores
FROM reports_clean_buffer;';

IF analyze_it THEN
	EXECUTE 'ANALYZE ' || rc_part;
END IF;

-- copy to reports_user_info

EXECUTE 'INSERT INTO ' || rui_part || $$
	( uuid, date_processed, email, user_comments, url, app_notes )
SELECT new_reports.uuid, new_reports.date_processed,
		email, user_comments, url, app_notes
FROM new_reports JOIN reports_clean_buffer USING ( uuid )
WHERE email <> '' OR user_comments <> ''
	OR url <> '' OR app_notes <> '';$$;

EXECUTE 'ANALYZE ' || rui_part;

-- exit
DROP TABLE new_reports;
DROP TABLE reports_clean_buffer;
RETURN TRUE;

END;
$_$;


ALTER FUNCTION public.update_reports_clean(fromtime timestamp with time zone, fortime interval, checkdata boolean, analyze_it boolean) OWNER TO postgres;

--
-- TOC entry 471 (class 1255 OID 81112)
-- Dependencies: 7
-- Name: update_reports_clean_cron(timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_reports_clean_cron(crontime timestamp with time zone) RETURNS boolean
    LANGUAGE sql
    AS $_$
SELECT update_reports_clean( date_trunc('hour', $1) - interval '1 hour' );
$_$;


ALTER FUNCTION public.update_reports_clean_cron(crontime timestamp with time zone) OWNER TO postgres;

--
-- TOC entry 484 (class 1255 OID 81113)
-- Dependencies: 7 1826
-- Name: update_reports_duplicates(timestamp with time zone, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_reports_duplicates(start_time timestamp with time zone, end_time timestamp with time zone) RETURNS integer
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

create temporary table new_reports_duplicates
on commit drop
as
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
	left outer join reports_duplicates 
		ON new_reports_duplicates.uuid = reports_duplicates.uuid
		AND reports_duplicates.date_processed > ( start_time - INTERVAL '1 day' )
		AND reports_duplicates.date_processed < ( end_time + INTERVAL '1 day' )
where reports_duplicates.uuid IS NULL;

-- done return number of dups found and exit
DROP TABLE new_reports_duplicates;
RETURN new_dups;
end;$$;


ALTER FUNCTION public.update_reports_duplicates(start_time timestamp with time zone, end_time timestamp with time zone) OWNER TO postgres;

--
-- TOC entry 485 (class 1255 OID 81114)
-- Dependencies: 7 1826
-- Name: update_signatures(date, boolean); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_signatures(updateday date, checkdata boolean DEFAULT true) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET "TimeZone" TO 'UTC'
    AS $$
BEGIN

-- new function for updating signature information post-rapid-release
-- designed to be run once per UTC day.
-- running it repeatedly won't cause issues
-- combines NULL and empty signatures

-- create temporary table

create temporary table new_signatures
on commit drop as
select coalesce(signature,'') as signature, 
	product::citext as product, 
	version::citext as version, 
	build, NULL::INT as product_version_id,
	min(date_processed) as first_report
from reports
where date_processed >= updateday
	and date_processed <= (updateday + 1)
group by signature, product, version, build;

PERFORM 1 FROM new_signatures;
IF NOT FOUND THEN
	IF checkdata THEN
		RAISE EXCEPTION 'no signature data found in reports for date %',updateday;
	END IF;
END IF;

analyze new_signatures;

-- add product IDs for betas and matching builds
update new_signatures
set product_version_id = product_versions.product_version_id
from product_versions JOIN product_version_builds
	ON product_versions.product_version_id = product_version_builds.product_version_id
where product_versions.release_version = new_signatures.version
	and product_versions.product_name = new_signatures.product
	and product_version_builds.build_id::text = new_signatures.build;

-- add product IDs for builds that don't match
update new_signatures
set product_version_id = product_versions.product_version_id
from product_versions JOIN product_version_builds
	ON product_versions.product_version_id = product_version_builds.product_version_id
where product_versions.release_version = new_signatures.version
	and product_versions.product_name = new_signatures.product
	and product_versions.build_type IN ('release','nightly', 'aurora')
	and new_signatures.product_version_id IS NULL;

analyze new_signatures;

-- update signatures table

insert into signatures ( signature, first_report, first_build )
select new_signatures.signature, min(new_signatures.first_report),
	min(build_numeric(new_signatures.build))
from new_signatures
left outer join signatures
	on new_signatures.signature = signatures.signature
where signatures.signature is null
	and new_signatures.product_version_id is not null
group by new_signatures.signature;

-- update signature_products table

insert into signature_products ( signature_id, product_version_id, first_report )
select signatures.signature_id,
		new_signatures.product_version_id,
		min(new_signatures.first_report)
from new_signatures JOIN signatures
	ON new_signatures.signature = signatures.signature
	left outer join signature_products
		on signatures.signature_id = signature_products.signature_id
		and new_signatures.product_version_id = signature_products.product_version_id
where new_signatures.product_version_id is not null
	and signature_products.signature_id is null
group by signatures.signature_id,
		new_signatures.product_version_id;

-- recreate the rollup from scratch

DELETE FROM signature_products_rollup;

insert into signature_products_rollup ( signature_id, product_name, ver_count, version_list )
select
	signature_id, product_name, count(*) as ver_count,
		array_accum(version_string ORDER BY product_versions.version_sort)
from signature_products JOIN product_versions
	USING (product_version_id)
group by signature_id, product_name;

-- recreate signature_bugs from scratch

DELETE FROM signature_bugs_rollup;

INSERT INTO signature_bugs_rollup (signature_id, bug_count, bug_list)
SELECT signature_id, count(*), array_accum(bug_id)
FROM signatures JOIN bug_associations USING (signature)
GROUP BY signature_id;

return true;
end;
$$;


ALTER FUNCTION public.update_signatures(updateday date, checkdata boolean) OWNER TO postgres;

--
-- TOC entry 486 (class 1255 OID 81115)
-- Dependencies: 1826 7
-- Name: update_socorro_db_version(text, date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_socorro_db_version(newversion text, backfilldate date DEFAULT NULL::date) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE rerun BOOLEAN;
BEGIN
	SELECT current_version = newversion
	INTO rerun
	FROM socorro_db_version;
	
	IF rerun THEN
		RAISE NOTICE 'This database is already set to version %.  If you have deliberately rerun the upgrade scripts, then this is as expected.  If not, then there is something wrong.',newversion;
	ELSE
		UPDATE socorro_db_version SET current_version = newversion;
	END IF;
	
	INSERT INTO socorro_db_version_history ( version, upgraded_on, backfill_to )
		VALUES ( newversion, now(), backfilldate );
	
	RETURN true;
END; $$;


ALTER FUNCTION public.update_socorro_db_version(newversion text, backfilldate date) OWNER TO postgres;

--
-- TOC entry 538 (class 1255 OID 84674)
-- Dependencies: 1826 7
-- Name: update_tcbs(date, boolean, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_tcbs(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this procedure goes throught the daily TCBS update for the
-- new TCBS table
-- designed to be run only once for each day
-- this new version depends on reports_clean

-- check that it hasn't already been run

IF checkdata THEN
	PERFORM 1 FROM tcbs
	WHERE report_date = updateday LIMIT 1;
	IF FOUND THEN
		RAISE NOTICE 'TCBS has already been run for the day %.',updateday;
		RETURN FALSE;
	END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RETURN FALSE;
	END IF;
END IF;

-- populate the matview for regular releases

INSERT INTO tcbs (
	signature_id, report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count
)
SELECT signature_id, updateday,
	product_version_id,
	process_type, release_channel,
	count(*),
	sum(case when os_name = 'Windows' THEN 1 else 0 END),
	sum(case when os_name = 'Mac OS X' THEN 1 else 0 END),
	sum(case when os_name = 'Linux' THEN 1 else 0 END),
    count(hang_id),
    sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
FROM reports_clean
	JOIN product_versions USING (product_version_id)
	WHERE utc_day_is(date_processed, updateday)
		AND tstz_between(date_processed, build_date, sunset_date)
GROUP BY signature_id, updateday, product_version_id,
	process_type, release_channel;

-- populate summary statistics for rapid beta parent records

INSERT INTO tcbs (
	signature_id, report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count )
SELECT signature_id, updateday, rapid_beta_id,
	process_type, release_channel,
	sum(report_count), sum(win_count), sum(mac_count), sum(lin_count),
	sum(hang_count), sum(startup_count)
FROM tcbs
	JOIN product_versions USING (product_version_id)
WHERE report_date = updateday
GROUP BY signature_id, updateday, rapid_beta_id,
	process_type, release_channel;

-- tcbs_ranking removed until it's being used

-- done
RETURN TRUE;
END;
$$;


ALTER FUNCTION public.update_tcbs(updateday date, checkdata boolean, check_period interval) OWNER TO postgres;

--
-- TOC entry 537 (class 1255 OID 84673)
-- Dependencies: 7 1826
-- Name: update_tcbs_build(date, boolean, interval); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_tcbs_build(updateday date, checkdata boolean DEFAULT true, check_period interval DEFAULT '01:00:00'::interval) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    SET client_min_messages TO 'ERROR'
    AS $$
BEGIN
-- this procedure goes throught the daily TCBS update for the
-- new TCBS table
-- designed to be run only once for each day
-- this new version depends on reports_clean

-- check that it hasn't already been run

IF checkdata THEN
	PERFORM 1 FROM tcbs_build
	WHERE report_date = updateday LIMIT 1;
	IF FOUND THEN
		RAISE NOTICE 'TCBS has already been run for the day %.',updateday;
		RETURN FALSE;
	END IF;
END IF;

-- check if reports_clean is complete
IF NOT reports_clean_done(updateday, check_period) THEN
	IF checkdata THEN
		RAISE EXCEPTION 'Reports_clean has not been updated to the end of %',updateday;
	ELSE
		RAISE INFO 'reports_clean not updated';
		RETURN FALSE;
	END IF;
END IF;

-- populate the matview for nightly and aurora

INSERT INTO tcbs_build (
	signature_id, build_date,
	report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count
)
SELECT signature_id, build_date(build),
	updateday, product_version_id,
	process_type, release_channel,
	count(*),
	sum(case when os_name = 'Windows' THEN 1 else 0 END),
	sum(case when os_name = 'Mac OS X' THEN 1 else 0 END),
	sum(case when os_name = 'Linux' THEN 1 else 0 END),
    count(hang_id),
    sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
FROM reports_clean
	JOIN product_versions USING (product_version_id)
	JOIN products USING ( product_name )
WHERE utc_day_is(date_processed, updateday)
		AND tstz_between(date_processed, build_date, sunset_date)
	-- 7 days of builds only
	AND updateday <= ( build_date(build) + 6 )
	-- only nightly, aurora, and rapid beta
	AND reports_clean.release_channel IN ( 'nightly','aurora' )
	AND version_matches_channel(version_string, release_channel)
GROUP BY signature_id, build_date(build), product_version_id,
	process_type, release_channel;

-- populate for rapid beta parent records only

INSERT INTO tcbs_build (
	signature_id, build_date,
	report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count,
	startup_count
)
SELECT signature_id, build_date(build),
	updateday, rapid_beta_id,
	process_type, release_channel,
	count(*),
	sum(case when os_name = 'Windows' THEN 1 else 0 END),
	sum(case when os_name = 'Mac OS X' THEN 1 else 0 END),
	sum(case when os_name = 'Linux' THEN 1 else 0 END),
    count(hang_id),
    sum(case when uptime < INTERVAL '1 minute' THEN 1 else 0 END)
FROM reports_clean
	JOIN product_versions USING (product_version_id)
	JOIN products USING ( product_name )
WHERE utc_day_is(date_processed, updateday)
		AND tstz_between(date_processed, build_date, sunset_date)
	-- 7 days of builds only
	AND updateday <= ( build_date(build) + 6 )
	-- only nightly, aurora, and rapid beta
	AND reports_clean.release_channel = 'beta'
	AND rapid_beta_id is not null
GROUP BY signature_id, build_date(build), rapid_beta_id,
	process_type, release_channel;

-- tcbs_ranking removed until it's being used

-- done
RETURN TRUE;
END;
$$;


ALTER FUNCTION public.update_tcbs_build(updateday date, checkdata boolean, check_period interval) OWNER TO postgres;

--
-- TOC entry 487 (class 1255 OID 81117)
-- Dependencies: 7 1420
-- Name: url2domain(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION url2domain(some_url text) RETURNS citext
    LANGUAGE sql IMMUTABLE
    AS $_$
select substring($1 FROM $x$^([\w:]+:/+(?:\w+\.)*\w+).*$x$)::citext
$_$;


ALTER FUNCTION public.url2domain(some_url text) OWNER TO postgres;

--
-- TOC entry 488 (class 1255 OID 81118)
-- Dependencies: 7
-- Name: utc_day_is(timestamp with time zone, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION utc_day_is(timestamp with time zone, timestamp without time zone) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
select $1 >= ( $2 AT TIME ZONE 'UTC' )
	AND $1 < ( ( $2 + INTERVAL '1 day' ) AT TIME ZONE 'UTC'  );
$_$;


ALTER FUNCTION public.utc_day_is(timestamp with time zone, timestamp without time zone) OWNER TO postgres;

--
-- TOC entry 489 (class 1255 OID 81119)
-- Dependencies: 7
-- Name: utc_day_near(timestamp with time zone, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION utc_day_near(timestamp with time zone, timestamp without time zone) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $_$
select $1 > ( $2 AT TIME ZONE 'UTC' - INTERVAL '1 day' )
AND $1 < ( $2 AT TIME ZONE 'UTC' + INTERVAL '2 days' )
$_$;


ALTER FUNCTION public.utc_day_near(timestamp with time zone, timestamp without time zone) OWNER TO postgres;

--
-- TOC entry 490 (class 1255 OID 81120)
-- Dependencies: 1826 7
-- Name: validate_lookup(text, text, text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

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


ALTER FUNCTION public.validate_lookup(ltable text, lcol text, lval text, lmessage text) OWNER TO postgres;

--
-- TOC entry 491 (class 1255 OID 81121)
-- Dependencies: 1420 7
-- Name: version_matches_channel(text, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_matches_channel(version text, channel citext) RETURNS boolean
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
SELECT CASE WHEN $1 ILIKE '%a1' AND $2 ILIKE 'nightly%'
	THEN TRUE
WHEN $1 ILIKE '%a2' AND $2 = 'aurora' 
	THEN TRUE
WHEN $1 ILIKE '%esr' AND $2 IN ( 'release', 'esr' )
	THEN TRUE
WHEN $1 NOT ILIKE '%a%' AND $1 NOT ILIKE '%esr' AND $2 IN ( 'beta', 'release' )
	THEN TRUE
ELSE FALSE END;
$_$;


ALTER FUNCTION public.version_matches_channel(version text, channel citext) OWNER TO postgres;

--
-- TOC entry 493 (class 1255 OID 81122)
-- Dependencies: 1420 1420 1826 7
-- Name: version_sort(text, integer, citext); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_sort(version text, beta_no integer DEFAULT 0, channel citext DEFAULT ''::citext) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $_$
DECLARE vne TEXT[];
	sortstring TEXT;
	dex INT;
BEGIN

	-- regexp the version number into tokens
	vne := regexp_matches( version, $x$^(\d+)\.(\d+)([a-zA-Z]*)(\d*)(?:\.(\d+))?(?:([a-zA-Z]+)(\d*))?.*$$x$ );
	
	-- bump betas after the 3rd digit back
	vne[3] := coalesce(nullif(vne[3],''),vne[6]);
	vne[4] := coalesce(nullif(vne[4],''),vne[7]);

	-- handle betal numbers
	IF beta_no > 0 THEN
		vne[3] := 'b';
		vne[4] := beta_no::TEXT;
	END IF;
	
	--handle final betas
	IF version LIKE '%(beta)%' THEN
		vne[3] := 'b';
		vne[4] := '99';
	END IF;
	
	--handle release channels
	CASE channel
		WHEN 'nightly' THEN
			vne[3] := 'a';
			vne[4] := '1';
		WHEN 'aurora' THEN
			vne[3] := 'a';
			vne[4] := '2';
		WHEN 'beta' THEN
			vne[3] := 'b';
			vne[4] := COALESCE(nullif(vne[4],''),99);
		WHEN 'release' THEN
			vne[3] := 'r';
			vne[4] := '0';
		WHEN 'ESR' THEN
			vne[3] := 'x';
			vne[4] := '0';
		ELSE
			NULL;
	END CASE;
	
	-- fix character otherwise
	IF vne[3] = 'esr' THEN
		vne[3] := 'x';
	ELSE
		vne[3] := COALESCE(nullif(vne[3],''),'r');
	END IF;
	
	--assemble string
	sortstring := version_sort_digit(vne[1]) 
		|| version_sort_digit(vne[2]) 
		|| version_sort_digit(vne[5]) 
		|| vne[3]
		|| version_sort_digit(vne[4]) ;
		
	RETURN sortstring;
END;$_$;


ALTER FUNCTION public.version_sort(version text, beta_no integer, channel citext) OWNER TO postgres;

--
-- TOC entry 494 (class 1255 OID 81123)
-- Dependencies: 7
-- Name: version_sort_digit(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_sort_digit(digit text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts an individual part of a version number
-- into a three-digit sortable string
SELECT CASE WHEN $1 <> '' THEN
	to_char($1::INT,'FM000')
	ELSE '000' END;
$_$;


ALTER FUNCTION public.version_sort_digit(digit text) OWNER TO postgres;

--
-- TOC entry 495 (class 1255 OID 81124)
-- Dependencies: 1826 7
-- Name: version_sort_trigger(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_sort_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
	-- on insert or update, makes sure that the
	-- version_sort column is correct
	NEW.version_sort := old_version_sort(NEW.version);
	RETURN NEW;
END;
$$;


ALTER FUNCTION public.version_sort_trigger() OWNER TO postgres;

--
-- TOC entry 496 (class 1255 OID 81125)
-- Dependencies: 1826 7
-- Name: version_sort_update_trigger_after(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_sort_update_trigger_after() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
-- update sort keys
PERFORM product_version_sort_number(NEW.product);
RETURN NEW;
END; $$;


ALTER FUNCTION public.version_sort_update_trigger_after() OWNER TO postgres;

--
-- TOC entry 497 (class 1255 OID 81126)
-- Dependencies: 7 1826
-- Name: version_sort_update_trigger_before(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_sort_update_trigger_before() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
-- updates productdims_version_sort
-- should be called only by a cascading update from productdims

-- update sort record
SELECT s1n1,s1s1,s1n2,s1s2,
s2n1,s2s1,s2n2,s2s2,
s3n1,s3s1,s3n2,s3s2,
ext
INTO 
NEW.sec1_num1,NEW.sec1_string1,NEW.sec1_num2,NEW.sec1_string2,
NEW.sec2_num1,NEW.sec2_string1,NEW.sec2_num2,NEW.sec2_string2,
NEW.sec3_num1,NEW.sec3_string1,NEW.sec3_num2,NEW.sec3_string2,
NEW.extra
FROM tokenize_version(NEW.version);

RETURN NEW;
END; $$;


ALTER FUNCTION public.version_sort_update_trigger_before() OWNER TO postgres;

--
-- TOC entry 498 (class 1255 OID 81127)
-- Dependencies: 7
-- Name: version_string(text, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_string(version text, beta_number integer) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts a stripped version and a beta number
-- into a version string
SELECT CASE WHEN $2 <> 0 THEN
	$1 || 'b' || $2
ELSE
	$1
END;
$_$;


ALTER FUNCTION public.version_string(version text, beta_number integer) OWNER TO postgres;

--
-- TOC entry 492 (class 1255 OID 81128)
-- Dependencies: 7
-- Name: version_string(text, integer, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_string(version text, beta_number integer, channel text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts a stripped version and a beta number
-- into a version string
SELECT CASE WHEN $2 <> 0 THEN
	$1 || 'b' || $2
WHEN $3 ILIKE 'nightly' THEN
	$1 || 'a1'
WHEN $3 ILIKE 'aurora' THEN
	$1 || 'a2'
ELSE
	$1
END;
$_$;


ALTER FUNCTION public.version_string(version text, beta_number integer, channel text) OWNER TO postgres;

--
-- TOC entry 499 (class 1255 OID 81129)
-- Dependencies: 7 1826
-- Name: watch_report_processing(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION watch_report_processing(INOUT run_min integer, OUT report_count integer, OUT min_time interval, OUT max_time interval, OUT avg_time interval) RETURNS record
    LANGUAGE plpgsql
    AS $$
declare reprec RECORD;
    cur_min interval;
    cur_max interval := '0 seconds';
    cur_tot interval := '0 seconds';
    cur_avg interval;
    cur_lag interval;
    cur_count int;
    last_report timestamp;
    end_time timestamptz;
    cur_time timestamptz;
    start_count int;
    start_time timestamptz;
    cur_loop INT := 0;
begin
  end_time := now() + run_min * interval '1 minute';
  start_time := now();

  select count(*) into start_count
  from reports where date_processed > ( start_time - interval '2 days' )
    and completed_datetime is not null;
  cur_time = clock_timestamp();

  while  cur_time < end_time loop

    select max(date_processed),
      count(*) - start_count
    into last_report, cur_count
    from reports where date_processed > ( start_time - interval '2 days' )
      and completed_datetime is not null;

    cur_loop := cur_loop + 1;
    cur_lag := cur_time - last_report;
    cur_tot := cur_tot + cur_lag;
    cur_min := LEAST(cur_min, cur_lag);
    cur_max := GREATEST(cur_max, cur_lag);
    cur_avg := cur_tot / cur_loop;

    RAISE INFO 'At: % Last Report: %',to_char(cur_time,'Mon DD HH24:MI:SS'),to_char(last_report,'Mon DD HH24:MI:SS');
    RAISE INFO 'Count: %   Lag: %  Min: %   Max: %   Avg: %', cur_count, to_char(cur_lag,'HH24:MI:SS'),to_char(cur_min, 'HH24:MI:SS'),to_char(cur_max, 'HH24:MI:SS'),to_char(cur_avg,'HH24:MI:SS');

    perform pg_sleep(10);
    cur_time := clock_timestamp();

  end loop;

  report_count := cur_count;
  min_time := cur_min;
  max_time := cur_max;
  avg_time := cur_avg;
  return;

  end;
$$;


ALTER FUNCTION public.watch_report_processing(INOUT run_min integer, OUT report_count integer, OUT min_time interval, OUT max_time interval, OUT avg_time interval) OWNER TO postgres;

--
-- TOC entry 500 (class 1255 OID 81130)
-- Dependencies: 7
-- Name: week_begins_partition(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION week_begins_partition(partname text) RETURNS timestamp with time zone
    LANGUAGE sql IMMUTABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT to_timestamp( substring($1 from $x$\d+$$x$), 'YYYYMMDD' );
$_$;


ALTER FUNCTION public.week_begins_partition(partname text) OWNER TO postgres;

--
-- TOC entry 501 (class 1255 OID 81131)
-- Dependencies: 7
-- Name: week_begins_partition_string(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION week_begins_partition_string(partname text) RETURNS text
    LANGUAGE sql IMMUTABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT to_char( week_begins_partition( $1 ), 'YYYY-MM-DD' ) || ' 00:00:00 UTC';
$_$;


ALTER FUNCTION public.week_begins_partition_string(partname text) OWNER TO postgres;

--
-- TOC entry 502 (class 1255 OID 81132)
-- Dependencies: 7
-- Name: week_begins_utc(timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION week_begins_utc(timestamp with time zone) RETURNS timestamp with time zone
    LANGUAGE sql STABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT date_trunc('week', $1);
$_$;


ALTER FUNCTION public.week_begins_utc(timestamp with time zone) OWNER TO postgres;

--
-- TOC entry 503 (class 1255 OID 81133)
-- Dependencies: 7
-- Name: week_ends_partition(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION week_ends_partition(partname text) RETURNS timestamp with time zone
    LANGUAGE sql IMMUTABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT to_timestamp( substring($1 from $x$\d+$$x$), 'YYYYMMDD' ) + INTERVAL '7 days';
$_$;


ALTER FUNCTION public.week_ends_partition(partname text) OWNER TO postgres;

--
-- TOC entry 504 (class 1255 OID 81134)
-- Dependencies: 7
-- Name: week_ends_partition_string(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION week_ends_partition_string(partname text) RETURNS text
    LANGUAGE sql IMMUTABLE
    SET "TimeZone" TO 'UTC'
    AS $_$
SELECT to_char( week_ends_partition( $1 ), 'YYYY-MM-DD' ) || ' 00:00:00 UTC';
$_$;


ALTER FUNCTION public.week_ends_partition_string(partname text) OWNER TO postgres;

--
-- TOC entry 516 (class 1255 OID 81135)
-- Dependencies: 7 1826
-- Name: weekly_report_partitions(integer, timestamp with time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION weekly_report_partitions(numweeks integer DEFAULT 2, targetdate timestamp with time zone DEFAULT NULL::timestamp with time zone) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
-- this function checks that we have partitions two weeks into
-- the future for each of the tables associated with
-- reports
-- designed to be called as a cronjob once a week
-- controlled by the data in the reports_partition_info table
DECLARE 
	thisweek DATE;
	dex INT := 1;
	weeknum INT := 0;
	tabinfo RECORD;
BEGIN
	targetdate := COALESCE(targetdate, now());
	thisweek := date_trunc('week', targetdate)::date;
	
	WHILE weeknum <= numweeks LOOP
		FOR tabinfo IN SELECT * FROM report_partition_info
			ORDER BY build_order LOOP
			
			PERFORM create_weekly_partition ( 
				tablename := tabinfo.table_name,
				theweek := thisweek,
				uniques := tabinfo.keys,
				indexes := tabinfo.indexes,
				fkeys := tabinfo.fkeys,
				tableowner := 'breakpad_rw'
			);

		END LOOP;
		weeknum := weeknum + 1;
		thisweek := thisweek + 7;
	END LOOP;

	RETURN TRUE;
	
END; $$;


ALTER FUNCTION public.weekly_report_partitions(numweeks integer, targetdate timestamp with time zone) OWNER TO postgres;

--
-- TOC entry 1827 (class 1255 OID 81136)
-- Dependencies: 7
-- Name: array_accum(anyelement); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE array_accum(anyelement) (
    SFUNC = array_append,
    STYPE = anyarray,
    INITCOND = '{}'
);


ALTER AGGREGATE public.array_accum(anyelement) OWNER TO postgres;

--
-- TOC entry 1828 (class 1255 OID 81137)
-- Dependencies: 1420 346 7
-- Name: content_count(citext, integer); Type: AGGREGATE; Schema: public; Owner: breakpad_rw
--

CREATE AGGREGATE content_count(citext, integer) (
    SFUNC = content_count_state,
    STYPE = integer,
    INITCOND = '0'
);


ALTER AGGREGATE public.content_count(citext, integer) OWNER TO breakpad_rw;

--
-- TOC entry 2537 (class 2617 OID 81140)
-- Dependencies: 329 7 1420 1420
-- Name: >; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR > (
    PROCEDURE = citext_gt,
    LEFTARG = citext,
    RIGHTARG = citext,
    COMMUTATOR = <,
    NEGATOR = <=,
    RESTRICT = scalargtsel,
    JOIN = scalargtjoinsel
);


ALTER OPERATOR public.> (citext, citext) OWNER TO postgres;

--
-- TOC entry 1829 (class 1255 OID 81141)
-- Dependencies: 1420 1420 331 2537 7
-- Name: max(citext); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE max(citext) (
    SFUNC = citext_larger,
    STYPE = citext,
    SORTOP = >
);


ALTER AGGREGATE public.max(citext) OWNER TO postgres;

--
-- TOC entry 2538 (class 2617 OID 81138)
-- Dependencies: 1420 333 7 1420
-- Name: <; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR < (
    PROCEDURE = citext_lt,
    LEFTARG = citext,
    RIGHTARG = citext,
    COMMUTATOR = >,
    NEGATOR = >=,
    RESTRICT = scalarltsel,
    JOIN = scalarltjoinsel
);


ALTER OPERATOR public.< (citext, citext) OWNER TO postgres;

--
-- TOC entry 1830 (class 1255 OID 81143)
-- Dependencies: 2538 1420 1420 335 7
-- Name: min(citext); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE min(citext) (
    SFUNC = citext_smaller,
    STYPE = citext,
    SORTOP = <
);


ALTER AGGREGATE public.min(citext) OWNER TO postgres;

--
-- TOC entry 1831 (class 1255 OID 81144)
-- Dependencies: 391 1420 7
-- Name: plugin_count(citext, integer); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE plugin_count(citext, integer) (
    SFUNC = plugin_count_state,
    STYPE = integer,
    INITCOND = '0'
);


ALTER AGGREGATE public.plugin_count(citext, integer) OWNER TO postgres;

--
-- TOC entry 2539 (class 2617 OID 81146)
-- Dependencies: 413 7 1420 1420
-- Name: !~; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR !~ (
    PROCEDURE = texticregexne,
    LEFTARG = citext,
    RIGHTARG = citext,
    NEGATOR = ~,
    RESTRICT = icregexnesel,
    JOIN = icregexnejoinsel
);


ALTER OPERATOR public.!~ (citext, citext) OWNER TO postgres;

--
-- TOC entry 2540 (class 2617 OID 81148)
-- Dependencies: 1420 7 414
-- Name: !~; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR !~ (
    PROCEDURE = texticregexne,
    LEFTARG = citext,
    RIGHTARG = text,
    NEGATOR = ~,
    RESTRICT = icregexnesel,
    JOIN = icregexnejoinsel
);


ALTER OPERATOR public.!~ (citext, text) OWNER TO postgres;

--
-- TOC entry 2541 (class 2617 OID 81150)
-- Dependencies: 1420 413 1420 7
-- Name: !~*; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR !~* (
    PROCEDURE = texticregexne,
    LEFTARG = citext,
    RIGHTARG = citext,
    NEGATOR = ~*,
    RESTRICT = icregexnesel,
    JOIN = icregexnejoinsel
);


ALTER OPERATOR public.!~* (citext, citext) OWNER TO postgres;

--
-- TOC entry 2542 (class 2617 OID 81152)
-- Dependencies: 414 7 1420
-- Name: !~*; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR !~* (
    PROCEDURE = texticregexne,
    LEFTARG = citext,
    RIGHTARG = text,
    NEGATOR = ~*,
    RESTRICT = icregexnesel,
    JOIN = icregexnejoinsel
);


ALTER OPERATOR public.!~* (citext, text) OWNER TO postgres;

--
-- TOC entry 2543 (class 2617 OID 81154)
-- Dependencies: 1420 409 1420 7
-- Name: !~~; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR !~~ (
    PROCEDURE = texticnlike,
    LEFTARG = citext,
    RIGHTARG = citext,
    NEGATOR = ~~,
    RESTRICT = icnlikesel,
    JOIN = icnlikejoinsel
);


ALTER OPERATOR public.!~~ (citext, citext) OWNER TO postgres;

--
-- TOC entry 2544 (class 2617 OID 81156)
-- Dependencies: 410 7 1420
-- Name: !~~; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR !~~ (
    PROCEDURE = texticnlike,
    LEFTARG = citext,
    RIGHTARG = text,
    NEGATOR = ~~,
    RESTRICT = icnlikesel,
    JOIN = icnlikejoinsel
);


ALTER OPERATOR public.!~~ (citext, text) OWNER TO postgres;

--
-- TOC entry 2545 (class 2617 OID 81158)
-- Dependencies: 409 1420 1420 7
-- Name: !~~*; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR !~~* (
    PROCEDURE = texticnlike,
    LEFTARG = citext,
    RIGHTARG = citext,
    NEGATOR = ~~*,
    RESTRICT = icnlikesel,
    JOIN = icnlikejoinsel
);


ALTER OPERATOR public.!~~* (citext, citext) OWNER TO postgres;

--
-- TOC entry 2546 (class 2617 OID 81160)
-- Dependencies: 410 7 1420
-- Name: !~~*; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR !~~* (
    PROCEDURE = texticnlike,
    LEFTARG = citext,
    RIGHTARG = text,
    NEGATOR = ~~*,
    RESTRICT = icnlikesel,
    JOIN = icnlikejoinsel
);


ALTER OPERATOR public.!~~* (citext, text) OWNER TO postgres;

--
-- TOC entry 2547 (class 2617 OID 81139)
-- Dependencies: 7 1420 1420 332
-- Name: <=; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR <= (
    PROCEDURE = citext_le,
    LEFTARG = citext,
    RIGHTARG = citext,
    COMMUTATOR = >=,
    NEGATOR = >,
    RESTRICT = scalarltsel,
    JOIN = scalarltjoinsel
);


ALTER OPERATOR public.<= (citext, citext) OWNER TO postgres;

--
-- TOC entry 2548 (class 2617 OID 81162)
-- Dependencies: 1420 7 334 1420
-- Name: <>; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR <> (
    PROCEDURE = citext_ne,
    LEFTARG = citext,
    RIGHTARG = citext,
    COMMUTATOR = <>,
    NEGATOR = =,
    RESTRICT = neqsel,
    JOIN = neqjoinsel
);


ALTER OPERATOR public.<> (citext, citext) OWNER TO postgres;

--
-- TOC entry 2549 (class 2617 OID 81161)
-- Dependencies: 327 1420 7 1420
-- Name: =; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR = (
    PROCEDURE = citext_eq,
    LEFTARG = citext,
    RIGHTARG = citext,
    COMMUTATOR = =,
    NEGATOR = <>,
    MERGES,
    HASHES,
    RESTRICT = eqsel,
    JOIN = eqjoinsel
);


ALTER OPERATOR public.= (citext, citext) OWNER TO postgres;

--
-- TOC entry 2550 (class 2617 OID 81142)
-- Dependencies: 7 328 1420 1420
-- Name: >=; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR >= (
    PROCEDURE = citext_ge,
    LEFTARG = citext,
    RIGHTARG = citext,
    COMMUTATOR = <=,
    NEGATOR = <,
    RESTRICT = scalargtsel,
    JOIN = scalargtjoinsel
);


ALTER OPERATOR public.>= (citext, citext) OWNER TO postgres;

--
-- TOC entry 2551 (class 2617 OID 81145)
-- Dependencies: 411 7 1420 1420
-- Name: ~; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR ~ (
    PROCEDURE = texticregexeq,
    LEFTARG = citext,
    RIGHTARG = citext,
    NEGATOR = !~,
    RESTRICT = icregexeqsel,
    JOIN = icregexeqjoinsel
);


ALTER OPERATOR public.~ (citext, citext) OWNER TO postgres;

--
-- TOC entry 2552 (class 2617 OID 81147)
-- Dependencies: 1420 412 7
-- Name: ~; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR ~ (
    PROCEDURE = texticregexeq,
    LEFTARG = citext,
    RIGHTARG = text,
    NEGATOR = !~,
    RESTRICT = icregexeqsel,
    JOIN = icregexeqjoinsel
);


ALTER OPERATOR public.~ (citext, text) OWNER TO postgres;

--
-- TOC entry 2553 (class 2617 OID 81149)
-- Dependencies: 7 1420 1420 411
-- Name: ~*; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR ~* (
    PROCEDURE = texticregexeq,
    LEFTARG = citext,
    RIGHTARG = citext,
    NEGATOR = !~*,
    RESTRICT = icregexeqsel,
    JOIN = icregexeqjoinsel
);


ALTER OPERATOR public.~* (citext, citext) OWNER TO postgres;

--
-- TOC entry 2554 (class 2617 OID 81151)
-- Dependencies: 412 1420 7
-- Name: ~*; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR ~* (
    PROCEDURE = texticregexeq,
    LEFTARG = citext,
    RIGHTARG = text,
    NEGATOR = !~*,
    RESTRICT = icregexeqsel,
    JOIN = icregexeqjoinsel
);


ALTER OPERATOR public.~* (citext, text) OWNER TO postgres;

--
-- TOC entry 2555 (class 2617 OID 81153)
-- Dependencies: 7 407 1420 1420
-- Name: ~~; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR ~~ (
    PROCEDURE = texticlike,
    LEFTARG = citext,
    RIGHTARG = citext,
    NEGATOR = !~~,
    RESTRICT = iclikesel,
    JOIN = iclikejoinsel
);


ALTER OPERATOR public.~~ (citext, citext) OWNER TO postgres;

--
-- TOC entry 2556 (class 2617 OID 81155)
-- Dependencies: 7 408 1420
-- Name: ~~; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR ~~ (
    PROCEDURE = texticlike,
    LEFTARG = citext,
    RIGHTARG = text,
    NEGATOR = !~~,
    RESTRICT = iclikesel,
    JOIN = iclikejoinsel
);


ALTER OPERATOR public.~~ (citext, text) OWNER TO postgres;

--
-- TOC entry 2557 (class 2617 OID 81157)
-- Dependencies: 1420 7 407 1420
-- Name: ~~*; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR ~~* (
    PROCEDURE = texticlike,
    LEFTARG = citext,
    RIGHTARG = citext,
    NEGATOR = !~~*,
    RESTRICT = iclikesel,
    JOIN = iclikejoinsel
);


ALTER OPERATOR public.~~* (citext, citext) OWNER TO postgres;

--
-- TOC entry 2558 (class 2617 OID 81159)
-- Dependencies: 408 7 1420
-- Name: ~~*; Type: OPERATOR; Schema: public; Owner: postgres
--

CREATE OPERATOR ~~* (
    PROCEDURE = texticlike,
    LEFTARG = citext,
    RIGHTARG = text,
    NEGATOR = !~~*,
    RESTRICT = iclikesel,
    JOIN = iclikejoinsel
);


ALTER OPERATOR public.~~* (citext, text) OWNER TO postgres;

--
-- TOC entry 2788 (class 2753 OID 81163)
-- Dependencies: 7
-- Name: citext_ops; Type: OPERATOR FAMILY; Schema: public; Owner: postgres
--

CREATE OPERATOR FAMILY citext_ops USING btree;


ALTER OPERATOR FAMILY public.citext_ops USING btree OWNER TO postgres;

--
-- TOC entry 2671 (class 2616 OID 81164)
-- Dependencies: 1420 7 2788
-- Name: citext_ops; Type: OPERATOR CLASS; Schema: public; Owner: postgres
--

CREATE OPERATOR CLASS citext_ops
    DEFAULT FOR TYPE citext USING btree AS
    OPERATOR 1 <(citext,citext) ,
    OPERATOR 2 <=(citext,citext) ,
    OPERATOR 3 =(citext,citext) ,
    OPERATOR 4 >=(citext,citext) ,
    OPERATOR 5 >(citext,citext) ,
    FUNCTION 1 citext_cmp(citext,citext);


ALTER OPERATOR CLASS public.citext_ops USING btree OWNER TO postgres;

--
-- TOC entry 2789 (class 2753 OID 81171)
-- Dependencies: 7
-- Name: citext_ops; Type: OPERATOR FAMILY; Schema: public; Owner: postgres
--

CREATE OPERATOR FAMILY citext_ops USING hash;


ALTER OPERATOR FAMILY public.citext_ops USING hash OWNER TO postgres;

--
-- TOC entry 2672 (class 2616 OID 81172)
-- Dependencies: 1420 7 2789
-- Name: citext_ops; Type: OPERATOR CLASS; Schema: public; Owner: postgres
--

CREATE OPERATOR CLASS citext_ops
    DEFAULT FOR TYPE citext USING hash AS
    OPERATOR 1 =(citext,citext) ,
    FUNCTION 1 citext_hash(citext);


ALTER OPERATOR CLASS public.citext_ops USING hash OWNER TO postgres;

SET search_path = pg_catalog;

--
-- TOC entry 3029 (class 2605 OID 81175)
-- Dependencies: 324 324 1420
-- Name: CAST (boolean AS public.citext); Type: CAST; Schema: pg_catalog; Owner: 
--

CREATE CAST (boolean AS public.citext) WITH FUNCTION public.citext(boolean) AS ASSIGNMENT;


--
-- TOC entry 3155 (class 2605 OID 81176)
-- Dependencies: 323 323 1420
-- Name: CAST (character AS public.citext); Type: CAST; Schema: pg_catalog; Owner: 
--

CREATE CAST (character AS public.citext) WITH FUNCTION public.citext(character) AS ASSIGNMENT;


--
-- TOC entry 3222 (class 2605 OID 81177)
-- Dependencies: 1420
-- Name: CAST (public.citext AS character); Type: CAST; Schema: pg_catalog; Owner: 
--

CREATE CAST (public.citext AS character) WITHOUT FUNCTION AS ASSIGNMENT;


--
-- TOC entry 3221 (class 2605 OID 81178)
-- Dependencies: 1420
-- Name: CAST (public.citext AS text); Type: CAST; Schema: pg_catalog; Owner: 
--

CREATE CAST (public.citext AS text) WITHOUT FUNCTION AS IMPLICIT;


--
-- TOC entry 3223 (class 2605 OID 81179)
-- Dependencies: 1420
-- Name: CAST (public.citext AS character varying); Type: CAST; Schema: pg_catalog; Owner: 
--

CREATE CAST (public.citext AS character varying) WITHOUT FUNCTION AS IMPLICIT;


--
-- TOC entry 3148 (class 2605 OID 81180)
-- Dependencies: 325 1420 325
-- Name: CAST (inet AS public.citext); Type: CAST; Schema: pg_catalog; Owner: 
--

CREATE CAST (inet AS public.citext) WITH FUNCTION public.citext(inet) AS ASSIGNMENT;


--
-- TOC entry 3095 (class 2605 OID 81181)
-- Dependencies: 1420
-- Name: CAST (text AS public.citext); Type: CAST; Schema: pg_catalog; Owner: 
--

CREATE CAST (text AS public.citext) WITHOUT FUNCTION AS ASSIGNMENT;


--
-- TOC entry 3163 (class 2605 OID 81182)
-- Dependencies: 1420
-- Name: CAST (character varying AS public.citext); Type: CAST; Schema: pg_catalog; Owner: 
--

CREATE CAST (character varying AS public.citext) WITHOUT FUNCTION AS ASSIGNMENT;


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 152 (class 1259 OID 81213)
-- Dependencies: 7
-- Name: activity_snapshot; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE activity_snapshot (
    datid oid,
    datname name,
    procpid integer,
    usesysid oid,
    usename name,
    application_name text,
    client_addr inet,
    client_port integer,
    backend_start timestamp with time zone,
    xact_start timestamp with time zone,
    query_start timestamp with time zone,
    waiting boolean,
    current_query text
);


ALTER TABLE public.activity_snapshot OWNER TO postgres;

--
-- TOC entry 153 (class 1259 OID 81219)
-- Dependencies: 1420 7
-- Name: addresses; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE addresses (
    address_id integer NOT NULL,
    address citext NOT NULL,
    first_seen timestamp with time zone
);


ALTER TABLE public.addresses OWNER TO breakpad_rw;

--
-- TOC entry 154 (class 1259 OID 81225)
-- Dependencies: 7 153
-- Name: addresses_address_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE addresses_address_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.addresses_address_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3568 (class 0 OID 0)
-- Dependencies: 154
-- Name: addresses_address_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE addresses_address_id_seq OWNED BY addresses.address_id;


--
-- TOC entry 155 (class 1259 OID 81235)
-- Dependencies: 3008 7
-- Name: bloat; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW bloat AS
    SELECT sml.schemaname, sml.tablename, (sml.reltuples)::bigint AS reltuples, (sml.relpages)::bigint AS relpages, sml.otta, round(CASE WHEN (sml.otta = (0)::double precision) THEN 0.0 ELSE ((sml.relpages)::numeric / (sml.otta)::numeric) END, 1) AS tbloat, (((sml.relpages)::bigint)::double precision - sml.otta) AS wastedpages, (sml.bs * ((((sml.relpages)::double precision - sml.otta))::bigint)::numeric) AS wastedbytes, pg_size_pretty((((sml.bs)::double precision * ((sml.relpages)::double precision - sml.otta)))::bigint) AS wastedsize, sml.iname, (sml.ituples)::bigint AS ituples, (sml.ipages)::bigint AS ipages, sml.iotta, round(CASE WHEN ((sml.iotta = (0)::double precision) OR (sml.ipages = 0)) THEN 0.0 ELSE ((sml.ipages)::numeric / (sml.iotta)::numeric) END, 1) AS ibloat, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN (0)::double precision ELSE (((sml.ipages)::bigint)::double precision - sml.iotta) END AS wastedipages, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN (0)::double precision ELSE ((sml.bs)::double precision * ((sml.ipages)::double precision - sml.iotta)) END AS wastedibytes, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN pg_size_pretty((0)::bigint) ELSE pg_size_pretty((((sml.bs)::double precision * ((sml.ipages)::double precision - sml.iotta)))::bigint) END AS wastedisize FROM (SELECT rs.schemaname, rs.tablename, cc.reltuples, cc.relpages, rs.bs, ceil(((cc.reltuples * (((((rs.datahdr + (rs.ma)::numeric) - CASE WHEN ((rs.datahdr % (rs.ma)::numeric) = (0)::numeric) THEN (rs.ma)::numeric ELSE (rs.datahdr % (rs.ma)::numeric) END))::double precision + rs.nullhdr2) + (4)::double precision)) / ((rs.bs)::double precision - (20)::double precision))) AS otta, COALESCE(c2.relname, '?'::name) AS iname, COALESCE(c2.reltuples, (0)::real) AS ituples, COALESCE(c2.relpages, 0) AS ipages, COALESCE(ceil(((c2.reltuples * ((rs.datahdr - (12)::numeric))::double precision) / ((rs.bs)::double precision - (20)::double precision))), (0)::double precision) AS iotta FROM (((((SELECT foo.ma, foo.bs, foo.schemaname, foo.tablename, ((foo.datawidth + (((foo.hdr + foo.ma) - CASE WHEN ((foo.hdr % foo.ma) = 0) THEN foo.ma ELSE (foo.hdr % foo.ma) END))::double precision))::numeric AS datahdr, (foo.maxfracsum * (((foo.nullhdr + foo.ma) - CASE WHEN ((foo.nullhdr % (foo.ma)::bigint) = 0) THEN (foo.ma)::bigint ELSE (foo.nullhdr % (foo.ma)::bigint) END))::double precision) AS nullhdr2 FROM (SELECT s.schemaname, s.tablename, constants.hdr, constants.ma, constants.bs, sum((((1)::double precision - s.null_frac) * (s.avg_width)::double precision)) AS datawidth, max(s.null_frac) AS maxfracsum, (constants.hdr + (SELECT (1 + (count(*) / 8)) FROM pg_stats s2 WHERE (((s2.null_frac <> (0)::double precision) AND (s2.schemaname = s.schemaname)) AND (s2.tablename = s.tablename)))) AS nullhdr FROM pg_stats s, (SELECT (SELECT (current_setting('block_size'::text))::numeric AS current_setting) AS bs, CASE WHEN ("substring"(foo.v, 12, 3) = ANY (ARRAY['8.0'::text, '8.1'::text, '8.2'::text])) THEN 27 ELSE 23 END AS hdr, CASE WHEN (foo.v ~ 'mingw32'::text) THEN 8 ELSE 4 END AS ma FROM (SELECT version() AS v) foo) constants GROUP BY s.schemaname, s.tablename, constants.hdr, constants.ma, constants.bs) foo) rs JOIN pg_class cc ON ((cc.relname = rs.tablename))) JOIN pg_namespace nn ON (((cc.relnamespace = nn.oid) AND (nn.nspname = rs.schemaname)))) LEFT JOIN pg_index i ON ((i.indrelid = cc.oid))) LEFT JOIN pg_class c2 ON ((c2.oid = i.indexrelid)))) sml WHERE ((((sml.relpages)::double precision - sml.otta) > (0)::double precision) OR (((sml.ipages)::double precision - sml.iotta) > (10)::double precision)) ORDER BY (sml.bs * ((((sml.relpages)::double precision - sml.otta))::bigint)::numeric) DESC, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN (0)::double precision ELSE ((sml.bs)::double precision * ((sml.ipages)::double precision - sml.iotta)) END DESC;


ALTER TABLE public.bloat OWNER TO postgres;

--
-- TOC entry 158 (class 1259 OID 81262)
-- Dependencies: 7
-- Name: bug_associations; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE bug_associations (
    signature text NOT NULL,
    bug_id integer NOT NULL
);


ALTER TABLE public.bug_associations OWNER TO breakpad_rw;

--
-- TOC entry 159 (class 1259 OID 81268)
-- Dependencies: 7
-- Name: bugs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE bugs (
    id integer NOT NULL,
    status text,
    resolution text,
    short_desc text
);


ALTER TABLE public.bugs OWNER TO breakpad_rw;

--
-- TOC entry 252 (class 1259 OID 84545)
-- Dependencies: 1420 7
-- Name: build_adu; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE build_adu (
    product_version_id integer NOT NULL,
    build_date date NOT NULL,
    adu_date date NOT NULL,
    os_name citext NOT NULL,
    adu_count integer NOT NULL
);


ALTER TABLE public.build_adu OWNER TO breakpad_rw;

--
-- TOC entry 160 (class 1259 OID 81281)
-- Dependencies: 3231 7
-- Name: correlation_addons; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE correlation_addons (
    correlation_id integer NOT NULL,
    addon_key text NOT NULL,
    addon_version text NOT NULL,
    crash_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.correlation_addons OWNER TO breakpad_rw;

--
-- TOC entry 161 (class 1259 OID 81288)
-- Dependencies: 3232 7 1420
-- Name: correlation_cores; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE correlation_cores (
    correlation_id integer NOT NULL,
    architecture citext NOT NULL,
    cores integer NOT NULL,
    crash_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.correlation_cores OWNER TO breakpad_rw;

--
-- TOC entry 162 (class 1259 OID 81295)
-- Dependencies: 3233 7
-- Name: correlation_modules; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE correlation_modules (
    correlation_id integer NOT NULL,
    module_signature text NOT NULL,
    module_version text NOT NULL,
    crash_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.correlation_modules OWNER TO breakpad_rw;

--
-- TOC entry 163 (class 1259 OID 81302)
-- Dependencies: 3234 1420 7
-- Name: correlations; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE correlations (
    correlation_id integer NOT NULL,
    product_version_id integer NOT NULL,
    os_name citext NOT NULL,
    reason_id integer NOT NULL,
    signature_id integer NOT NULL,
    crash_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.correlations OWNER TO breakpad_rw;

--
-- TOC entry 164 (class 1259 OID 81309)
-- Dependencies: 7 163
-- Name: correlations_correlation_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE correlations_correlation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
    CYCLE;


ALTER TABLE public.correlations_correlation_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3576 (class 0 OID 0)
-- Dependencies: 164
-- Name: correlations_correlation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE correlations_correlation_id_seq OWNED BY correlations.correlation_id;


--
-- TOC entry 254 (class 1259 OID 84557)
-- Dependencies: 3290 1420 7 1420 1420
-- Name: crash_types; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE crash_types (
    crash_type_id integer NOT NULL,
    crash_type citext NOT NULL,
    crash_type_short citext NOT NULL,
    process_type citext NOT NULL,
    has_hang_id boolean,
    old_code character(1) NOT NULL,
    include_agg boolean DEFAULT true NOT NULL
);


ALTER TABLE public.crash_types OWNER TO breakpad_rw;

--
-- TOC entry 253 (class 1259 OID 84555)
-- Dependencies: 254 7
-- Name: crash_types_crash_type_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE crash_types_crash_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.crash_types_crash_type_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3577 (class 0 OID 0)
-- Dependencies: 253
-- Name: crash_types_crash_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE crash_types_crash_type_id_seq OWNED BY crash_types.crash_type_id;


--
-- TOC entry 255 (class 1259 OID 84576)
-- Dependencies: 1420 7
-- Name: crashes_by_user; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE crashes_by_user (
    product_version_id integer NOT NULL,
    os_short_name citext NOT NULL,
    crash_type_id integer NOT NULL,
    report_date date NOT NULL,
    report_count integer NOT NULL,
    adu integer NOT NULL
);


ALTER TABLE public.crashes_by_user OWNER TO breakpad_rw;

--
-- TOC entry 257 (class 1259 OID 84596)
-- Dependencies: 1420 7
-- Name: crashes_by_user_build; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE crashes_by_user_build (
    product_version_id integer NOT NULL,
    os_short_name citext NOT NULL,
    crash_type_id integer NOT NULL,
    build_date date NOT NULL,
    report_date date NOT NULL,
    report_count integer NOT NULL,
    adu integer NOT NULL
);


ALTER TABLE public.crashes_by_user_build OWNER TO breakpad_rw;

--
-- TOC entry 193 (class 1259 OID 81497)
-- Dependencies: 7 1420 1420
-- Name: os_names; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE os_names (
    os_name citext NOT NULL,
    os_short_name citext NOT NULL
);


ALTER TABLE public.os_names OWNER TO breakpad_rw;

--
-- TOC entry 167 (class 1259 OID 81336)
-- Dependencies: 3236 1420 7 1420
-- Name: product_release_channels; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE product_release_channels (
    product_name citext NOT NULL,
    release_channel citext NOT NULL,
    throttle numeric DEFAULT 1.0 NOT NULL
);


ALTER TABLE public.product_release_channels OWNER TO breakpad_rw;

--
-- TOC entry 156 (class 1259 OID 81240)
-- Dependencies: 3225 3226 3227 3228 3229 7 1420 1420 1420 1420 1424
-- Name: product_versions; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE product_versions (
    product_version_id integer NOT NULL,
    product_name citext NOT NULL,
    major_version major_version NOT NULL,
    release_version citext NOT NULL,
    version_string citext NOT NULL,
    beta_number integer,
    version_sort text DEFAULT 0 NOT NULL,
    build_date date NOT NULL,
    sunset_date date NOT NULL,
    featured_version boolean DEFAULT false NOT NULL,
    build_type citext DEFAULT 'release'::citext NOT NULL,
    has_builds boolean DEFAULT false,
    is_rapid_beta boolean DEFAULT false,
    rapid_beta_id integer
);


ALTER TABLE public.product_versions OWNER TO breakpad_rw;

--
-- TOC entry 258 (class 1259 OID 84609)
-- Dependencies: 3018 1420 7 1420 1420 1420 1420 1420
-- Name: crashes_by_user_build_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW crashes_by_user_build_view AS
    SELECT crashes_by_user_build.product_version_id, product_versions.product_name, product_versions.version_string, crashes_by_user_build.os_short_name, os_names.os_name, crash_types.crash_type, crash_types.crash_type_short, crashes_by_user_build.build_date, sum(crashes_by_user_build.report_count) AS report_count, sum(((crashes_by_user_build.report_count)::numeric / product_release_channels.throttle)) AS adjusted_report_count, sum(crashes_by_user_build.adu) AS adu, product_release_channels.throttle FROM ((((crashes_by_user_build JOIN product_versions USING (product_version_id)) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) JOIN os_names USING (os_short_name)) JOIN crash_types USING (crash_type_id)) GROUP BY crashes_by_user_build.product_version_id, product_versions.product_name, product_versions.version_string, crashes_by_user_build.os_short_name, os_names.os_name, crash_types.crash_type, crash_types.crash_type_short, crashes_by_user_build.build_date, product_release_channels.throttle;


ALTER TABLE public.crashes_by_user_build_view OWNER TO postgres;

--
-- TOC entry 256 (class 1259 OID 84589)
-- Dependencies: 3017 1420 1420 1420 1420 1420 1420 7
-- Name: crashes_by_user_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW crashes_by_user_view AS
    SELECT crashes_by_user.product_version_id, product_versions.product_name, product_versions.version_string, crashes_by_user.os_short_name, os_names.os_name, crash_types.crash_type, crash_types.crash_type_short, crashes_by_user.report_date, crashes_by_user.report_count, ((crashes_by_user.report_count)::numeric / product_release_channels.throttle) AS adjusted_report_count, crashes_by_user.adu, product_release_channels.throttle FROM ((((crashes_by_user JOIN product_versions USING (product_version_id)) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) JOIN os_names USING (os_short_name)) JOIN crash_types USING (crash_type_id));


ALTER TABLE public.crashes_by_user_view OWNER TO postgres;

--
-- TOC entry 165 (class 1259 OID 81311)
-- Dependencies: 7
-- Name: crontabber_state; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE crontabber_state (
    state text NOT NULL,
    last_updated timestamp with time zone NOT NULL
);


ALTER TABLE public.crontabber_state OWNER TO breakpad_rw;

--
-- TOC entry 166 (class 1259 OID 81330)
-- Dependencies: 7 1420
-- Name: daily_hangs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE daily_hangs (
    uuid text NOT NULL,
    plugin_uuid text NOT NULL,
    report_date date,
    product_version_id integer NOT NULL,
    browser_signature_id integer NOT NULL,
    plugin_signature_id integer NOT NULL,
    hang_id text NOT NULL,
    flash_version_id integer,
    url citext,
    duplicates text[]
);


ALTER TABLE public.daily_hangs OWNER TO breakpad_rw;

--
-- TOC entry 168 (class 1259 OID 81349)
-- Dependencies: 3237 1420 7 1420 1424 1424
-- Name: products; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE products (
    product_name citext NOT NULL,
    sort smallint DEFAULT 0 NOT NULL,
    rapid_release_version major_version,
    release_name citext NOT NULL,
    rapid_beta_version major_version
);


ALTER TABLE public.products OWNER TO breakpad_rw;

--
-- TOC entry 169 (class 1259 OID 81362)
-- Dependencies: 3238 1420 7
-- Name: release_channels; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE release_channels (
    release_channel citext NOT NULL,
    sort smallint DEFAULT 0 NOT NULL
);


ALTER TABLE public.release_channels OWNER TO breakpad_rw;

--
-- TOC entry 249 (class 1259 OID 84530)
-- Dependencies: 3014 7 1420 1420 1420
-- Name: product_info; Type: VIEW; Schema: public; Owner: breakpad_rw
--

CREATE VIEW product_info AS
    SELECT product_versions.product_version_id, product_versions.product_name, product_versions.version_string, 'new'::text AS which_table, product_versions.build_date AS start_date, product_versions.sunset_date AS end_date, product_versions.featured_version AS is_featured, product_versions.build_type, ((product_release_channels.throttle * (100)::numeric))::numeric(5,2) AS throttle, product_versions.version_sort, products.sort AS product_sort, release_channels.sort AS channel_sort, product_versions.has_builds, product_versions.is_rapid_beta FROM (((product_versions JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) JOIN products ON ((product_versions.product_name = products.product_name))) JOIN release_channels ON ((product_versions.build_type = release_channels.release_channel))) ORDER BY product_versions.product_name, product_versions.version_string;


ALTER TABLE public.product_info OWNER TO breakpad_rw;

--
-- TOC entry 250 (class 1259 OID 84535)
-- Dependencies: 3015 7 1420 1420
-- Name: default_versions; Type: VIEW; Schema: public; Owner: breakpad_rw
--

CREATE VIEW default_versions AS
    SELECT count_versions.product_name, count_versions.version_string, count_versions.product_version_id FROM (SELECT product_info.product_name, product_info.version_string, product_info.product_version_id, row_number() OVER (PARTITION BY product_info.product_name ORDER BY ((('now'::text)::date >= product_info.start_date) AND (('now'::text)::date <= product_info.end_date)) DESC, product_info.is_featured DESC, product_info.channel_sort DESC) AS sort_count FROM product_info) count_versions WHERE (count_versions.sort_count = 1);


ALTER TABLE public.default_versions OWNER TO breakpad_rw;

--
-- TOC entry 251 (class 1259 OID 84539)
-- Dependencies: 3016 1420 1420 7
-- Name: default_versions_builds; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW default_versions_builds AS
    SELECT count_versions.product_name, count_versions.version_string, count_versions.product_version_id FROM (SELECT product_info.product_name, product_info.version_string, product_info.product_version_id, row_number() OVER (PARTITION BY product_info.product_name ORDER BY ((('now'::text)::date >= product_info.start_date) AND (('now'::text)::date <= product_info.end_date)) DESC, product_info.is_featured DESC, product_info.channel_sort DESC) AS sort_count FROM product_info WHERE product_info.has_builds) count_versions WHERE (count_versions.sort_count = 1);


ALTER TABLE public.default_versions_builds OWNER TO postgres;

--
-- TOC entry 170 (class 1259 OID 81378)
-- Dependencies: 7 1420
-- Name: domains; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE domains (
    domain_id integer NOT NULL,
    domain citext NOT NULL,
    first_seen timestamp with time zone
);


ALTER TABLE public.domains OWNER TO breakpad_rw;

--
-- TOC entry 171 (class 1259 OID 81384)
-- Dependencies: 170 7
-- Name: domains_domain_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE domains_domain_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.domains_domain_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3586 (class 0 OID 0)
-- Dependencies: 171
-- Name: domains_domain_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE domains_domain_id_seq OWNED BY domains.domain_id;


--
-- TOC entry 172 (class 1259 OID 81386)
-- Dependencies: 3240 3241 3242 7
-- Name: email_campaigns; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE email_campaigns (
    id integer NOT NULL,
    product text NOT NULL,
    versions text NOT NULL,
    signature text NOT NULL,
    subject text NOT NULL,
    body text NOT NULL,
    start_date timestamp with time zone NOT NULL,
    end_date timestamp with time zone NOT NULL,
    email_count integer DEFAULT 0,
    author text NOT NULL,
    date_created timestamp with time zone DEFAULT now() NOT NULL,
    status text DEFAULT 'stopped'::text NOT NULL
);


ALTER TABLE public.email_campaigns OWNER TO breakpad_rw;

--
-- TOC entry 173 (class 1259 OID 81395)
-- Dependencies: 3244 7
-- Name: email_campaigns_contacts; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE email_campaigns_contacts (
    email_campaigns_id integer,
    email_contacts_id integer,
    status text DEFAULT 'stopped'::text NOT NULL
);


ALTER TABLE public.email_campaigns_contacts OWNER TO breakpad_rw;

--
-- TOC entry 174 (class 1259 OID 81402)
-- Dependencies: 172 7
-- Name: email_campaigns_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE email_campaigns_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.email_campaigns_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3589 (class 0 OID 0)
-- Dependencies: 174
-- Name: email_campaigns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE email_campaigns_id_seq OWNED BY email_campaigns.id;


--
-- TOC entry 175 (class 1259 OID 81404)
-- Dependencies: 3245 7
-- Name: email_contacts; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE email_contacts (
    id integer NOT NULL,
    email text NOT NULL,
    subscribe_token text NOT NULL,
    subscribe_status boolean DEFAULT true,
    ooid text,
    crash_date timestamp with time zone
);


ALTER TABLE public.email_contacts OWNER TO breakpad_rw;

--
-- TOC entry 176 (class 1259 OID 81411)
-- Dependencies: 175 7
-- Name: email_contacts_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE email_contacts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.email_contacts_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3592 (class 0 OID 0)
-- Dependencies: 176
-- Name: email_contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE email_contacts_id_seq OWNED BY email_contacts.id;


--
-- TOC entry 177 (class 1259 OID 81413)
-- Dependencies: 7
-- Name: explosiveness; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE explosiveness (
    product_version_id integer NOT NULL,
    signature_id integer NOT NULL,
    last_date date NOT NULL,
    oneday numeric,
    threeday numeric,
    day0 numeric,
    day1 numeric,
    day2 numeric,
    day3 numeric,
    day4 numeric,
    day5 numeric,
    day6 numeric,
    day7 numeric,
    day8 numeric,
    day9 numeric
);


ALTER TABLE public.explosiveness OWNER TO breakpad_rw;

--
-- TOC entry 178 (class 1259 OID 81419)
-- Dependencies: 7
-- Name: extensions; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE extensions (
    report_id integer NOT NULL,
    date_processed timestamp with time zone,
    extension_key integer NOT NULL,
    extension_id text NOT NULL,
    extension_version text
);


ALTER TABLE public.extensions OWNER TO breakpad_rw;

--
-- TOC entry 179 (class 1259 OID 81425)
-- Dependencies: 1420 7
-- Name: flash_versions; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE flash_versions (
    flash_version_id integer NOT NULL,
    flash_version citext NOT NULL,
    first_seen timestamp with time zone
);


ALTER TABLE public.flash_versions OWNER TO breakpad_rw;

--
-- TOC entry 180 (class 1259 OID 81431)
-- Dependencies: 7 179
-- Name: flash_versions_flash_version_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE flash_versions_flash_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.flash_versions_flash_version_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3597 (class 0 OID 0)
-- Dependencies: 180
-- Name: flash_versions_flash_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE flash_versions_flash_version_id_seq OWNED BY flash_versions.flash_version_id;


--
-- TOC entry 181 (class 1259 OID 81433)
-- Dependencies: 7
-- Name: signatures; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE signatures (
    signature_id integer NOT NULL,
    signature text,
    first_report timestamp with time zone,
    first_build numeric
);


ALTER TABLE public.signatures OWNER TO breakpad_rw;

--
-- TOC entry 182 (class 1259 OID 81439)
-- Dependencies: 3009 1420 7 1420 1420 1420
-- Name: hang_report; Type: VIEW; Schema: public; Owner: breakpad_rw
--

CREATE VIEW hang_report AS
    SELECT product_versions.product_name AS product, product_versions.version_string AS version, browser_signatures.signature AS browser_signature, plugin_signatures.signature AS plugin_signature, daily_hangs.hang_id AS browser_hangid, flash_versions.flash_version, daily_hangs.url, daily_hangs.uuid, daily_hangs.duplicates, daily_hangs.report_date AS report_day FROM ((((daily_hangs JOIN product_versions USING (product_version_id)) JOIN signatures browser_signatures ON ((daily_hangs.browser_signature_id = browser_signatures.signature_id))) JOIN signatures plugin_signatures ON ((daily_hangs.plugin_signature_id = plugin_signatures.signature_id))) LEFT JOIN flash_versions USING (flash_version_id));


ALTER TABLE public.hang_report OWNER TO breakpad_rw;

--
-- TOC entry 183 (class 1259 OID 81444)
-- Dependencies: 7
-- Name: high_load_temp; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE high_load_temp (
    now timestamp with time zone,
    datid oid,
    datname name,
    procpid integer,
    usesysid oid,
    usename name,
    application_name text,
    client_addr inet,
    client_port integer,
    backend_start timestamp with time zone,
    xact_start timestamp with time zone,
    query_start timestamp with time zone,
    waiting boolean,
    current_query text
);


ALTER TABLE public.high_load_temp OWNER TO postgres;

--
-- TOC entry 259 (class 1259 OID 84616)
-- Dependencies: 3291 3292 3293 7
-- Name: home_page_graph; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE home_page_graph (
    product_version_id integer NOT NULL,
    report_date date NOT NULL,
    report_count integer DEFAULT 0 NOT NULL,
    adu integer DEFAULT 0 NOT NULL,
    crash_hadu numeric DEFAULT 0.0 NOT NULL
);


ALTER TABLE public.home_page_graph OWNER TO breakpad_rw;

--
-- TOC entry 261 (class 1259 OID 84633)
-- Dependencies: 3294 3295 7
-- Name: home_page_graph_build; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE home_page_graph_build (
    product_version_id integer NOT NULL,
    report_date date NOT NULL,
    build_date date NOT NULL,
    report_count integer DEFAULT 0 NOT NULL,
    adu integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.home_page_graph_build OWNER TO breakpad_rw;

--
-- TOC entry 262 (class 1259 OID 84640)
-- Dependencies: 3020 1420 7 1420
-- Name: home_page_graph_build_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW home_page_graph_build_view AS
    SELECT home_page_graph_build.product_version_id, product_versions.product_name, product_versions.version_string, home_page_graph_build.build_date, sum(home_page_graph_build.report_count) AS report_count, sum(home_page_graph_build.adu) AS adu, crash_hadu(sum(home_page_graph_build.report_count), sum(home_page_graph_build.adu), product_release_channels.throttle) AS crash_hadu FROM ((home_page_graph_build JOIN product_versions USING (product_version_id)) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) GROUP BY home_page_graph_build.product_version_id, product_versions.product_name, product_versions.version_string, home_page_graph_build.build_date, product_release_channels.throttle;


ALTER TABLE public.home_page_graph_build_view OWNER TO postgres;

--
-- TOC entry 260 (class 1259 OID 84627)
-- Dependencies: 3019 1420 7 1420
-- Name: home_page_graph_view; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW home_page_graph_view AS
    SELECT home_page_graph.product_version_id, product_versions.product_name, product_versions.version_string, home_page_graph.report_date, home_page_graph.report_count, home_page_graph.adu, home_page_graph.crash_hadu FROM (home_page_graph JOIN product_versions USING (product_version_id));


ALTER TABLE public.home_page_graph_view OWNER TO postgres;

--
-- TOC entry 184 (class 1259 OID 81450)
-- Dependencies: 3249 7
-- Name: jobs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE jobs (
    id integer NOT NULL,
    pathname character varying(1024) NOT NULL,
    uuid character varying(50) NOT NULL,
    owner integer,
    priority integer DEFAULT 0,
    queueddatetime timestamp with time zone,
    starteddatetime timestamp with time zone,
    completeddatetime timestamp with time zone,
    success boolean,
    message text
);


ALTER TABLE public.jobs OWNER TO breakpad_rw;

--
-- TOC entry 185 (class 1259 OID 81457)
-- Dependencies: 184 7
-- Name: jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
    CYCLE;


ALTER TABLE public.jobs_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3602 (class 0 OID 0)
-- Dependencies: 185
-- Name: jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE jobs_id_seq OWNED BY jobs.id;


--
-- TOC entry 186 (class 1259 OID 81459)
-- Dependencies: 3010 7
-- Name: jobs_in_queue; Type: VIEW; Schema: public; Owner: monitoring
--

CREATE VIEW jobs_in_queue AS
    SELECT count(*) AS count FROM jobs WHERE (jobs.completeddatetime IS NULL);


ALTER TABLE public.jobs_in_queue OWNER TO monitoring;

--
-- TOC entry 187 (class 1259 OID 81463)
-- Dependencies: 7
-- Name: locks; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE locks (
    locktype text,
    database oid,
    relation oid,
    page integer,
    tuple smallint,
    virtualxid text,
    transactionid xid,
    classid oid,
    objid oid,
    objsubid smallint,
    virtualtransaction text,
    pid integer,
    mode text,
    granted boolean
);


ALTER TABLE public.locks OWNER TO postgres;

--
-- TOC entry 188 (class 1259 OID 81469)
-- Dependencies: 7
-- Name: locks1; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE locks1 (
    now timestamp with time zone,
    procpid integer,
    query_start timestamp with time zone,
    nspname name,
    relname name,
    mode text,
    granted boolean,
    current_query text
);


ALTER TABLE public.locks1 OWNER TO postgres;

--
-- TOC entry 189 (class 1259 OID 81475)
-- Dependencies: 7
-- Name: locks2; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE locks2 (
    now timestamp with time zone,
    procpid integer,
    query_start timestamp with time zone,
    nspname name,
    relname name,
    mode text,
    granted boolean,
    current_query text
);


ALTER TABLE public.locks2 OWNER TO postgres;

--
-- TOC entry 190 (class 1259 OID 81481)
-- Dependencies: 7
-- Name: locks3; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE locks3 (
    now timestamp with time zone,
    waiting_locktype text,
    waiting_table regclass,
    waiting_query text,
    waiting_mode text,
    waiting_pid integer,
    other_locktype text,
    other_table regclass,
    other_query text,
    other_mode text,
    other_pid integer,
    other_granted boolean
);


ALTER TABLE public.locks3 OWNER TO postgres;

--
-- TOC entry 191 (class 1259 OID 81487)
-- Dependencies: 3251 7
-- Name: nightly_builds; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE nightly_builds (
    product_version_id integer NOT NULL,
    build_date date NOT NULL,
    report_date date NOT NULL,
    days_out integer NOT NULL,
    report_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.nightly_builds OWNER TO breakpad_rw;

--
-- TOC entry 192 (class 1259 OID 81491)
-- Dependencies: 7 1420
-- Name: os_name_matches; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE os_name_matches (
    os_name citext NOT NULL,
    match_string text NOT NULL
);


ALTER TABLE public.os_name_matches OWNER TO breakpad_rw;

--
-- TOC entry 194 (class 1259 OID 81503)
-- Dependencies: 1420 1420 7
-- Name: os_versions; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE os_versions (
    os_version_id integer NOT NULL,
    os_name citext NOT NULL,
    major_version integer NOT NULL,
    minor_version integer NOT NULL,
    os_version_string citext
);


ALTER TABLE public.os_versions OWNER TO breakpad_rw;

--
-- TOC entry 195 (class 1259 OID 81509)
-- Dependencies: 194 7
-- Name: os_versions_os_version_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE os_versions_os_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.os_versions_os_version_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3612 (class 0 OID 0)
-- Dependencies: 195
-- Name: os_versions_os_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE os_versions_os_version_id_seq OWNED BY os_versions.os_version_id;


--
-- TOC entry 196 (class 1259 OID 81516)
-- Dependencies: 3011 7
-- Name: performance_check_1; Type: VIEW; Schema: public; Owner: ganglia
--

CREATE VIEW performance_check_1 AS
    SELECT 1;


ALTER TABLE public.performance_check_1 OWNER TO ganglia;

--
-- TOC entry 197 (class 1259 OID 81520)
-- Dependencies: 3012 7
-- Name: pg_stat_statements; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW pg_stat_statements AS
    SELECT pg_stat_statements.userid, pg_stat_statements.dbid, pg_stat_statements.query, pg_stat_statements.calls, pg_stat_statements.total_time, pg_stat_statements.rows, pg_stat_statements.shared_blks_hit, pg_stat_statements.shared_blks_read, pg_stat_statements.shared_blks_written, pg_stat_statements.local_blks_hit, pg_stat_statements.local_blks_read, pg_stat_statements.local_blks_written, pg_stat_statements.temp_blks_read, pg_stat_statements.temp_blks_written FROM pg_stat_statements() pg_stat_statements(userid, dbid, query, calls, total_time, rows, shared_blks_hit, shared_blks_read, shared_blks_written, local_blks_hit, local_blks_read, local_blks_written, temp_blks_read, temp_blks_written);


ALTER TABLE public.pg_stat_statements OWNER TO postgres;

--
-- TOC entry 198 (class 1259 OID 81524)
-- Dependencies: 7
-- Name: plugins; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE plugins (
    id integer NOT NULL,
    filename text NOT NULL,
    name text NOT NULL
);


ALTER TABLE public.plugins OWNER TO breakpad_rw;

--
-- TOC entry 199 (class 1259 OID 81530)
-- Dependencies: 198 7
-- Name: plugins_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE plugins_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.plugins_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3617 (class 0 OID 0)
-- Dependencies: 199
-- Name: plugins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE plugins_id_seq OWNED BY plugins.id;


--
-- TOC entry 200 (class 1259 OID 81532)
-- Dependencies: 7
-- Name: plugins_reports; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE plugins_reports (
    report_id integer NOT NULL,
    plugin_id integer NOT NULL,
    date_processed timestamp with time zone,
    version text NOT NULL
);


ALTER TABLE public.plugins_reports OWNER TO breakpad_rw;

--
-- TOC entry 201 (class 1259 OID 81538)
-- Dependencies: 7
-- Name: priorityjobs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE priorityjobs (
    uuid character varying(255) NOT NULL
);


ALTER TABLE public.priorityjobs OWNER TO breakpad_rw;

--
-- TOC entry 202 (class 1259 OID 81541)
-- Dependencies: 7
-- Name: priorityjobs_log; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE priorityjobs_log (
    uuid character varying(255)
);


ALTER TABLE public.priorityjobs_log OWNER TO postgres;

--
-- TOC entry 203 (class 1259 OID 81544)
-- Dependencies: 7
-- Name: priorityjobs_logging_switch; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE priorityjobs_logging_switch (
    log_jobs boolean NOT NULL
);


ALTER TABLE public.priorityjobs_logging_switch OWNER TO postgres;

--
-- TOC entry 204 (class 1259 OID 81547)
-- Dependencies: 7 1420
-- Name: process_types; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE process_types (
    process_type citext NOT NULL
);


ALTER TABLE public.process_types OWNER TO breakpad_rw;

--
-- TOC entry 205 (class 1259 OID 81553)
-- Dependencies: 7
-- Name: processors; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE processors (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    startdatetime timestamp without time zone NOT NULL,
    lastseendatetime timestamp without time zone
);


ALTER TABLE public.processors OWNER TO breakpad_rw;

--
-- TOC entry 206 (class 1259 OID 81556)
-- Dependencies: 205 7
-- Name: processors_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE processors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.processors_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3625 (class 0 OID 0)
-- Dependencies: 206
-- Name: processors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE processors_id_seq OWNED BY processors.id;


--
-- TOC entry 207 (class 1259 OID 81558)
-- Dependencies: 3255 1420 7
-- Name: product_adu; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE product_adu (
    product_version_id integer NOT NULL,
    os_name citext NOT NULL,
    adu_date date NOT NULL,
    adu_count bigint DEFAULT 0 NOT NULL
);


ALTER TABLE public.product_adu OWNER TO breakpad_rw;

--
-- TOC entry 263 (class 1259 OID 84647)
-- Dependencies: 3021 1420 7 1420
-- Name: product_crash_ratio; Type: VIEW; Schema: public; Owner: breakpad_rw
--

CREATE VIEW product_crash_ratio AS
    SELECT crcounts.product_version_id, product_versions.product_name, product_versions.version_string, crcounts.report_date AS adu_date, sum(crcounts.report_count) AS crashes, sum(crcounts.adu) AS adu_count, (product_release_channels.throttle)::numeric(5,2) AS throttle, (sum(((crcounts.report_count)::numeric / product_release_channels.throttle)))::integer AS adjusted_crashes, crash_hadu(sum(crcounts.report_count), sum(crcounts.adu), product_release_channels.throttle) AS crash_ratio FROM (((crashes_by_user crcounts JOIN crash_types USING (crash_type_id)) JOIN product_versions ON ((crcounts.product_version_id = product_versions.product_version_id))) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) WHERE crash_types.include_agg GROUP BY crcounts.product_version_id, product_versions.product_name, product_versions.version_string, crcounts.report_date, product_release_channels.throttle;


ALTER TABLE public.product_crash_ratio OWNER TO breakpad_rw;

--
-- TOC entry 208 (class 1259 OID 81565)
-- Dependencies: 1426 7 1426
-- Name: product_info_changelog; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE product_info_changelog (
    product_version_id integer NOT NULL,
    user_name text NOT NULL,
    changed_on timestamp with time zone NOT NULL,
    oldrec product_info_change,
    newrec product_info_change
);


ALTER TABLE public.product_info_changelog OWNER TO breakpad_rw;

--
-- TOC entry 264 (class 1259 OID 84652)
-- Dependencies: 3022 7 1420 1420 1420 1420
-- Name: product_os_crash_ratio; Type: VIEW; Schema: public; Owner: breakpad_rw
--

CREATE VIEW product_os_crash_ratio AS
    SELECT crcounts.product_version_id, product_versions.product_name, product_versions.version_string, os_names.os_short_name, os_names.os_name, crcounts.report_date AS adu_date, sum(crcounts.report_count) AS crashes, sum(crcounts.adu) AS adu_count, (product_release_channels.throttle)::numeric(5,2) AS throttle, (sum(((crcounts.report_count)::numeric / product_release_channels.throttle)))::integer AS adjusted_crashes, crash_hadu(sum(crcounts.report_count), sum(crcounts.adu), product_release_channels.throttle) AS crash_ratio FROM ((((crashes_by_user crcounts JOIN crash_types USING (crash_type_id)) JOIN product_versions ON ((crcounts.product_version_id = product_versions.product_version_id))) JOIN os_names ON ((crcounts.os_short_name = os_names.os_short_name))) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) WHERE crash_types.include_agg GROUP BY crcounts.product_version_id, product_versions.product_name, product_versions.version_string, os_names.os_name, os_names.os_short_name, crcounts.report_date, product_release_channels.throttle;


ALTER TABLE public.product_os_crash_ratio OWNER TO breakpad_rw;

--
-- TOC entry 209 (class 1259 OID 81571)
-- Dependencies: 3256 1424 1424 7 1420
-- Name: product_productid_map; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE product_productid_map (
    product_name citext NOT NULL,
    productid text NOT NULL,
    rewrite boolean DEFAULT false NOT NULL,
    version_began major_version NOT NULL,
    version_ended major_version
);


ALTER TABLE public.product_productid_map OWNER TO breakpad_rw;

--
-- TOC entry 248 (class 1259 OID 84526)
-- Dependencies: 3013 7 1420 1420
-- Name: product_selector; Type: VIEW; Schema: public; Owner: breakpad_rw
--

CREATE VIEW product_selector AS
    SELECT product_versions.product_name, product_versions.version_string, 'new'::text AS which_table, product_versions.version_sort, product_versions.has_builds, product_versions.is_rapid_beta FROM product_versions WHERE (now() <= product_versions.sunset_date) ORDER BY product_versions.product_name, product_versions.version_string;


ALTER TABLE public.product_selector OWNER TO breakpad_rw;

--
-- TOC entry 210 (class 1259 OID 81583)
-- Dependencies: 1420 7
-- Name: product_version_builds; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE product_version_builds (
    product_version_id integer NOT NULL,
    build_id numeric NOT NULL,
    platform text NOT NULL,
    repository citext
);


ALTER TABLE public.product_version_builds OWNER TO breakpad_rw;

--
-- TOC entry 157 (class 1259 OID 81249)
-- Dependencies: 156 7
-- Name: product_version_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE product_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.product_version_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3633 (class 0 OID 0)
-- Dependencies: 157
-- Name: product_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE product_version_id_seq OWNED BY product_versions.product_version_id;


--
-- TOC entry 211 (class 1259 OID 81595)
-- Dependencies: 7
-- Name: rank_compare; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE rank_compare (
    product_version_id integer NOT NULL,
    signature_id integer NOT NULL,
    rank_days integer NOT NULL,
    report_count integer,
    total_reports bigint,
    rank_report_count integer,
    percent_of_total numeric
);


ALTER TABLE public.rank_compare OWNER TO breakpad_rw;

--
-- TOC entry 212 (class 1259 OID 81601)
-- Dependencies: 7
-- Name: raw_adu; Type: TABLE; Schema: public; Owner: breakpad_metrics; Tablespace: 
--

CREATE TABLE raw_adu (
    adu_count integer,
    date date,
    product_name text,
    product_os_platform text,
    product_os_version text,
    product_version text,
    build text,
    build_channel text,
    product_guid text
);


ALTER TABLE public.raw_adu OWNER TO breakpad_metrics;

--
-- TOC entry 213 (class 1259 OID 81607)
-- Dependencies: 7 1420
-- Name: reasons; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reasons (
    reason_id integer NOT NULL,
    reason citext NOT NULL,
    first_seen timestamp with time zone
);


ALTER TABLE public.reasons OWNER TO breakpad_rw;

--
-- TOC entry 214 (class 1259 OID 81613)
-- Dependencies: 7 213
-- Name: reasons_reason_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE reasons_reason_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.reasons_reason_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3638 (class 0 OID 0)
-- Dependencies: 214
-- Name: reasons_reason_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE reasons_reason_id_seq OWNED BY reasons.reason_id;


--
-- TOC entry 215 (class 1259 OID 81615)
-- Dependencies: 1420 7
-- Name: release_channel_matches; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE release_channel_matches (
    release_channel citext NOT NULL,
    match_string text NOT NULL
);


ALTER TABLE public.release_channel_matches OWNER TO breakpad_rw;

--
-- TOC entry 216 (class 1259 OID 81621)
-- Dependencies: 1420 7
-- Name: release_repositories; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE release_repositories (
    repository citext NOT NULL
);


ALTER TABLE public.release_repositories OWNER TO breakpad_rw;

--
-- TOC entry 217 (class 1259 OID 81627)
-- Dependencies: 3258 1420 1420 1420 7
-- Name: releases_raw; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE releases_raw (
    product_name citext NOT NULL,
    version text NOT NULL,
    platform text NOT NULL,
    build_id numeric NOT NULL,
    build_type citext NOT NULL,
    beta_number integer,
    repository citext DEFAULT 'mozilla-release'::citext NOT NULL
);


ALTER TABLE public.releases_raw OWNER TO breakpad_rw;

--
-- TOC entry 218 (class 1259 OID 81634)
-- Dependencies: 7
-- Name: replication_test; Type: TABLE; Schema: public; Owner: monitoring; Tablespace: 
--

CREATE TABLE replication_test (
    id smallint,
    test boolean
);


ALTER TABLE public.replication_test OWNER TO monitoring;

--
-- TOC entry 219 (class 1259 OID 81637)
-- Dependencies: 3259 3260 3261 3262 1420 7
-- Name: report_partition_info; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE report_partition_info (
    table_name citext NOT NULL,
    build_order integer DEFAULT 1 NOT NULL,
    keys text[] DEFAULT '{}'::text[] NOT NULL,
    indexes text[] DEFAULT '{}'::text[] NOT NULL,
    fkeys text[] DEFAULT '{}'::text[] NOT NULL
);


ALTER TABLE public.report_partition_info OWNER TO breakpad_rw;

--
-- TOC entry 220 (class 1259 OID 81647)
-- Dependencies: 7
-- Name: reports; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports (
    id integer NOT NULL,
    client_crash_date timestamp with time zone,
    date_processed timestamp with time zone,
    uuid character varying(50) NOT NULL,
    product character varying(30),
    version character varying(16),
    build character varying(30),
    signature character varying(255),
    url character varying(255),
    install_age integer,
    last_crash integer,
    uptime integer,
    cpu_name character varying(100),
    cpu_info character varying(100),
    reason character varying(255),
    address character varying(20),
    os_name character varying(100),
    os_version character varying(100),
    email character varying(100),
    user_id character varying(50),
    started_datetime timestamp with time zone,
    completed_datetime timestamp with time zone,
    success boolean,
    truncated boolean,
    processor_notes text,
    user_comments character varying(1024),
    app_notes character varying(1024),
    distributor character varying(20),
    distributor_version character varying(20),
    topmost_filenames text,
    addons_checked boolean,
    flash_version text,
    hangid text,
    process_type text,
    release_channel text,
    productid text
);


ALTER TABLE public.reports OWNER TO breakpad_rw;

--
-- TOC entry 221 (class 1259 OID 81653)
-- Dependencies: 7
-- Name: reports_bad; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_bad (
    uuid text NOT NULL,
    date_processed timestamp with time zone NOT NULL
);


ALTER TABLE public.reports_bad OWNER TO breakpad_rw;

--
-- TOC entry 222 (class 1259 OID 81659)
-- Dependencies: 7 1420 1420 1420 1420
-- Name: reports_clean; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_clean (
    uuid text NOT NULL,
    date_processed timestamp with time zone NOT NULL,
    client_crash_date timestamp with time zone,
    product_version_id integer,
    build numeric,
    signature_id integer NOT NULL,
    install_age interval,
    uptime interval,
    reason_id integer NOT NULL,
    address_id integer NOT NULL,
    os_name citext NOT NULL,
    os_version_id integer NOT NULL,
    hang_id text,
    flash_version_id integer NOT NULL,
    process_type citext NOT NULL,
    release_channel citext NOT NULL,
    duplicate_of text,
    domain_id integer NOT NULL,
    architecture citext,
    cores integer
);


ALTER TABLE public.reports_clean OWNER TO breakpad_rw;

--
-- TOC entry 242 (class 1259 OID 82258)
-- Dependencies: 3283 1420 1420 222 7 1420 1420
-- Name: reports_clean_20120625; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_clean_20120625 (
    CONSTRAINT date_processed_week CHECK (((date_processed >= timezone('UTC'::text, '2012-06-25 00:00:00'::timestamp without time zone)) AND (date_processed < timezone('UTC'::text, '2012-07-02 00:00:00'::timestamp without time zone))))
)
INHERITS (reports_clean);


ALTER TABLE public.reports_clean_20120625 OWNER TO breakpad_rw;

--
-- TOC entry 244 (class 1259 OID 82848)
-- Dependencies: 3285 1420 1420 1420 222 1420 7
-- Name: reports_clean_20120702; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_clean_20120702 (
    CONSTRAINT date_processed_week CHECK (((date_processed >= timezone('UTC'::text, '2012-07-02 00:00:00'::timestamp without time zone)) AND (date_processed < timezone('UTC'::text, '2012-07-09 00:00:00'::timestamp without time zone))))
)
INHERITS (reports_clean);


ALTER TABLE public.reports_clean_20120702 OWNER TO breakpad_rw;

--
-- TOC entry 246 (class 1259 OID 83857)
-- Dependencies: 3287 7 1420 1420 1420 1420 222
-- Name: reports_clean_20120709; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_clean_20120709 (
    CONSTRAINT date_processed_week CHECK (((date_processed >= timezone('UTC'::text, '2012-07-09 00:00:00'::timestamp without time zone)) AND (date_processed < timezone('UTC'::text, '2012-07-16 00:00:00'::timestamp without time zone))))
)
INHERITS (reports_clean);


ALTER TABLE public.reports_clean_20120709 OWNER TO breakpad_rw;

--
-- TOC entry 223 (class 1259 OID 81665)
-- Dependencies: 7
-- Name: reports_duplicates; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_duplicates (
    uuid text NOT NULL,
    duplicate_of text NOT NULL,
    date_processed timestamp with time zone NOT NULL
);


ALTER TABLE public.reports_duplicates OWNER TO breakpad_rw;

--
-- TOC entry 224 (class 1259 OID 81671)
-- Dependencies: 220 7
-- Name: reports_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE reports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.reports_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3682 (class 0 OID 0)
-- Dependencies: 224
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE reports_id_seq OWNED BY reports.id;


--
-- TOC entry 225 (class 1259 OID 81673)
-- Dependencies: 1420 7 1420 1420
-- Name: reports_user_info; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_user_info (
    uuid text NOT NULL,
    date_processed timestamp with time zone NOT NULL,
    user_comments citext,
    app_notes citext,
    email citext,
    url text
);


ALTER TABLE public.reports_user_info OWNER TO breakpad_rw;

--
-- TOC entry 243 (class 1259 OID 82279)
-- Dependencies: 3284 1420 7 225 1420 1420
-- Name: reports_user_info_20120625; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_user_info_20120625 (
    CONSTRAINT date_processed_week CHECK (((date_processed >= timezone('UTC'::text, '2012-06-25 00:00:00'::timestamp without time zone)) AND (date_processed < timezone('UTC'::text, '2012-07-02 00:00:00'::timestamp without time zone))))
)
INHERITS (reports_user_info);


ALTER TABLE public.reports_user_info_20120625 OWNER TO breakpad_rw;

--
-- TOC entry 245 (class 1259 OID 82869)
-- Dependencies: 3286 7 1420 1420 1420 225
-- Name: reports_user_info_20120702; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_user_info_20120702 (
    CONSTRAINT date_processed_week CHECK (((date_processed >= timezone('UTC'::text, '2012-07-02 00:00:00'::timestamp without time zone)) AND (date_processed < timezone('UTC'::text, '2012-07-09 00:00:00'::timestamp without time zone))))
)
INHERITS (reports_user_info);


ALTER TABLE public.reports_user_info_20120702 OWNER TO breakpad_rw;

--
-- TOC entry 247 (class 1259 OID 83878)
-- Dependencies: 3288 1420 1420 1420 7 225
-- Name: reports_user_info_20120709; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE reports_user_info_20120709 (
    CONSTRAINT date_processed_week CHECK (((date_processed >= timezone('UTC'::text, '2012-07-09 00:00:00'::timestamp without time zone)) AND (date_processed < timezone('UTC'::text, '2012-07-16 00:00:00'::timestamp without time zone))))
)
INHERITS (reports_user_info);


ALTER TABLE public.reports_user_info_20120709 OWNER TO breakpad_rw;

--
-- TOC entry 226 (class 1259 OID 81679)
-- Dependencies: 7
-- Name: seq_reports_id; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE seq_reports_id
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seq_reports_id OWNER TO breakpad_rw;

--
-- TOC entry 227 (class 1259 OID 81681)
-- Dependencies: 7
-- Name: server_status; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE server_status (
    id integer NOT NULL,
    date_recently_completed timestamp with time zone,
    date_oldest_job_queued timestamp with time zone,
    avg_process_sec real,
    avg_wait_sec real,
    waiting_job_count integer NOT NULL,
    processors_count integer NOT NULL,
    date_created timestamp with time zone NOT NULL
);


ALTER TABLE public.server_status OWNER TO breakpad_rw;

--
-- TOC entry 228 (class 1259 OID 81684)
-- Dependencies: 7 227
-- Name: server_status_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE server_status_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.server_status_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3691 (class 0 OID 0)
-- Dependencies: 228
-- Name: server_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE server_status_id_seq OWNED BY server_status.id;


--
-- TOC entry 229 (class 1259 OID 81686)
-- Dependencies: 3265 7
-- Name: sessions; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE sessions (
    session_id character varying(127) NOT NULL,
    last_activity integer NOT NULL,
    data text NOT NULL,
    CONSTRAINT last_activity_check CHECK ((last_activity >= 0))
);


ALTER TABLE public.sessions OWNER TO breakpad_rw;

--
-- TOC entry 230 (class 1259 OID 81701)
-- Dependencies: 7
-- Name: signature_products; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE signature_products (
    signature_id integer NOT NULL,
    product_version_id integer NOT NULL,
    first_report timestamp with time zone
);


ALTER TABLE public.signature_products OWNER TO breakpad_rw;

--
-- TOC entry 231 (class 1259 OID 81704)
-- Dependencies: 3266 3267 1420 7
-- Name: signature_products_rollup; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE signature_products_rollup (
    signature_id integer NOT NULL,
    product_name citext NOT NULL,
    ver_count integer DEFAULT 0 NOT NULL,
    version_list text[] DEFAULT '{}'::text[] NOT NULL
);


ALTER TABLE public.signature_products_rollup OWNER TO breakpad_rw;

--
-- TOC entry 232 (class 1259 OID 81712)
-- Dependencies: 181 7
-- Name: signatures_signature_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE signatures_signature_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.signatures_signature_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3696 (class 0 OID 0)
-- Dependencies: 232
-- Name: signatures_signature_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE signatures_signature_id_seq OWNED BY signatures.signature_id;


--
-- TOC entry 233 (class 1259 OID 81714)
-- Dependencies: 7
-- Name: socorro_db_version; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE socorro_db_version (
    current_version text NOT NULL,
    refreshed_at timestamp with time zone
);


ALTER TABLE public.socorro_db_version OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 81720)
-- Dependencies: 3268 7
-- Name: socorro_db_version_history; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE socorro_db_version_history (
    version text NOT NULL,
    upgraded_on timestamp with time zone DEFAULT now() NOT NULL,
    backfill_to date
);


ALTER TABLE public.socorro_db_version_history OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 81727)
-- Dependencies: 1420 1420 1420 1420 1420 1424 7
-- Name: special_product_platforms; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE special_product_platforms (
    platform citext NOT NULL,
    repository citext NOT NULL,
    release_channel citext NOT NULL,
    release_name citext NOT NULL,
    product_name citext NOT NULL,
    min_version major_version NOT NULL
);


ALTER TABLE public.special_product_platforms OWNER TO breakpad_rw;

--
-- TOC entry 236 (class 1259 OID 81733)
-- Dependencies: 3269 3270 3271 3272 3273 1420 7 1420
-- Name: tcbs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE tcbs (
    signature_id integer NOT NULL,
    report_date date NOT NULL,
    product_version_id integer NOT NULL,
    process_type citext NOT NULL,
    release_channel citext NOT NULL,
    report_count integer DEFAULT 0 NOT NULL,
    win_count integer DEFAULT 0 NOT NULL,
    mac_count integer DEFAULT 0 NOT NULL,
    lin_count integer DEFAULT 0 NOT NULL,
    hang_count integer DEFAULT 0 NOT NULL,
    startup_count integer
);


ALTER TABLE public.tcbs OWNER TO breakpad_rw;

--
-- TOC entry 265 (class 1259 OID 84660)
-- Dependencies: 3296 3297 3298 3299 3300 1420 7 1420
-- Name: tcbs_build; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE tcbs_build (
    signature_id integer NOT NULL,
    build_date date NOT NULL,
    report_date date NOT NULL,
    product_version_id integer NOT NULL,
    process_type citext NOT NULL,
    release_channel citext NOT NULL,
    report_count integer DEFAULT 0 NOT NULL,
    win_count integer DEFAULT 0 NOT NULL,
    mac_count integer DEFAULT 0 NOT NULL,
    lin_count integer DEFAULT 0 NOT NULL,
    hang_count integer DEFAULT 0 NOT NULL,
    startup_count integer
);


ALTER TABLE public.tcbs_build OWNER TO breakpad_rw;

--
-- TOC entry 237 (class 1259 OID 81763)
-- Dependencies: 3274 3275 3276 3277 3278 3279 1420 7
-- Name: transform_rules; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE transform_rules (
    transform_rule_id integer NOT NULL,
    category citext NOT NULL,
    rule_order integer NOT NULL,
    predicate text DEFAULT ''::text NOT NULL,
    predicate_args text DEFAULT ''::text NOT NULL,
    predicate_kwargs text DEFAULT ''::text NOT NULL,
    action text DEFAULT ''::text NOT NULL,
    action_args text DEFAULT ''::text NOT NULL,
    action_kwargs text DEFAULT ''::text NOT NULL
);


ALTER TABLE public.transform_rules OWNER TO breakpad_rw;

--
-- TOC entry 238 (class 1259 OID 81775)
-- Dependencies: 237 7
-- Name: transform_rules_transform_rule_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE transform_rules_transform_rule_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.transform_rules_transform_rule_id_seq OWNER TO breakpad_rw;

--
-- TOC entry 3703 (class 0 OID 0)
-- Dependencies: 238
-- Name: transform_rules_transform_rule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE transform_rules_transform_rule_id_seq OWNED BY transform_rules.transform_rule_id;


--
-- TOC entry 239 (class 1259 OID 81777)
-- Dependencies: 3282 1420 7
-- Name: uptime_levels; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE uptime_levels (
    uptime_level integer NOT NULL,
    uptime_string citext NOT NULL,
    min_uptime interval NOT NULL,
    max_uptime interval NOT NULL,
    CONSTRAINT period_check CHECK ((min_uptime < max_uptime))
);


ALTER TABLE public.uptime_levels OWNER TO breakpad_rw;

--
-- TOC entry 240 (class 1259 OID 81784)
-- Dependencies: 239 7
-- Name: uptime_levels_uptime_level_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE uptime_levels_uptime_level_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.uptime_levels_uptime_level_seq OWNER TO breakpad_rw;

--
-- TOC entry 3705 (class 0 OID 0)
-- Dependencies: 240
-- Name: uptime_levels_uptime_level_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE uptime_levels_uptime_level_seq OWNED BY uptime_levels.uptime_level;


--
-- TOC entry 241 (class 1259 OID 81794)
-- Dependencies: 1420 7
-- Name: windows_versions; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE TABLE windows_versions (
    windows_version_name citext NOT NULL,
    major_version integer NOT NULL,
    minor_version integer NOT NULL
);


ALTER TABLE public.windows_versions OWNER TO breakpad_rw;

--
-- TOC entry 3224 (class 2604 OID 81800)
-- Dependencies: 154 153
-- Name: address_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY addresses ALTER COLUMN address_id SET DEFAULT nextval('addresses_address_id_seq'::regclass);


--
-- TOC entry 3235 (class 2604 OID 81801)
-- Dependencies: 164 163
-- Name: correlation_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY correlations ALTER COLUMN correlation_id SET DEFAULT nextval('correlations_correlation_id_seq'::regclass);


--
-- TOC entry 3289 (class 2604 OID 84560)
-- Dependencies: 253 254 254
-- Name: crash_type_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY crash_types ALTER COLUMN crash_type_id SET DEFAULT nextval('crash_types_crash_type_id_seq'::regclass);


--
-- TOC entry 3239 (class 2604 OID 81803)
-- Dependencies: 171 170
-- Name: domain_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY domains ALTER COLUMN domain_id SET DEFAULT nextval('domains_domain_id_seq'::regclass);


--
-- TOC entry 3243 (class 2604 OID 81804)
-- Dependencies: 174 172
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY email_campaigns ALTER COLUMN id SET DEFAULT nextval('email_campaigns_id_seq'::regclass);


--
-- TOC entry 3246 (class 2604 OID 81805)
-- Dependencies: 176 175
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY email_contacts ALTER COLUMN id SET DEFAULT nextval('email_contacts_id_seq'::regclass);


--
-- TOC entry 3247 (class 2604 OID 81806)
-- Dependencies: 180 179
-- Name: flash_version_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY flash_versions ALTER COLUMN flash_version_id SET DEFAULT nextval('flash_versions_flash_version_id_seq'::regclass);


--
-- TOC entry 3250 (class 2604 OID 81807)
-- Dependencies: 185 184
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY jobs ALTER COLUMN id SET DEFAULT nextval('jobs_id_seq'::regclass);


--
-- TOC entry 3252 (class 2604 OID 81808)
-- Dependencies: 195 194
-- Name: os_version_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY os_versions ALTER COLUMN os_version_id SET DEFAULT nextval('os_versions_os_version_id_seq'::regclass);


--
-- TOC entry 3253 (class 2604 OID 81810)
-- Dependencies: 199 198
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins ALTER COLUMN id SET DEFAULT nextval('plugins_id_seq'::regclass);


--
-- TOC entry 3254 (class 2604 OID 81811)
-- Dependencies: 206 205
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY processors ALTER COLUMN id SET DEFAULT nextval('processors_id_seq'::regclass);


--
-- TOC entry 3230 (class 2604 OID 84525)
-- Dependencies: 157 156
-- Name: product_version_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_versions ALTER COLUMN product_version_id SET DEFAULT nextval('product_version_id_seq'::regclass);


--
-- TOC entry 3257 (class 2604 OID 81813)
-- Dependencies: 214 213
-- Name: reason_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY reasons ALTER COLUMN reason_id SET DEFAULT nextval('reasons_reason_id_seq'::regclass);


--
-- TOC entry 3263 (class 2604 OID 81814)
-- Dependencies: 224 220
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY reports ALTER COLUMN id SET DEFAULT nextval('reports_id_seq'::regclass);


--
-- TOC entry 3264 (class 2604 OID 81815)
-- Dependencies: 228 227
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY server_status ALTER COLUMN id SET DEFAULT nextval('server_status_id_seq'::regclass);


--
-- TOC entry 3248 (class 2604 OID 81816)
-- Dependencies: 232 181
-- Name: signature_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY signatures ALTER COLUMN signature_id SET DEFAULT nextval('signatures_signature_id_seq'::regclass);


--
-- TOC entry 3280 (class 2604 OID 81819)
-- Dependencies: 238 237
-- Name: transform_rule_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY transform_rules ALTER COLUMN transform_rule_id SET DEFAULT nextval('transform_rules_transform_rule_id_seq'::regclass);


--
-- TOC entry 3281 (class 2604 OID 81820)
-- Dependencies: 240 239
-- Name: uptime_level; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY uptime_levels ALTER COLUMN uptime_level SET DEFAULT nextval('uptime_levels_uptime_level_seq'::regclass);


--
-- TOC entry 3302 (class 2606 OID 81823)
-- Dependencies: 153 153
-- Name: addresses_address_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY addresses
    ADD CONSTRAINT addresses_address_key UNIQUE (address);


--
-- TOC entry 3304 (class 2606 OID 81825)
-- Dependencies: 153 153
-- Name: addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY addresses
    ADD CONSTRAINT addresses_pkey PRIMARY KEY (address_id);


--
-- TOC entry 3314 (class 2606 OID 81829)
-- Dependencies: 158 158 158
-- Name: bug_associations_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY bug_associations
    ADD CONSTRAINT bug_associations_pkey PRIMARY KEY (signature, bug_id);


--
-- TOC entry 3317 (class 2606 OID 81831)
-- Dependencies: 159 159
-- Name: bugs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY bugs
    ADD CONSTRAINT bugs_pkey PRIMARY KEY (id);


--
-- TOC entry 3515 (class 2606 OID 84552)
-- Dependencies: 252 252 252 252 252
-- Name: build_adu_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY build_adu
    ADD CONSTRAINT build_adu_key PRIMARY KEY (product_version_id, build_date, adu_date, os_name);


--
-- TOC entry 3319 (class 2606 OID 81833)
-- Dependencies: 160 160 160 160
-- Name: correlation_addons_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY correlation_addons
    ADD CONSTRAINT correlation_addons_key UNIQUE (correlation_id, addon_key, addon_version);


--
-- TOC entry 3321 (class 2606 OID 81835)
-- Dependencies: 161 161 161 161
-- Name: correlation_cores_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY correlation_cores
    ADD CONSTRAINT correlation_cores_key UNIQUE (correlation_id, architecture, cores);


--
-- TOC entry 3323 (class 2606 OID 81837)
-- Dependencies: 162 162 162 162
-- Name: correlation_modules_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY correlation_modules
    ADD CONSTRAINT correlation_modules_key UNIQUE (correlation_id, module_signature, module_version);


--
-- TOC entry 3325 (class 2606 OID 81839)
-- Dependencies: 163 163 163 163 163
-- Name: correlations_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY correlations
    ADD CONSTRAINT correlations_key UNIQUE (product_version_id, os_name, reason_id, signature_id);


--
-- TOC entry 3327 (class 2606 OID 81841)
-- Dependencies: 163 163
-- Name: correlations_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY correlations
    ADD CONSTRAINT correlations_pkey PRIMARY KEY (correlation_id);


--
-- TOC entry 3517 (class 2606 OID 84568)
-- Dependencies: 254 254
-- Name: crash_type_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY crash_types
    ADD CONSTRAINT crash_type_key UNIQUE (crash_type);


--
-- TOC entry 3519 (class 2606 OID 84570)
-- Dependencies: 254 254
-- Name: crash_type_short_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY crash_types
    ADD CONSTRAINT crash_type_short_key UNIQUE (crash_type_short);


--
-- TOC entry 3521 (class 2606 OID 84566)
-- Dependencies: 254 254
-- Name: crash_types_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY crash_types
    ADD CONSTRAINT crash_types_pkey PRIMARY KEY (crash_type_id);


--
-- TOC entry 3525 (class 2606 OID 84603)
-- Dependencies: 257 257 257 257 257 257
-- Name: crashes_by_user_build_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY crashes_by_user_build
    ADD CONSTRAINT crashes_by_user_build_key PRIMARY KEY (product_version_id, build_date, report_date, os_short_name, crash_type_id);


--
-- TOC entry 3523 (class 2606 OID 84583)
-- Dependencies: 255 255 255 255 255
-- Name: crashes_by_user_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY crashes_by_user
    ADD CONSTRAINT crashes_by_user_key PRIMARY KEY (product_version_id, report_date, os_short_name, crash_type_id);


--
-- TOC entry 3330 (class 2606 OID 81843)
-- Dependencies: 165 165
-- Name: crontabber_state_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY crontabber_state
    ADD CONSTRAINT crontabber_state_pkey PRIMARY KEY (last_updated);


--
-- TOC entry 3335 (class 2606 OID 81849)
-- Dependencies: 166 166
-- Name: daily_hangs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY daily_hangs
    ADD CONSTRAINT daily_hangs_pkey PRIMARY KEY (plugin_uuid);


--
-- TOC entry 3347 (class 2606 OID 81853)
-- Dependencies: 170 170
-- Name: domains_domain_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY domains
    ADD CONSTRAINT domains_domain_key UNIQUE (domain);


--
-- TOC entry 3349 (class 2606 OID 81855)
-- Dependencies: 170 170
-- Name: domains_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY domains
    ADD CONSTRAINT domains_pkey PRIMARY KEY (domain_id);


--
-- TOC entry 3354 (class 2606 OID 81857)
-- Dependencies: 173 173 173
-- Name: email_campaigns_contacts_mapping_unique; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY email_campaigns_contacts
    ADD CONSTRAINT email_campaigns_contacts_mapping_unique UNIQUE (email_campaigns_id, email_contacts_id);


--
-- TOC entry 3351 (class 2606 OID 81859)
-- Dependencies: 172 172
-- Name: email_campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY email_campaigns
    ADD CONSTRAINT email_campaigns_pkey PRIMARY KEY (id);


--
-- TOC entry 3356 (class 2606 OID 81861)
-- Dependencies: 175 175
-- Name: email_contacts_email_unique; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY email_contacts
    ADD CONSTRAINT email_contacts_email_unique UNIQUE (email);


--
-- TOC entry 3358 (class 2606 OID 81863)
-- Dependencies: 175 175
-- Name: email_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY email_contacts
    ADD CONSTRAINT email_contacts_pkey PRIMARY KEY (id);


--
-- TOC entry 3360 (class 2606 OID 81865)
-- Dependencies: 175 175
-- Name: email_contacts_token_unique; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY email_contacts
    ADD CONSTRAINT email_contacts_token_unique UNIQUE (subscribe_token);


--
-- TOC entry 3362 (class 2606 OID 81867)
-- Dependencies: 177 177 177 177
-- Name: explosiveness_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY explosiveness
    ADD CONSTRAINT explosiveness_key PRIMARY KEY (product_version_id, signature_id, last_date);


--
-- TOC entry 3391 (class 2606 OID 81869)
-- Dependencies: 198 198 198
-- Name: filename_name_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY plugins
    ADD CONSTRAINT filename_name_key UNIQUE (filename, name);


--
-- TOC entry 3366 (class 2606 OID 81871)
-- Dependencies: 179 179
-- Name: flash_versions_flash_version_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY flash_versions
    ADD CONSTRAINT flash_versions_flash_version_key UNIQUE (flash_version);


--
-- TOC entry 3368 (class 2606 OID 81873)
-- Dependencies: 179 179
-- Name: flash_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY flash_versions
    ADD CONSTRAINT flash_versions_pkey PRIMARY KEY (flash_version_id);


--
-- TOC entry 3529 (class 2606 OID 84639)
-- Dependencies: 261 261 261 261
-- Name: home_page_graph_build_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY home_page_graph_build
    ADD CONSTRAINT home_page_graph_build_key PRIMARY KEY (product_version_id, build_date, report_date);


--
-- TOC entry 3527 (class 2606 OID 84626)
-- Dependencies: 259 259 259
-- Name: home_page_graph_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY home_page_graph
    ADD CONSTRAINT home_page_graph_key PRIMARY KEY (product_version_id, report_date);


--
-- TOC entry 3376 (class 2606 OID 81875)
-- Dependencies: 184 184
-- Name: jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- TOC entry 3378 (class 2606 OID 81877)
-- Dependencies: 184 184
-- Name: jobs_uuid_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_uuid_key UNIQUE (uuid);


--
-- TOC entry 3380 (class 2606 OID 81879)
-- Dependencies: 191 191 191 191
-- Name: nightly_builds_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY nightly_builds
    ADD CONSTRAINT nightly_builds_key PRIMARY KEY (product_version_id, build_date, days_out);


--
-- TOC entry 3383 (class 2606 OID 81881)
-- Dependencies: 192 192 192
-- Name: os_name_matches_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY os_name_matches
    ADD CONSTRAINT os_name_matches_key PRIMARY KEY (os_name, match_string);


--
-- TOC entry 3385 (class 2606 OID 81883)
-- Dependencies: 193 193
-- Name: os_names_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY os_names
    ADD CONSTRAINT os_names_pkey PRIMARY KEY (os_name);


--
-- TOC entry 3387 (class 2606 OID 81885)
-- Dependencies: 194 194 194 194
-- Name: os_versions_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY os_versions
    ADD CONSTRAINT os_versions_key UNIQUE (os_name, major_version, minor_version);


--
-- TOC entry 3389 (class 2606 OID 81887)
-- Dependencies: 194 194
-- Name: os_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY os_versions
    ADD CONSTRAINT os_versions_pkey PRIMARY KEY (os_version_id);


--
-- TOC entry 3393 (class 2606 OID 81891)
-- Dependencies: 198 198
-- Name: plugins_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY plugins
    ADD CONSTRAINT plugins_pkey PRIMARY KEY (id);


--
-- TOC entry 3397 (class 2606 OID 81893)
-- Dependencies: 203 203
-- Name: priorityjobs_logging_switch_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY priorityjobs_logging_switch
    ADD CONSTRAINT priorityjobs_logging_switch_pkey PRIMARY KEY (log_jobs);


--
-- TOC entry 3395 (class 2606 OID 81895)
-- Dependencies: 201 201
-- Name: priorityjobs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY priorityjobs
    ADD CONSTRAINT priorityjobs_pkey PRIMARY KEY (uuid);


--
-- TOC entry 3399 (class 2606 OID 81897)
-- Dependencies: 204 204
-- Name: process_types_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY process_types
    ADD CONSTRAINT process_types_pkey PRIMARY KEY (process_type);


--
-- TOC entry 3401 (class 2606 OID 81899)
-- Dependencies: 205 205
-- Name: processors_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY processors
    ADD CONSTRAINT processors_pkey PRIMARY KEY (id);


--
-- TOC entry 3403 (class 2606 OID 81901)
-- Dependencies: 207 207 207 207
-- Name: product_adu_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY product_adu
    ADD CONSTRAINT product_adu_key PRIMARY KEY (product_version_id, adu_date, os_name);


--
-- TOC entry 3405 (class 2606 OID 81903)
-- Dependencies: 208 208 208 208
-- Name: product_info_changelog_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY product_info_changelog
    ADD CONSTRAINT product_info_changelog_key PRIMARY KEY (product_version_id, changed_on, user_name);


--
-- TOC entry 3407 (class 2606 OID 81905)
-- Dependencies: 209 209
-- Name: product_productid_map_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY product_productid_map
    ADD CONSTRAINT product_productid_map_pkey PRIMARY KEY (productid);


--
-- TOC entry 3341 (class 2606 OID 81907)
-- Dependencies: 167 167 167
-- Name: product_release_channels_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY product_release_channels
    ADD CONSTRAINT product_release_channels_key PRIMARY KEY (product_name, release_channel);


--
-- TOC entry 3411 (class 2606 OID 81909)
-- Dependencies: 210 210 210 210
-- Name: product_version_builds_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY product_version_builds
    ADD CONSTRAINT product_version_builds_key PRIMARY KEY (product_version_id, build_id, platform);


--
-- TOC entry 3307 (class 2606 OID 81911)
-- Dependencies: 156 156 156
-- Name: product_version_version_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY product_versions
    ADD CONSTRAINT product_version_version_key UNIQUE (product_name, version_string);


--
-- TOC entry 3310 (class 2606 OID 81913)
-- Dependencies: 156 156
-- Name: product_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY product_versions
    ADD CONSTRAINT product_versions_pkey PRIMARY KEY (product_version_id);


--
-- TOC entry 3409 (class 2606 OID 81923)
-- Dependencies: 209 209 209
-- Name: productid_map_key2; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY product_productid_map
    ADD CONSTRAINT productid_map_key2 UNIQUE (product_name, version_began);


--
-- TOC entry 3343 (class 2606 OID 81925)
-- Dependencies: 168 168
-- Name: products_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY products
    ADD CONSTRAINT products_pkey PRIMARY KEY (product_name);


--
-- TOC entry 3413 (class 2606 OID 81927)
-- Dependencies: 211 211 211 211
-- Name: rank_compare_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY rank_compare
    ADD CONSTRAINT rank_compare_key PRIMARY KEY (product_version_id, signature_id, rank_days);


--
-- TOC entry 3418 (class 2606 OID 81929)
-- Dependencies: 213 213
-- Name: reasons_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY reasons
    ADD CONSTRAINT reasons_pkey PRIMARY KEY (reason_id);


--
-- TOC entry 3420 (class 2606 OID 81931)
-- Dependencies: 213 213
-- Name: reasons_reason_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY reasons
    ADD CONSTRAINT reasons_reason_key UNIQUE (reason);


--
-- TOC entry 3422 (class 2606 OID 81935)
-- Dependencies: 215 215 215
-- Name: release_channel_matches_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY release_channel_matches
    ADD CONSTRAINT release_channel_matches_key PRIMARY KEY (release_channel, match_string);


--
-- TOC entry 3345 (class 2606 OID 81937)
-- Dependencies: 169 169
-- Name: release_channels_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY release_channels
    ADD CONSTRAINT release_channels_pkey PRIMARY KEY (release_channel);


--
-- TOC entry 3426 (class 2606 OID 81939)
-- Dependencies: 217 217 217 217 217 217 217
-- Name: release_raw_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY releases_raw
    ADD CONSTRAINT release_raw_key PRIMARY KEY (product_name, version, build_type, build_id, platform, repository);


--
-- TOC entry 3424 (class 2606 OID 81941)
-- Dependencies: 216 216
-- Name: release_repositories_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY release_repositories
    ADD CONSTRAINT release_repositories_pkey PRIMARY KEY (repository);


--
-- TOC entry 3429 (class 2606 OID 81943)
-- Dependencies: 219 219
-- Name: report_partition_info_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY report_partition_info
    ADD CONSTRAINT report_partition_info_pkey PRIMARY KEY (table_name);


--
-- TOC entry 3431 (class 2606 OID 81945)
-- Dependencies: 222 222
-- Name: reports_clean_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY reports_clean
    ADD CONSTRAINT reports_clean_pkey PRIMARY KEY (uuid);


--
-- TOC entry 3434 (class 2606 OID 81947)
-- Dependencies: 223 223
-- Name: reports_duplicates_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY reports_duplicates
    ADD CONSTRAINT reports_duplicates_pkey PRIMARY KEY (uuid);


--
-- TOC entry 3437 (class 2606 OID 81949)
-- Dependencies: 225 225
-- Name: reports_user_info_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY reports_user_info
    ADD CONSTRAINT reports_user_info_pkey PRIMARY KEY (uuid);


--
-- TOC entry 3440 (class 2606 OID 81951)
-- Dependencies: 227 227
-- Name: server_status_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY server_status
    ADD CONSTRAINT server_status_pkey PRIMARY KEY (id);


--
-- TOC entry 3442 (class 2606 OID 81953)
-- Dependencies: 229 229
-- Name: session_id_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY sessions
    ADD CONSTRAINT session_id_pkey PRIMARY KEY (session_id);


--
-- TOC entry 3444 (class 2606 OID 81957)
-- Dependencies: 230 230 230
-- Name: signature_products_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY signature_products
    ADD CONSTRAINT signature_products_key PRIMARY KEY (signature_id, product_version_id);


--
-- TOC entry 3447 (class 2606 OID 81959)
-- Dependencies: 231 231 231
-- Name: signature_products_rollup_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY signature_products_rollup
    ADD CONSTRAINT signature_products_rollup_key PRIMARY KEY (signature_id, product_name);


--
-- TOC entry 3370 (class 2606 OID 81961)
-- Dependencies: 181 181
-- Name: signatures_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY signatures
    ADD CONSTRAINT signatures_pkey PRIMARY KEY (signature_id);

ALTER TABLE signatures CLUSTER ON signatures_pkey;


--
-- TOC entry 3372 (class 2606 OID 81963)
-- Dependencies: 181 181
-- Name: signatures_signature_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY signatures
    ADD CONSTRAINT signatures_signature_key UNIQUE (signature);


--
-- TOC entry 3451 (class 2606 OID 81965)
-- Dependencies: 234 234 234
-- Name: socorro_db_version_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY socorro_db_version_history
    ADD CONSTRAINT socorro_db_version_history_pkey PRIMARY KEY (version, upgraded_on);


--
-- TOC entry 3449 (class 2606 OID 81967)
-- Dependencies: 233 233
-- Name: socorro_db_version_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY socorro_db_version
    ADD CONSTRAINT socorro_db_version_pkey PRIMARY KEY (current_version);


--
-- TOC entry 3453 (class 2606 OID 81969)
-- Dependencies: 235 235 235 235 235
-- Name: special_product_platforms_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY special_product_platforms
    ADD CONSTRAINT special_product_platforms_key PRIMARY KEY (release_name, platform, repository, release_channel);


--
-- TOC entry 3531 (class 2606 OID 84672)
-- Dependencies: 265 265 265 265 265 265
-- Name: tcbs_build_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY tcbs_build
    ADD CONSTRAINT tcbs_build_key PRIMARY KEY (product_version_id, report_date, build_date, process_type, signature_id);


--
-- TOC entry 3455 (class 2606 OID 81971)
-- Dependencies: 236 236 236 236 236 236
-- Name: tcbs_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY tcbs
    ADD CONSTRAINT tcbs_key PRIMARY KEY (signature_id, report_date, product_version_id, process_type, release_channel);


--
-- TOC entry 3460 (class 2606 OID 81979)
-- Dependencies: 237 237 237
-- Name: transform_rules_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY transform_rules
    ADD CONSTRAINT transform_rules_key UNIQUE (category, rule_order) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 3462 (class 2606 OID 81982)
-- Dependencies: 237 237
-- Name: transform_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY transform_rules
    ADD CONSTRAINT transform_rules_pkey PRIMARY KEY (transform_rule_id);


--
-- TOC entry 3464 (class 2606 OID 81984)
-- Dependencies: 239 239
-- Name: uptime_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY uptime_levels
    ADD CONSTRAINT uptime_levels_pkey PRIMARY KEY (uptime_level);


--
-- TOC entry 3466 (class 2606 OID 81986)
-- Dependencies: 239 239
-- Name: uptime_levels_uptime_string_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY uptime_levels
    ADD CONSTRAINT uptime_levels_uptime_string_key UNIQUE (uptime_string);


--
-- TOC entry 3468 (class 2606 OID 81990)
-- Dependencies: 241 241 241
-- Name: windows_version_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace: 
--

ALTER TABLE ONLY windows_versions
    ADD CONSTRAINT windows_version_key UNIQUE (major_version, minor_version);


--
-- TOC entry 3328 (class 1259 OID 81992)
-- Dependencies: 165 165
-- Name: crontabber_state_one_row; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE UNIQUE INDEX crontabber_state_one_row ON crontabber_state USING btree (((state IS NOT NULL)));


--
-- TOC entry 3331 (class 1259 OID 81993)
-- Dependencies: 166
-- Name: daily_hangs_browser_signature_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX daily_hangs_browser_signature_id ON daily_hangs USING btree (browser_signature_id);


--
-- TOC entry 3332 (class 1259 OID 81994)
-- Dependencies: 166
-- Name: daily_hangs_flash_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX daily_hangs_flash_version_id ON daily_hangs USING btree (flash_version_id);


--
-- TOC entry 3333 (class 1259 OID 81995)
-- Dependencies: 166
-- Name: daily_hangs_hang_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX daily_hangs_hang_id ON daily_hangs USING btree (hang_id);


--
-- TOC entry 3336 (class 1259 OID 81996)
-- Dependencies: 166
-- Name: daily_hangs_plugin_signature_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX daily_hangs_plugin_signature_id ON daily_hangs USING btree (plugin_signature_id);


--
-- TOC entry 3337 (class 1259 OID 81997)
-- Dependencies: 166
-- Name: daily_hangs_product_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX daily_hangs_product_version_id ON daily_hangs USING btree (product_version_id);


--
-- TOC entry 3338 (class 1259 OID 81998)
-- Dependencies: 166
-- Name: daily_hangs_report_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX daily_hangs_report_date ON daily_hangs USING btree (report_date);


--
-- TOC entry 3339 (class 1259 OID 81999)
-- Dependencies: 166
-- Name: daily_hangs_uuid; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX daily_hangs_uuid ON daily_hangs USING btree (uuid);


--
-- TOC entry 3352 (class 1259 OID 82000)
-- Dependencies: 172 172
-- Name: email_campaigns_product_signature_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX email_campaigns_product_signature_key ON email_campaigns USING btree (product, signature);


--
-- TOC entry 3363 (class 1259 OID 82001)
-- Dependencies: 177
-- Name: explosiveness_product_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX explosiveness_product_version_id ON explosiveness USING btree (product_version_id);


--
-- TOC entry 3364 (class 1259 OID 82002)
-- Dependencies: 177
-- Name: explosiveness_signature_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX explosiveness_signature_id ON explosiveness USING btree (signature_id);


--
-- TOC entry 3315 (class 1259 OID 82003)
-- Dependencies: 158
-- Name: idx_bug_associations_bug_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX idx_bug_associations_bug_id ON bug_associations USING btree (bug_id);


--
-- TOC entry 3438 (class 1259 OID 82004)
-- Dependencies: 227 227
-- Name: idx_server_status_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX idx_server_status_date ON server_status USING btree (date_created, id);


--
-- TOC entry 3373 (class 1259 OID 82005)
-- Dependencies: 184 184
-- Name: jobs_completeddatetime_queueddatetime_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX jobs_completeddatetime_queueddatetime_key ON jobs USING btree (completeddatetime, queueddatetime);


--
-- TOC entry 3374 (class 1259 OID 82006)
-- Dependencies: 184 184
-- Name: jobs_owner_starteddatetime_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX jobs_owner_starteddatetime_key ON jobs USING btree (owner, starteddatetime);

ALTER TABLE jobs CLUSTER ON jobs_owner_starteddatetime_key;


--
-- TOC entry 3381 (class 1259 OID 82007)
-- Dependencies: 191 191
-- Name: nightly_builds_product_version_id_report_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX nightly_builds_product_version_id_report_date ON nightly_builds USING btree (product_version_id, report_date);


--
-- TOC entry 3305 (class 1259 OID 82009)
-- Dependencies: 2671 156 156 156 156 2671
-- Name: product_version_unique_beta; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE UNIQUE INDEX product_version_unique_beta ON product_versions USING btree (product_name, release_version, beta_number) WHERE (beta_number IS NOT NULL);


--
-- TOC entry 3308 (class 1259 OID 82010)
-- Dependencies: 156
-- Name: product_versions_major_version; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX product_versions_major_version ON product_versions USING btree (major_version);


--
-- TOC entry 3311 (class 1259 OID 82011)
-- Dependencies: 2671 156
-- Name: product_versions_product_name; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX product_versions_product_name ON product_versions USING btree (product_name);


--
-- TOC entry 3312 (class 1259 OID 82012)
-- Dependencies: 156
-- Name: product_versions_version_sort; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX product_versions_version_sort ON product_versions USING btree (version_sort);


--
-- TOC entry 3414 (class 1259 OID 82017)
-- Dependencies: 211 211
-- Name: rank_compare_product_version_id_rank_report_count; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX rank_compare_product_version_id_rank_report_count ON rank_compare USING btree (product_version_id, rank_report_count);


--
-- TOC entry 3415 (class 1259 OID 82018)
-- Dependencies: 211
-- Name: rank_compare_signature_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX rank_compare_signature_id ON rank_compare USING btree (signature_id);


--
-- TOC entry 3416 (class 1259 OID 82019)
-- Dependencies: 212 212 212 212 212
-- Name: raw_adu_1_idx; Type: INDEX; Schema: public; Owner: breakpad_metrics; Tablespace: 
--

CREATE INDEX raw_adu_1_idx ON raw_adu USING btree (date, product_name, product_version, product_os_platform, product_os_version);


--
-- TOC entry 3427 (class 1259 OID 82020)
-- Dependencies: 217 217 320
-- Name: releases_raw_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX releases_raw_date ON releases_raw USING btree (build_date(build_id));


--
-- TOC entry 3469 (class 1259 OID 82273)
-- Dependencies: 242
-- Name: reports_clean_20120625_address_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_address_id ON reports_clean_20120625 USING btree (address_id);


--
-- TOC entry 3470 (class 1259 OID 82267)
-- Dependencies: 242 242 2671
-- Name: reports_clean_20120625_arch_cores; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_arch_cores ON reports_clean_20120625 USING btree (architecture, cores);


--
-- TOC entry 3471 (class 1259 OID 82268)
-- Dependencies: 242
-- Name: reports_clean_20120625_date_processed; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_date_processed ON reports_clean_20120625 USING btree (date_processed);


--
-- TOC entry 3472 (class 1259 OID 82278)
-- Dependencies: 242
-- Name: reports_clean_20120625_domain_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_domain_id ON reports_clean_20120625 USING btree (domain_id);


--
-- TOC entry 3473 (class 1259 OID 82274)
-- Dependencies: 242
-- Name: reports_clean_20120625_flash_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_flash_version_id ON reports_clean_20120625 USING btree (flash_version_id);


--
-- TOC entry 3474 (class 1259 OID 82275)
-- Dependencies: 242
-- Name: reports_clean_20120625_hang_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_hang_id ON reports_clean_20120625 USING btree (hang_id);


--
-- TOC entry 3475 (class 1259 OID 82270)
-- Dependencies: 242 2671
-- Name: reports_clean_20120625_os_name; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_os_name ON reports_clean_20120625 USING btree (os_name);


--
-- TOC entry 3476 (class 1259 OID 82271)
-- Dependencies: 242
-- Name: reports_clean_20120625_os_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_os_version_id ON reports_clean_20120625 USING btree (os_version_id);


--
-- TOC entry 3477 (class 1259 OID 82276)
-- Dependencies: 2671 242
-- Name: reports_clean_20120625_process_type; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_process_type ON reports_clean_20120625 USING btree (process_type);


--
-- TOC entry 3478 (class 1259 OID 82269)
-- Dependencies: 242
-- Name: reports_clean_20120625_product_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_product_version_id ON reports_clean_20120625 USING btree (product_version_id);


--
-- TOC entry 3479 (class 1259 OID 82277)
-- Dependencies: 242 2671
-- Name: reports_clean_20120625_release_channel; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_release_channel ON reports_clean_20120625 USING btree (release_channel);


--
-- TOC entry 3480 (class 1259 OID 82266)
-- Dependencies: 242 242 242
-- Name: reports_clean_20120625_sig_prod_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_sig_prod_date ON reports_clean_20120625 USING btree (signature_id, product_version_id, date_processed);


--
-- TOC entry 3481 (class 1259 OID 82272)
-- Dependencies: 242
-- Name: reports_clean_20120625_signature_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120625_signature_id ON reports_clean_20120625 USING btree (signature_id);


--
-- TOC entry 3482 (class 1259 OID 82265)
-- Dependencies: 242
-- Name: reports_clean_20120625_uuid; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE UNIQUE INDEX reports_clean_20120625_uuid ON reports_clean_20120625 USING btree (uuid);


--
-- TOC entry 3484 (class 1259 OID 82863)
-- Dependencies: 244
-- Name: reports_clean_20120702_address_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_address_id ON reports_clean_20120702 USING btree (address_id);


--
-- TOC entry 3485 (class 1259 OID 82857)
-- Dependencies: 244 244 2671
-- Name: reports_clean_20120702_arch_cores; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_arch_cores ON reports_clean_20120702 USING btree (architecture, cores);


--
-- TOC entry 3486 (class 1259 OID 82858)
-- Dependencies: 244
-- Name: reports_clean_20120702_date_processed; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_date_processed ON reports_clean_20120702 USING btree (date_processed);


--
-- TOC entry 3487 (class 1259 OID 82868)
-- Dependencies: 244
-- Name: reports_clean_20120702_domain_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_domain_id ON reports_clean_20120702 USING btree (domain_id);


--
-- TOC entry 3488 (class 1259 OID 82864)
-- Dependencies: 244
-- Name: reports_clean_20120702_flash_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_flash_version_id ON reports_clean_20120702 USING btree (flash_version_id);


--
-- TOC entry 3489 (class 1259 OID 82865)
-- Dependencies: 244
-- Name: reports_clean_20120702_hang_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_hang_id ON reports_clean_20120702 USING btree (hang_id);


--
-- TOC entry 3490 (class 1259 OID 82860)
-- Dependencies: 244 2671
-- Name: reports_clean_20120702_os_name; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_os_name ON reports_clean_20120702 USING btree (os_name);


--
-- TOC entry 3491 (class 1259 OID 82861)
-- Dependencies: 244
-- Name: reports_clean_20120702_os_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_os_version_id ON reports_clean_20120702 USING btree (os_version_id);


--
-- TOC entry 3492 (class 1259 OID 82866)
-- Dependencies: 244 2671
-- Name: reports_clean_20120702_process_type; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_process_type ON reports_clean_20120702 USING btree (process_type);


--
-- TOC entry 3493 (class 1259 OID 82859)
-- Dependencies: 244
-- Name: reports_clean_20120702_product_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_product_version_id ON reports_clean_20120702 USING btree (product_version_id);


--
-- TOC entry 3494 (class 1259 OID 82867)
-- Dependencies: 2671 244
-- Name: reports_clean_20120702_release_channel; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_release_channel ON reports_clean_20120702 USING btree (release_channel);


--
-- TOC entry 3495 (class 1259 OID 82856)
-- Dependencies: 244 244 244
-- Name: reports_clean_20120702_sig_prod_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_sig_prod_date ON reports_clean_20120702 USING btree (signature_id, product_version_id, date_processed);


--
-- TOC entry 3496 (class 1259 OID 82862)
-- Dependencies: 244
-- Name: reports_clean_20120702_signature_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120702_signature_id ON reports_clean_20120702 USING btree (signature_id);


--
-- TOC entry 3497 (class 1259 OID 82855)
-- Dependencies: 244
-- Name: reports_clean_20120702_uuid; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE UNIQUE INDEX reports_clean_20120702_uuid ON reports_clean_20120702 USING btree (uuid);


--
-- TOC entry 3499 (class 1259 OID 83872)
-- Dependencies: 246
-- Name: reports_clean_20120709_address_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_address_id ON reports_clean_20120709 USING btree (address_id);


--
-- TOC entry 3500 (class 1259 OID 83866)
-- Dependencies: 246 246 2671
-- Name: reports_clean_20120709_arch_cores; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_arch_cores ON reports_clean_20120709 USING btree (architecture, cores);


--
-- TOC entry 3501 (class 1259 OID 83867)
-- Dependencies: 246
-- Name: reports_clean_20120709_date_processed; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_date_processed ON reports_clean_20120709 USING btree (date_processed);


--
-- TOC entry 3502 (class 1259 OID 83877)
-- Dependencies: 246
-- Name: reports_clean_20120709_domain_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_domain_id ON reports_clean_20120709 USING btree (domain_id);


--
-- TOC entry 3503 (class 1259 OID 83873)
-- Dependencies: 246
-- Name: reports_clean_20120709_flash_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_flash_version_id ON reports_clean_20120709 USING btree (flash_version_id);


--
-- TOC entry 3504 (class 1259 OID 83874)
-- Dependencies: 246
-- Name: reports_clean_20120709_hang_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_hang_id ON reports_clean_20120709 USING btree (hang_id);


--
-- TOC entry 3505 (class 1259 OID 83869)
-- Dependencies: 246 2671
-- Name: reports_clean_20120709_os_name; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_os_name ON reports_clean_20120709 USING btree (os_name);


--
-- TOC entry 3506 (class 1259 OID 83870)
-- Dependencies: 246
-- Name: reports_clean_20120709_os_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_os_version_id ON reports_clean_20120709 USING btree (os_version_id);


--
-- TOC entry 3507 (class 1259 OID 83875)
-- Dependencies: 246 2671
-- Name: reports_clean_20120709_process_type; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_process_type ON reports_clean_20120709 USING btree (process_type);


--
-- TOC entry 3508 (class 1259 OID 83868)
-- Dependencies: 246
-- Name: reports_clean_20120709_product_version_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_product_version_id ON reports_clean_20120709 USING btree (product_version_id);


--
-- TOC entry 3509 (class 1259 OID 83876)
-- Dependencies: 246 2671
-- Name: reports_clean_20120709_release_channel; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_release_channel ON reports_clean_20120709 USING btree (release_channel);


--
-- TOC entry 3510 (class 1259 OID 83865)
-- Dependencies: 246 246 246
-- Name: reports_clean_20120709_sig_prod_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_sig_prod_date ON reports_clean_20120709 USING btree (signature_id, product_version_id, date_processed);


--
-- TOC entry 3511 (class 1259 OID 83871)
-- Dependencies: 246
-- Name: reports_clean_20120709_signature_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_clean_20120709_signature_id ON reports_clean_20120709 USING btree (signature_id);


--
-- TOC entry 3512 (class 1259 OID 83864)
-- Dependencies: 246
-- Name: reports_clean_20120709_uuid; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE UNIQUE INDEX reports_clean_20120709_uuid ON reports_clean_20120709 USING btree (uuid);


--
-- TOC entry 3432 (class 1259 OID 82021)
-- Dependencies: 223
-- Name: reports_duplicates_leader; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_duplicates_leader ON reports_duplicates USING btree (duplicate_of);


--
-- TOC entry 3435 (class 1259 OID 82022)
-- Dependencies: 223 223
-- Name: reports_duplicates_timestamp; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX reports_duplicates_timestamp ON reports_duplicates USING btree (date_processed, uuid);


--
-- TOC entry 3483 (class 1259 OID 82286)
-- Dependencies: 243
-- Name: reports_user_info_20120625_uuid; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE UNIQUE INDEX reports_user_info_20120625_uuid ON reports_user_info_20120625 USING btree (uuid);


--
-- TOC entry 3498 (class 1259 OID 82876)
-- Dependencies: 245
-- Name: reports_user_info_20120702_uuid; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE UNIQUE INDEX reports_user_info_20120702_uuid ON reports_user_info_20120702 USING btree (uuid);


--
-- TOC entry 3513 (class 1259 OID 83885)
-- Dependencies: 247
-- Name: reports_user_info_20120709_uuid; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE UNIQUE INDEX reports_user_info_20120709_uuid ON reports_user_info_20120709 USING btree (uuid);


--
-- TOC entry 3445 (class 1259 OID 82023)
-- Dependencies: 230
-- Name: signature_products_product_version; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX signature_products_product_version ON signature_products USING btree (product_version_id);


--
-- TOC entry 3456 (class 1259 OID 82024)
-- Dependencies: 236 236
-- Name: tcbs_product_version; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX tcbs_product_version ON tcbs USING btree (product_version_id, report_date);


--
-- TOC entry 3457 (class 1259 OID 82025)
-- Dependencies: 236
-- Name: tcbs_report_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX tcbs_report_date ON tcbs USING btree (report_date);


--
-- TOC entry 3458 (class 1259 OID 82026)
-- Dependencies: 236
-- Name: tcbs_signature; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace: 
--

CREATE INDEX tcbs_signature ON tcbs USING btree (signature_id);


--
-- TOC entry 3556 (class 2620 OID 82037)
-- Dependencies: 366 165
-- Name: crontabber_nodelete; Type: TRIGGER; Schema: public; Owner: breakpad_rw
--

CREATE TRIGGER crontabber_nodelete BEFORE DELETE ON crontabber_state FOR EACH ROW EXECUTE PROCEDURE crontabber_nodelete();


--
-- TOC entry 3557 (class 2620 OID 82038)
-- Dependencies: 367 165
-- Name: crontabber_timestamp; Type: TRIGGER; Schema: public; Owner: breakpad_rw
--

CREATE TRIGGER crontabber_timestamp BEFORE UPDATE ON crontabber_state FOR EACH ROW EXECUTE PROCEDURE crontabber_timestamp();


--
-- TOC entry 3558 (class 2620 OID 82039)
-- Dependencies: 383 201
-- Name: log_priorityjobs; Type: TRIGGER; Schema: public; Owner: breakpad_rw
--

CREATE TRIGGER log_priorityjobs AFTER INSERT ON priorityjobs FOR EACH ROW EXECUTE PROCEDURE log_priorityjobs();


--
-- TOC entry 3559 (class 2620 OID 82040)
-- Dependencies: 431 237
-- Name: transform_rules_insert_order; Type: TRIGGER; Schema: public; Owner: breakpad_rw
--

CREATE TRIGGER transform_rules_insert_order BEFORE INSERT ON transform_rules FOR EACH ROW EXECUTE PROCEDURE transform_rules_insert_order();


--
-- TOC entry 3560 (class 2620 OID 82041)
-- Dependencies: 237 432 237 237
-- Name: transform_rules_update_order; Type: TRIGGER; Schema: public; Owner: breakpad_rw
--

CREATE TRIGGER transform_rules_update_order AFTER UPDATE OF rule_order, category ON transform_rules FOR EACH ROW EXECUTE PROCEDURE transform_rules_update_order();


--
-- TOC entry 3534 (class 2606 OID 82045)
-- Dependencies: 3316 159 158
-- Name: bug_associations_bugs_fk; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY bug_associations
    ADD CONSTRAINT bug_associations_bugs_fk FOREIGN KEY (bug_id) REFERENCES bugs(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 3535 (class 2606 OID 82050)
-- Dependencies: 163 160 3326
-- Name: correlation_addons_correlation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY correlation_addons
    ADD CONSTRAINT correlation_addons_correlation_id_fkey FOREIGN KEY (correlation_id) REFERENCES correlations(correlation_id) ON DELETE CASCADE;


--
-- TOC entry 3536 (class 2606 OID 82055)
-- Dependencies: 163 3326 161
-- Name: correlation_cores_correlation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY correlation_cores
    ADD CONSTRAINT correlation_cores_correlation_id_fkey FOREIGN KEY (correlation_id) REFERENCES correlations(correlation_id) ON DELETE CASCADE;


--
-- TOC entry 3537 (class 2606 OID 82060)
-- Dependencies: 3326 162 163
-- Name: correlation_modules_correlation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY correlation_modules
    ADD CONSTRAINT correlation_modules_correlation_id_fkey FOREIGN KEY (correlation_id) REFERENCES correlations(correlation_id) ON DELETE CASCADE;


--
-- TOC entry 3553 (class 2606 OID 84571)
-- Dependencies: 2549 204 254 3398
-- Name: crash_types_process_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY crash_types
    ADD CONSTRAINT crash_types_process_type_fkey FOREIGN KEY (process_type) REFERENCES process_types(process_type);


--
-- TOC entry 3555 (class 2606 OID 84604)
-- Dependencies: 254 257 3520
-- Name: crashes_by_user_build_crash_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY crashes_by_user_build
    ADD CONSTRAINT crashes_by_user_build_crash_type_id_fkey FOREIGN KEY (crash_type_id) REFERENCES crash_types(crash_type_id);


--
-- TOC entry 3554 (class 2606 OID 84584)
-- Dependencies: 255 3520 254
-- Name: crashes_by_user_crash_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY crashes_by_user
    ADD CONSTRAINT crashes_by_user_crash_type_id_fkey FOREIGN KEY (crash_type_id) REFERENCES crash_types(crash_type_id);


--
-- TOC entry 3540 (class 2606 OID 82065)
-- Dependencies: 3350 173 172
-- Name: email_campaigns_contacts_email_campaigns_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY email_campaigns_contacts
    ADD CONSTRAINT email_campaigns_contacts_email_campaigns_id_fkey FOREIGN KEY (email_campaigns_id) REFERENCES email_campaigns(id);


--
-- TOC entry 3541 (class 2606 OID 82070)
-- Dependencies: 3357 173 175
-- Name: email_campaigns_contacts_email_contacts_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY email_campaigns_contacts
    ADD CONSTRAINT email_campaigns_contacts_email_contacts_id_fkey FOREIGN KEY (email_contacts_id) REFERENCES email_contacts(id);


--
-- TOC entry 3542 (class 2606 OID 82075)
-- Dependencies: 184 3400 205
-- Name: jobs_owner_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_owner_fkey FOREIGN KEY (owner) REFERENCES processors(id) ON DELETE CASCADE;


--
-- TOC entry 3543 (class 2606 OID 82080)
-- Dependencies: 192 2549 3384 193
-- Name: os_name_matches_os_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY os_name_matches
    ADD CONSTRAINT os_name_matches_os_name_fkey FOREIGN KEY (os_name) REFERENCES os_names(os_name);


--
-- TOC entry 3544 (class 2606 OID 82085)
-- Dependencies: 2549 194 193 3384
-- Name: os_versions_os_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY os_versions
    ADD CONSTRAINT os_versions_os_name_fkey FOREIGN KEY (os_name) REFERENCES os_names(os_name);


--
-- TOC entry 3545 (class 2606 OID 82090)
-- Dependencies: 3342 168 209 2549
-- Name: product_productid_map_product_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_productid_map
    ADD CONSTRAINT product_productid_map_product_name_fkey FOREIGN KEY (product_name) REFERENCES products(product_name) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 3538 (class 2606 OID 82095)
-- Dependencies: 3342 168 2549 167
-- Name: product_release_channels_product_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_release_channels
    ADD CONSTRAINT product_release_channels_product_name_fkey FOREIGN KEY (product_name) REFERENCES products(product_name);


--
-- TOC entry 3539 (class 2606 OID 82100)
-- Dependencies: 167 3344 2549 169
-- Name: product_release_channels_release_channel_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_release_channels
    ADD CONSTRAINT product_release_channels_release_channel_fkey FOREIGN KEY (release_channel) REFERENCES release_channels(release_channel);


--
-- TOC entry 3546 (class 2606 OID 82105)
-- Dependencies: 210 156 3309
-- Name: product_version_builds_product_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_version_builds
    ADD CONSTRAINT product_version_builds_product_version_id_fkey FOREIGN KEY (product_version_id) REFERENCES product_versions(product_version_id) ON DELETE CASCADE;


--
-- TOC entry 3532 (class 2606 OID 82110)
-- Dependencies: 2549 3342 156 168
-- Name: product_versions_product_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_versions
    ADD CONSTRAINT product_versions_product_name_fkey FOREIGN KEY (product_name) REFERENCES products(product_name);


--
-- TOC entry 3533 (class 2606 OID 84508)
-- Dependencies: 156 3309 156
-- Name: product_versions_rapid_beta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_versions
    ADD CONSTRAINT product_versions_rapid_beta_id_fkey FOREIGN KEY (rapid_beta_id) REFERENCES product_versions(product_version_id);


--
-- TOC entry 3547 (class 2606 OID 82130)
-- Dependencies: 215 2549 3344 169
-- Name: release_channel_matches_release_channel_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY release_channel_matches
    ADD CONSTRAINT release_channel_matches_release_channel_fkey FOREIGN KEY (release_channel) REFERENCES release_channels(release_channel);


--
-- TOC entry 3549 (class 2606 OID 82140)
-- Dependencies: 2549 168 3342 231
-- Name: signature_products_rollup_product_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY signature_products_rollup
    ADD CONSTRAINT signature_products_rollup_product_name_fkey FOREIGN KEY (product_name) REFERENCES products(product_name);


--
-- TOC entry 3550 (class 2606 OID 82145)
-- Dependencies: 231 3369 181
-- Name: signature_products_rollup_signature_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY signature_products_rollup
    ADD CONSTRAINT signature_products_rollup_signature_id_fkey FOREIGN KEY (signature_id) REFERENCES signatures(signature_id);


--
-- TOC entry 3548 (class 2606 OID 82150)
-- Dependencies: 230 3369 181
-- Name: signature_products_signature_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY signature_products
    ADD CONSTRAINT signature_products_signature_id_fkey FOREIGN KEY (signature_id) REFERENCES signatures(signature_id);


--
-- TOC entry 3551 (class 2606 OID 82155)
-- Dependencies: 2549 236 169 3344
-- Name: tcbs_release_channel_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY tcbs
    ADD CONSTRAINT tcbs_release_channel_fkey FOREIGN KEY (release_channel) REFERENCES release_channels(release_channel);


--
-- TOC entry 3552 (class 2606 OID 82160)
-- Dependencies: 236 3369 181
-- Name: tcbs_signature_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY tcbs
    ADD CONSTRAINT tcbs_signature_id_fkey FOREIGN KEY (signature_id) REFERENCES signatures(signature_id);


--
-- TOC entry 3564 (class 0 OID 0)
-- Dependencies: 7
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- TOC entry 3565 (class 0 OID 0)
-- Dependencies: 518
-- Name: pg_stat_statements_reset(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION pg_stat_statements_reset() FROM PUBLIC;
REVOKE ALL ON FUNCTION pg_stat_statements_reset() FROM postgres;
GRANT ALL ON FUNCTION pg_stat_statements_reset() TO postgres;


--
-- TOC entry 3566 (class 0 OID 0)
-- Dependencies: 152
-- Name: activity_snapshot; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE activity_snapshot FROM PUBLIC;
REVOKE ALL ON TABLE activity_snapshot FROM postgres;
GRANT ALL ON TABLE activity_snapshot TO postgres;
GRANT SELECT ON TABLE activity_snapshot TO breakpad_ro;
GRANT SELECT ON TABLE activity_snapshot TO breakpad;
GRANT ALL ON TABLE activity_snapshot TO monitor;


--
-- TOC entry 3567 (class 0 OID 0)
-- Dependencies: 153
-- Name: addresses; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE addresses FROM PUBLIC;
REVOKE ALL ON TABLE addresses FROM breakpad_rw;
GRANT ALL ON TABLE addresses TO breakpad_rw;
GRANT SELECT ON TABLE addresses TO breakpad_ro;
GRANT SELECT ON TABLE addresses TO breakpad;
GRANT ALL ON TABLE addresses TO monitor;
GRANT SELECT ON TABLE addresses TO analyst;


--
-- TOC entry 3569 (class 0 OID 0)
-- Dependencies: 155
-- Name: bloat; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE bloat FROM PUBLIC;
REVOKE ALL ON TABLE bloat FROM postgres;
GRANT ALL ON TABLE bloat TO postgres;
GRANT SELECT ON TABLE bloat TO monitoring;
GRANT SELECT ON TABLE bloat TO breakpad_ro;
GRANT SELECT ON TABLE bloat TO breakpad;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE bloat TO breakpad_rw;


--
-- TOC entry 3570 (class 0 OID 0)
-- Dependencies: 158
-- Name: bug_associations; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE bug_associations FROM PUBLIC;
REVOKE ALL ON TABLE bug_associations FROM breakpad_rw;
GRANT ALL ON TABLE bug_associations TO breakpad_rw;
GRANT SELECT ON TABLE bug_associations TO monitoring;
GRANT SELECT ON TABLE bug_associations TO breakpad_ro;
GRANT SELECT ON TABLE bug_associations TO breakpad;
GRANT SELECT ON TABLE bug_associations TO analyst;


--
-- TOC entry 3571 (class 0 OID 0)
-- Dependencies: 159
-- Name: bugs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE bugs FROM PUBLIC;
REVOKE ALL ON TABLE bugs FROM breakpad_rw;
GRANT ALL ON TABLE bugs TO breakpad_rw;
GRANT SELECT ON TABLE bugs TO monitoring;
GRANT SELECT ON TABLE bugs TO breakpad_ro;
GRANT SELECT ON TABLE bugs TO breakpad;
GRANT SELECT ON TABLE bugs TO analyst;


--
-- TOC entry 3572 (class 0 OID 0)
-- Dependencies: 160
-- Name: correlation_addons; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE correlation_addons FROM PUBLIC;
REVOKE ALL ON TABLE correlation_addons FROM breakpad_rw;
GRANT ALL ON TABLE correlation_addons TO breakpad_rw;
GRANT SELECT ON TABLE correlation_addons TO breakpad_ro;
GRANT SELECT ON TABLE correlation_addons TO breakpad;
GRANT ALL ON TABLE correlation_addons TO monitor;
GRANT SELECT ON TABLE correlation_addons TO analyst;


--
-- TOC entry 3573 (class 0 OID 0)
-- Dependencies: 161
-- Name: correlation_cores; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE correlation_cores FROM PUBLIC;
REVOKE ALL ON TABLE correlation_cores FROM breakpad_rw;
GRANT ALL ON TABLE correlation_cores TO breakpad_rw;
GRANT SELECT ON TABLE correlation_cores TO breakpad_ro;
GRANT SELECT ON TABLE correlation_cores TO breakpad;
GRANT ALL ON TABLE correlation_cores TO monitor;
GRANT SELECT ON TABLE correlation_cores TO analyst;


--
-- TOC entry 3574 (class 0 OID 0)
-- Dependencies: 162
-- Name: correlation_modules; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE correlation_modules FROM PUBLIC;
REVOKE ALL ON TABLE correlation_modules FROM breakpad_rw;
GRANT ALL ON TABLE correlation_modules TO breakpad_rw;
GRANT SELECT ON TABLE correlation_modules TO breakpad_ro;
GRANT SELECT ON TABLE correlation_modules TO breakpad;
GRANT ALL ON TABLE correlation_modules TO monitor;
GRANT SELECT ON TABLE correlation_modules TO analyst;


--
-- TOC entry 3575 (class 0 OID 0)
-- Dependencies: 163
-- Name: correlations; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE correlations FROM PUBLIC;
REVOKE ALL ON TABLE correlations FROM breakpad_rw;
GRANT ALL ON TABLE correlations TO breakpad_rw;
GRANT SELECT ON TABLE correlations TO breakpad_ro;
GRANT SELECT ON TABLE correlations TO breakpad;
GRANT ALL ON TABLE correlations TO monitor;
GRANT SELECT ON TABLE correlations TO analyst;


--
-- TOC entry 3578 (class 0 OID 0)
-- Dependencies: 193
-- Name: os_names; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE os_names FROM PUBLIC;
REVOKE ALL ON TABLE os_names FROM breakpad_rw;
GRANT ALL ON TABLE os_names TO breakpad_rw;
GRANT SELECT ON TABLE os_names TO breakpad_ro;
GRANT SELECT ON TABLE os_names TO breakpad;
GRANT ALL ON TABLE os_names TO monitor;
GRANT SELECT ON TABLE os_names TO analyst;


--
-- TOC entry 3579 (class 0 OID 0)
-- Dependencies: 167
-- Name: product_release_channels; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_release_channels FROM PUBLIC;
REVOKE ALL ON TABLE product_release_channels FROM breakpad_rw;
GRANT ALL ON TABLE product_release_channels TO breakpad_rw;
GRANT SELECT ON TABLE product_release_channels TO breakpad_ro;
GRANT SELECT ON TABLE product_release_channels TO breakpad;
GRANT ALL ON TABLE product_release_channels TO monitor;
GRANT SELECT ON TABLE product_release_channels TO analyst;


--
-- TOC entry 3580 (class 0 OID 0)
-- Dependencies: 156
-- Name: product_versions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_versions FROM PUBLIC;
REVOKE ALL ON TABLE product_versions FROM breakpad_rw;
GRANT ALL ON TABLE product_versions TO breakpad_rw;
GRANT SELECT ON TABLE product_versions TO breakpad_ro;
GRANT SELECT ON TABLE product_versions TO breakpad;
GRANT ALL ON TABLE product_versions TO monitor;
GRANT SELECT ON TABLE product_versions TO analyst;


--
-- TOC entry 3581 (class 0 OID 0)
-- Dependencies: 165
-- Name: crontabber_state; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE crontabber_state FROM PUBLIC;
REVOKE ALL ON TABLE crontabber_state FROM breakpad_rw;
GRANT ALL ON TABLE crontabber_state TO breakpad_rw;
GRANT SELECT ON TABLE crontabber_state TO breakpad;
GRANT SELECT ON TABLE crontabber_state TO breakpad_ro;
GRANT ALL ON TABLE crontabber_state TO monitor;


--
-- TOC entry 3582 (class 0 OID 0)
-- Dependencies: 166
-- Name: daily_hangs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE daily_hangs FROM PUBLIC;
REVOKE ALL ON TABLE daily_hangs FROM breakpad_rw;
GRANT ALL ON TABLE daily_hangs TO breakpad_rw;
GRANT SELECT ON TABLE daily_hangs TO breakpad_ro;
GRANT SELECT ON TABLE daily_hangs TO breakpad;
GRANT ALL ON TABLE daily_hangs TO monitor;
GRANT SELECT ON TABLE daily_hangs TO analyst;


--
-- TOC entry 3583 (class 0 OID 0)
-- Dependencies: 168
-- Name: products; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE products FROM PUBLIC;
REVOKE ALL ON TABLE products FROM breakpad_rw;
GRANT ALL ON TABLE products TO breakpad_rw;
GRANT SELECT ON TABLE products TO breakpad_ro;
GRANT SELECT ON TABLE products TO breakpad;
GRANT ALL ON TABLE products TO monitor;
GRANT SELECT ON TABLE products TO analyst;


--
-- TOC entry 3584 (class 0 OID 0)
-- Dependencies: 169
-- Name: release_channels; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE release_channels FROM PUBLIC;
REVOKE ALL ON TABLE release_channels FROM breakpad_rw;
GRANT ALL ON TABLE release_channels TO breakpad_rw;
GRANT SELECT ON TABLE release_channels TO breakpad_ro;
GRANT SELECT ON TABLE release_channels TO breakpad;
GRANT ALL ON TABLE release_channels TO monitor;
GRANT SELECT ON TABLE release_channels TO analyst;


--
-- TOC entry 3585 (class 0 OID 0)
-- Dependencies: 170
-- Name: domains; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE domains FROM PUBLIC;
REVOKE ALL ON TABLE domains FROM breakpad_rw;
GRANT ALL ON TABLE domains TO breakpad_rw;
GRANT SELECT ON TABLE domains TO breakpad_ro;
GRANT SELECT ON TABLE domains TO breakpad;
GRANT ALL ON TABLE domains TO monitor;
GRANT SELECT ON TABLE domains TO analyst;


--
-- TOC entry 3587 (class 0 OID 0)
-- Dependencies: 172
-- Name: email_campaigns; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE email_campaigns FROM PUBLIC;
REVOKE ALL ON TABLE email_campaigns FROM breakpad_rw;
GRANT ALL ON TABLE email_campaigns TO breakpad_rw;
GRANT SELECT ON TABLE email_campaigns TO monitoring;
GRANT SELECT ON TABLE email_campaigns TO breakpad_ro;
GRANT SELECT ON TABLE email_campaigns TO breakpad;


--
-- TOC entry 3588 (class 0 OID 0)
-- Dependencies: 173
-- Name: email_campaigns_contacts; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE email_campaigns_contacts FROM PUBLIC;
REVOKE ALL ON TABLE email_campaigns_contacts FROM breakpad_rw;
GRANT ALL ON TABLE email_campaigns_contacts TO breakpad_rw;
GRANT SELECT ON TABLE email_campaigns_contacts TO monitoring;
GRANT SELECT ON TABLE email_campaigns_contacts TO breakpad_ro;
GRANT SELECT ON TABLE email_campaigns_contacts TO breakpad;


--
-- TOC entry 3590 (class 0 OID 0)
-- Dependencies: 174
-- Name: email_campaigns_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE email_campaigns_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE email_campaigns_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE email_campaigns_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE email_campaigns_id_seq TO breakpad;


--
-- TOC entry 3591 (class 0 OID 0)
-- Dependencies: 175
-- Name: email_contacts; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE email_contacts FROM PUBLIC;
REVOKE ALL ON TABLE email_contacts FROM breakpad_rw;
GRANT ALL ON TABLE email_contacts TO breakpad_rw;
GRANT SELECT ON TABLE email_contacts TO monitoring;
GRANT SELECT ON TABLE email_contacts TO breakpad_ro;
GRANT SELECT ON TABLE email_contacts TO breakpad;


--
-- TOC entry 3593 (class 0 OID 0)
-- Dependencies: 176
-- Name: email_contacts_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE email_contacts_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE email_contacts_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE email_contacts_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE email_contacts_id_seq TO breakpad;


--
-- TOC entry 3594 (class 0 OID 0)
-- Dependencies: 177
-- Name: explosiveness; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE explosiveness FROM PUBLIC;
REVOKE ALL ON TABLE explosiveness FROM breakpad_rw;
GRANT ALL ON TABLE explosiveness TO breakpad_rw;
GRANT SELECT ON TABLE explosiveness TO breakpad_ro;
GRANT SELECT ON TABLE explosiveness TO breakpad;
GRANT ALL ON TABLE explosiveness TO monitor;


--
-- TOC entry 3595 (class 0 OID 0)
-- Dependencies: 178
-- Name: extensions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions FROM PUBLIC;
REVOKE ALL ON TABLE extensions FROM breakpad_rw;
GRANT ALL ON TABLE extensions TO breakpad_rw;
GRANT SELECT ON TABLE extensions TO monitoring;
GRANT SELECT ON TABLE extensions TO breakpad_ro;
GRANT SELECT ON TABLE extensions TO breakpad;
GRANT SELECT ON TABLE extensions TO analyst;


--
-- TOC entry 3596 (class 0 OID 0)
-- Dependencies: 179
-- Name: flash_versions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE flash_versions FROM PUBLIC;
REVOKE ALL ON TABLE flash_versions FROM breakpad_rw;
GRANT ALL ON TABLE flash_versions TO breakpad_rw;
GRANT SELECT ON TABLE flash_versions TO breakpad_ro;
GRANT SELECT ON TABLE flash_versions TO breakpad;
GRANT ALL ON TABLE flash_versions TO monitor;
GRANT SELECT ON TABLE flash_versions TO analyst;


--
-- TOC entry 3598 (class 0 OID 0)
-- Dependencies: 181
-- Name: signatures; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signatures FROM PUBLIC;
REVOKE ALL ON TABLE signatures FROM breakpad_rw;
GRANT ALL ON TABLE signatures TO breakpad_rw;
GRANT SELECT ON TABLE signatures TO breakpad_ro;
GRANT SELECT ON TABLE signatures TO breakpad;
GRANT ALL ON TABLE signatures TO monitor;
GRANT SELECT ON TABLE signatures TO analyst;


--
-- TOC entry 3599 (class 0 OID 0)
-- Dependencies: 182
-- Name: hang_report; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE hang_report FROM PUBLIC;
REVOKE ALL ON TABLE hang_report FROM breakpad_rw;
GRANT ALL ON TABLE hang_report TO breakpad_rw;
GRANT SELECT ON TABLE hang_report TO breakpad;
GRANT SELECT ON TABLE hang_report TO breakpad_ro;
GRANT ALL ON TABLE hang_report TO monitor;


--
-- TOC entry 3600 (class 0 OID 0)
-- Dependencies: 183
-- Name: high_load_temp; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE high_load_temp FROM PUBLIC;
REVOKE ALL ON TABLE high_load_temp FROM postgres;
GRANT ALL ON TABLE high_load_temp TO postgres;
GRANT SELECT ON TABLE high_load_temp TO breakpad_ro;
GRANT SELECT ON TABLE high_load_temp TO breakpad;
GRANT ALL ON TABLE high_load_temp TO monitor;


--
-- TOC entry 3601 (class 0 OID 0)
-- Dependencies: 184
-- Name: jobs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE jobs FROM PUBLIC;
REVOKE ALL ON TABLE jobs FROM breakpad_rw;
GRANT ALL ON TABLE jobs TO breakpad_rw;
GRANT SELECT ON TABLE jobs TO monitoring;
GRANT SELECT ON TABLE jobs TO breakpad_ro;
GRANT SELECT ON TABLE jobs TO breakpad;
GRANT SELECT ON TABLE jobs TO analyst;


--
-- TOC entry 3603 (class 0 OID 0)
-- Dependencies: 185
-- Name: jobs_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE jobs_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE jobs_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE jobs_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE jobs_id_seq TO breakpad;


--
-- TOC entry 3604 (class 0 OID 0)
-- Dependencies: 186
-- Name: jobs_in_queue; Type: ACL; Schema: public; Owner: monitoring
--

REVOKE ALL ON TABLE jobs_in_queue FROM PUBLIC;
REVOKE ALL ON TABLE jobs_in_queue FROM monitoring;
GRANT ALL ON TABLE jobs_in_queue TO monitoring;
GRANT SELECT ON TABLE jobs_in_queue TO breakpad_ro;
GRANT SELECT ON TABLE jobs_in_queue TO breakpad;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE jobs_in_queue TO breakpad_rw;


--
-- TOC entry 3605 (class 0 OID 0)
-- Dependencies: 187
-- Name: locks; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE locks FROM PUBLIC;
REVOKE ALL ON TABLE locks FROM postgres;
GRANT ALL ON TABLE locks TO postgres;
GRANT SELECT ON TABLE locks TO breakpad_ro;
GRANT SELECT ON TABLE locks TO breakpad;
GRANT ALL ON TABLE locks TO monitor;


--
-- TOC entry 3606 (class 0 OID 0)
-- Dependencies: 188
-- Name: locks1; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE locks1 FROM PUBLIC;
REVOKE ALL ON TABLE locks1 FROM postgres;
GRANT ALL ON TABLE locks1 TO postgres;
GRANT SELECT ON TABLE locks1 TO breakpad_ro;
GRANT SELECT ON TABLE locks1 TO breakpad;
GRANT ALL ON TABLE locks1 TO monitor;


--
-- TOC entry 3607 (class 0 OID 0)
-- Dependencies: 189
-- Name: locks2; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE locks2 FROM PUBLIC;
REVOKE ALL ON TABLE locks2 FROM postgres;
GRANT ALL ON TABLE locks2 TO postgres;
GRANT SELECT ON TABLE locks2 TO breakpad_ro;
GRANT SELECT ON TABLE locks2 TO breakpad;
GRANT ALL ON TABLE locks2 TO monitor;


--
-- TOC entry 3608 (class 0 OID 0)
-- Dependencies: 190
-- Name: locks3; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE locks3 FROM PUBLIC;
REVOKE ALL ON TABLE locks3 FROM postgres;
GRANT ALL ON TABLE locks3 TO postgres;
GRANT SELECT ON TABLE locks3 TO breakpad_ro;
GRANT SELECT ON TABLE locks3 TO breakpad;
GRANT ALL ON TABLE locks3 TO monitor;


--
-- TOC entry 3609 (class 0 OID 0)
-- Dependencies: 191
-- Name: nightly_builds; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE nightly_builds FROM PUBLIC;
REVOKE ALL ON TABLE nightly_builds FROM breakpad_rw;
GRANT ALL ON TABLE nightly_builds TO breakpad_rw;
GRANT SELECT ON TABLE nightly_builds TO breakpad_ro;
GRANT SELECT ON TABLE nightly_builds TO breakpad;
GRANT ALL ON TABLE nightly_builds TO monitor;


--
-- TOC entry 3610 (class 0 OID 0)
-- Dependencies: 192
-- Name: os_name_matches; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE os_name_matches FROM PUBLIC;
REVOKE ALL ON TABLE os_name_matches FROM breakpad_rw;
GRANT ALL ON TABLE os_name_matches TO breakpad_rw;
GRANT SELECT ON TABLE os_name_matches TO breakpad_ro;
GRANT SELECT ON TABLE os_name_matches TO breakpad;
GRANT ALL ON TABLE os_name_matches TO monitor;


--
-- TOC entry 3611 (class 0 OID 0)
-- Dependencies: 194
-- Name: os_versions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE os_versions FROM PUBLIC;
REVOKE ALL ON TABLE os_versions FROM breakpad_rw;
GRANT ALL ON TABLE os_versions TO breakpad_rw;
GRANT SELECT ON TABLE os_versions TO breakpad_ro;
GRANT SELECT ON TABLE os_versions TO breakpad;
GRANT ALL ON TABLE os_versions TO monitor;
GRANT SELECT ON TABLE os_versions TO analyst;


--
-- TOC entry 3613 (class 0 OID 0)
-- Dependencies: 195
-- Name: os_versions_os_version_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE os_versions_os_version_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE os_versions_os_version_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE os_versions_os_version_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE os_versions_os_version_id_seq TO breakpad;


--
-- TOC entry 3614 (class 0 OID 0)
-- Dependencies: 196
-- Name: performance_check_1; Type: ACL; Schema: public; Owner: ganglia
--

REVOKE ALL ON TABLE performance_check_1 FROM PUBLIC;
REVOKE ALL ON TABLE performance_check_1 FROM ganglia;
GRANT ALL ON TABLE performance_check_1 TO ganglia;
GRANT SELECT ON TABLE performance_check_1 TO breakpad;
GRANT SELECT ON TABLE performance_check_1 TO breakpad_ro;
GRANT ALL ON TABLE performance_check_1 TO monitor;


--
-- TOC entry 3615 (class 0 OID 0)
-- Dependencies: 197
-- Name: pg_stat_statements; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE pg_stat_statements FROM PUBLIC;
REVOKE ALL ON TABLE pg_stat_statements FROM postgres;
GRANT ALL ON TABLE pg_stat_statements TO postgres;
GRANT SELECT ON TABLE pg_stat_statements TO PUBLIC;
GRANT SELECT ON TABLE pg_stat_statements TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE pg_stat_statements TO breakpad_rw;
GRANT SELECT ON TABLE pg_stat_statements TO breakpad;


--
-- TOC entry 3616 (class 0 OID 0)
-- Dependencies: 198
-- Name: plugins; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins FROM PUBLIC;
REVOKE ALL ON TABLE plugins FROM breakpad_rw;
GRANT ALL ON TABLE plugins TO breakpad_rw;
GRANT SELECT ON TABLE plugins TO monitoring;
GRANT SELECT ON TABLE plugins TO breakpad_ro;
GRANT SELECT ON TABLE plugins TO breakpad;
GRANT SELECT ON TABLE plugins TO analyst;


--
-- TOC entry 3618 (class 0 OID 0)
-- Dependencies: 199
-- Name: plugins_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE plugins_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE plugins_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE plugins_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE plugins_id_seq TO breakpad;


--
-- TOC entry 3619 (class 0 OID 0)
-- Dependencies: 200
-- Name: plugins_reports; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports TO monitoring;
GRANT SELECT ON TABLE plugins_reports TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports TO breakpad;
GRANT SELECT ON TABLE plugins_reports TO analyst;


--
-- TOC entry 3620 (class 0 OID 0)
-- Dependencies: 201
-- Name: priorityjobs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE priorityjobs FROM PUBLIC;
REVOKE ALL ON TABLE priorityjobs FROM breakpad_rw;
GRANT ALL ON TABLE priorityjobs TO breakpad_rw;
GRANT SELECT ON TABLE priorityjobs TO monitoring;
GRANT SELECT ON TABLE priorityjobs TO breakpad_ro;
GRANT SELECT ON TABLE priorityjobs TO breakpad;


--
-- TOC entry 3621 (class 0 OID 0)
-- Dependencies: 202
-- Name: priorityjobs_log; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE priorityjobs_log FROM PUBLIC;
REVOKE ALL ON TABLE priorityjobs_log FROM postgres;
GRANT ALL ON TABLE priorityjobs_log TO postgres;
GRANT SELECT ON TABLE priorityjobs_log TO monitoring;
GRANT SELECT ON TABLE priorityjobs_log TO breakpad_ro;
GRANT ALL ON TABLE priorityjobs_log TO breakpad;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE priorityjobs_log TO breakpad_rw;


--
-- TOC entry 3622 (class 0 OID 0)
-- Dependencies: 203
-- Name: priorityjobs_logging_switch; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE priorityjobs_logging_switch FROM PUBLIC;
REVOKE ALL ON TABLE priorityjobs_logging_switch FROM postgres;
GRANT ALL ON TABLE priorityjobs_logging_switch TO postgres;
GRANT SELECT ON TABLE priorityjobs_logging_switch TO monitoring;
GRANT SELECT ON TABLE priorityjobs_logging_switch TO breakpad_ro;
GRANT SELECT ON TABLE priorityjobs_logging_switch TO breakpad;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE priorityjobs_logging_switch TO breakpad_rw;


--
-- TOC entry 3623 (class 0 OID 0)
-- Dependencies: 204
-- Name: process_types; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE process_types FROM PUBLIC;
REVOKE ALL ON TABLE process_types FROM breakpad_rw;
GRANT ALL ON TABLE process_types TO breakpad_rw;
GRANT SELECT ON TABLE process_types TO breakpad_ro;
GRANT SELECT ON TABLE process_types TO breakpad;
GRANT ALL ON TABLE process_types TO monitor;
GRANT SELECT ON TABLE process_types TO analyst;


--
-- TOC entry 3624 (class 0 OID 0)
-- Dependencies: 205
-- Name: processors; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE processors FROM PUBLIC;
REVOKE ALL ON TABLE processors FROM breakpad_rw;
GRANT ALL ON TABLE processors TO breakpad_rw;
GRANT SELECT ON TABLE processors TO monitoring;
GRANT SELECT ON TABLE processors TO breakpad_ro;
GRANT SELECT ON TABLE processors TO breakpad;


--
-- TOC entry 3626 (class 0 OID 0)
-- Dependencies: 206
-- Name: processors_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE processors_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE processors_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE processors_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE processors_id_seq TO breakpad;


--
-- TOC entry 3627 (class 0 OID 0)
-- Dependencies: 207
-- Name: product_adu; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_adu FROM PUBLIC;
REVOKE ALL ON TABLE product_adu FROM breakpad_rw;
GRANT ALL ON TABLE product_adu TO breakpad_rw;
GRANT SELECT ON TABLE product_adu TO breakpad_ro;
GRANT SELECT ON TABLE product_adu TO breakpad;
GRANT ALL ON TABLE product_adu TO monitor;
GRANT SELECT ON TABLE product_adu TO analyst;


--
-- TOC entry 3628 (class 0 OID 0)
-- Dependencies: 263
-- Name: product_crash_ratio; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_crash_ratio FROM PUBLIC;
REVOKE ALL ON TABLE product_crash_ratio FROM breakpad_rw;
GRANT ALL ON TABLE product_crash_ratio TO breakpad_rw;
GRANT SELECT ON TABLE product_crash_ratio TO analyst;


--
-- TOC entry 3629 (class 0 OID 0)
-- Dependencies: 208
-- Name: product_info_changelog; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_info_changelog FROM PUBLIC;
REVOKE ALL ON TABLE product_info_changelog FROM breakpad_rw;
GRANT ALL ON TABLE product_info_changelog TO breakpad_rw;
GRANT SELECT ON TABLE product_info_changelog TO breakpad_ro;
GRANT SELECT ON TABLE product_info_changelog TO breakpad;
GRANT ALL ON TABLE product_info_changelog TO monitor;


--
-- TOC entry 3630 (class 0 OID 0)
-- Dependencies: 264
-- Name: product_os_crash_ratio; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_os_crash_ratio FROM PUBLIC;
REVOKE ALL ON TABLE product_os_crash_ratio FROM breakpad_rw;
GRANT ALL ON TABLE product_os_crash_ratio TO breakpad_rw;
GRANT SELECT ON TABLE product_os_crash_ratio TO analyst;


--
-- TOC entry 3631 (class 0 OID 0)
-- Dependencies: 209
-- Name: product_productid_map; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_productid_map FROM PUBLIC;
REVOKE ALL ON TABLE product_productid_map FROM breakpad_rw;
GRANT ALL ON TABLE product_productid_map TO breakpad_rw;
GRANT SELECT ON TABLE product_productid_map TO breakpad_ro;
GRANT SELECT ON TABLE product_productid_map TO breakpad;
GRANT ALL ON TABLE product_productid_map TO monitor;
GRANT SELECT ON TABLE product_productid_map TO analyst;


--
-- TOC entry 3632 (class 0 OID 0)
-- Dependencies: 210
-- Name: product_version_builds; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_version_builds FROM PUBLIC;
REVOKE ALL ON TABLE product_version_builds FROM breakpad_rw;
GRANT ALL ON TABLE product_version_builds TO breakpad_rw;
GRANT SELECT ON TABLE product_version_builds TO breakpad_ro;
GRANT SELECT ON TABLE product_version_builds TO breakpad;
GRANT ALL ON TABLE product_version_builds TO monitor;
GRANT SELECT ON TABLE product_version_builds TO analyst;


--
-- TOC entry 3634 (class 0 OID 0)
-- Dependencies: 157
-- Name: product_version_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE product_version_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE product_version_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE product_version_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE product_version_id_seq TO breakpad;


--
-- TOC entry 3635 (class 0 OID 0)
-- Dependencies: 211
-- Name: rank_compare; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE rank_compare FROM PUBLIC;
REVOKE ALL ON TABLE rank_compare FROM breakpad_rw;
GRANT ALL ON TABLE rank_compare TO breakpad_rw;
GRANT SELECT ON TABLE rank_compare TO breakpad_ro;
GRANT SELECT ON TABLE rank_compare TO breakpad;
GRANT ALL ON TABLE rank_compare TO monitor;
GRANT SELECT ON TABLE rank_compare TO analyst;


--
-- TOC entry 3636 (class 0 OID 0)
-- Dependencies: 212
-- Name: raw_adu; Type: ACL; Schema: public; Owner: breakpad_metrics
--

REVOKE ALL ON TABLE raw_adu FROM PUBLIC;
REVOKE ALL ON TABLE raw_adu FROM breakpad_metrics;
GRANT ALL ON TABLE raw_adu TO breakpad_metrics;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE raw_adu TO breakpad_rw;
GRANT SELECT ON TABLE raw_adu TO nagiosdaemon;
GRANT SELECT ON TABLE raw_adu TO monitoring;
GRANT SELECT ON TABLE raw_adu TO breakpad_ro;
GRANT SELECT ON TABLE raw_adu TO breakpad;
GRANT SELECT ON TABLE raw_adu TO analyst;


--
-- TOC entry 3637 (class 0 OID 0)
-- Dependencies: 213
-- Name: reasons; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reasons FROM PUBLIC;
REVOKE ALL ON TABLE reasons FROM breakpad_rw;
GRANT ALL ON TABLE reasons TO breakpad_rw;
GRANT SELECT ON TABLE reasons TO breakpad_ro;
GRANT SELECT ON TABLE reasons TO breakpad;
GRANT ALL ON TABLE reasons TO monitor;
GRANT SELECT ON TABLE reasons TO analyst;


--
-- TOC entry 3639 (class 0 OID 0)
-- Dependencies: 215
-- Name: release_channel_matches; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE release_channel_matches FROM PUBLIC;
REVOKE ALL ON TABLE release_channel_matches FROM breakpad_rw;
GRANT ALL ON TABLE release_channel_matches TO breakpad_rw;
GRANT SELECT ON TABLE release_channel_matches TO breakpad_ro;
GRANT SELECT ON TABLE release_channel_matches TO breakpad;
GRANT ALL ON TABLE release_channel_matches TO monitor;


--
-- TOC entry 3640 (class 0 OID 0)
-- Dependencies: 216
-- Name: release_repositories; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE release_repositories FROM PUBLIC;
REVOKE ALL ON TABLE release_repositories FROM breakpad_rw;
GRANT ALL ON TABLE release_repositories TO breakpad_rw;
GRANT SELECT ON TABLE release_repositories TO breakpad_ro;
GRANT SELECT ON TABLE release_repositories TO breakpad;
GRANT ALL ON TABLE release_repositories TO monitor;


--
-- TOC entry 3641 (class 0 OID 0)
-- Dependencies: 217
-- Name: releases_raw; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE releases_raw FROM PUBLIC;
REVOKE ALL ON TABLE releases_raw FROM breakpad_rw;
GRANT ALL ON TABLE releases_raw TO breakpad_rw;
GRANT SELECT ON TABLE releases_raw TO breakpad_ro;
GRANT SELECT ON TABLE releases_raw TO breakpad;
GRANT ALL ON TABLE releases_raw TO monitor;
GRANT SELECT ON TABLE releases_raw TO analyst;


--
-- TOC entry 3642 (class 0 OID 0)
-- Dependencies: 218
-- Name: replication_test; Type: ACL; Schema: public; Owner: monitoring
--

REVOKE ALL ON TABLE replication_test FROM PUBLIC;
REVOKE ALL ON TABLE replication_test FROM monitoring;
GRANT ALL ON TABLE replication_test TO monitoring;
GRANT SELECT ON TABLE replication_test TO breakpad;
GRANT SELECT ON TABLE replication_test TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE replication_test TO breakpad_rw;


--
-- TOC entry 3643 (class 0 OID 0)
-- Dependencies: 219
-- Name: report_partition_info; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE report_partition_info FROM PUBLIC;
REVOKE ALL ON TABLE report_partition_info FROM breakpad_rw;
GRANT ALL ON TABLE report_partition_info TO breakpad_rw;
GRANT SELECT ON TABLE report_partition_info TO breakpad_ro;
GRANT SELECT ON TABLE report_partition_info TO breakpad;
GRANT ALL ON TABLE report_partition_info TO monitor;


--
-- TOC entry 3644 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports FROM PUBLIC;
REVOKE ALL ON TABLE reports FROM breakpad_rw;
GRANT ALL ON TABLE reports TO breakpad_rw;
GRANT SELECT ON TABLE reports TO monitoring;
GRANT SELECT ON TABLE reports TO breakpad_ro;
GRANT SELECT ON TABLE reports TO breakpad;


--
-- TOC entry 3645 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.id; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(id) ON TABLE reports FROM PUBLIC;
REVOKE ALL(id) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(id) ON TABLE reports TO analyst;


--
-- TOC entry 3646 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.client_crash_date; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(client_crash_date) ON TABLE reports FROM PUBLIC;
REVOKE ALL(client_crash_date) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(client_crash_date) ON TABLE reports TO analyst;


--
-- TOC entry 3647 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.date_processed; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(date_processed) ON TABLE reports FROM PUBLIC;
REVOKE ALL(date_processed) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(date_processed) ON TABLE reports TO analyst;


--
-- TOC entry 3648 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.uuid; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(uuid) ON TABLE reports FROM PUBLIC;
REVOKE ALL(uuid) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(uuid) ON TABLE reports TO analyst;


--
-- TOC entry 3649 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.product; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(product) ON TABLE reports FROM PUBLIC;
REVOKE ALL(product) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(product) ON TABLE reports TO analyst;


--
-- TOC entry 3650 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.version; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(version) ON TABLE reports FROM PUBLIC;
REVOKE ALL(version) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(version) ON TABLE reports TO analyst;


--
-- TOC entry 3651 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.build; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(build) ON TABLE reports FROM PUBLIC;
REVOKE ALL(build) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(build) ON TABLE reports TO analyst;


--
-- TOC entry 3652 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.signature; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(signature) ON TABLE reports FROM PUBLIC;
REVOKE ALL(signature) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(signature) ON TABLE reports TO analyst;


--
-- TOC entry 3653 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.install_age; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(install_age) ON TABLE reports FROM PUBLIC;
REVOKE ALL(install_age) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(install_age) ON TABLE reports TO analyst;


--
-- TOC entry 3654 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.last_crash; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(last_crash) ON TABLE reports FROM PUBLIC;
REVOKE ALL(last_crash) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(last_crash) ON TABLE reports TO analyst;


--
-- TOC entry 3655 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.uptime; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(uptime) ON TABLE reports FROM PUBLIC;
REVOKE ALL(uptime) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(uptime) ON TABLE reports TO analyst;


--
-- TOC entry 3656 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.cpu_name; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(cpu_name) ON TABLE reports FROM PUBLIC;
REVOKE ALL(cpu_name) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(cpu_name) ON TABLE reports TO analyst;


--
-- TOC entry 3657 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.cpu_info; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(cpu_info) ON TABLE reports FROM PUBLIC;
REVOKE ALL(cpu_info) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(cpu_info) ON TABLE reports TO analyst;


--
-- TOC entry 3658 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.reason; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(reason) ON TABLE reports FROM PUBLIC;
REVOKE ALL(reason) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(reason) ON TABLE reports TO analyst;


--
-- TOC entry 3659 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.address; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(address) ON TABLE reports FROM PUBLIC;
REVOKE ALL(address) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(address) ON TABLE reports TO analyst;


--
-- TOC entry 3660 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.os_name; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(os_name) ON TABLE reports FROM PUBLIC;
REVOKE ALL(os_name) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(os_name) ON TABLE reports TO analyst;


--
-- TOC entry 3661 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.os_version; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(os_version) ON TABLE reports FROM PUBLIC;
REVOKE ALL(os_version) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(os_version) ON TABLE reports TO analyst;


--
-- TOC entry 3662 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.user_id; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(user_id) ON TABLE reports FROM PUBLIC;
REVOKE ALL(user_id) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(user_id) ON TABLE reports TO analyst;


--
-- TOC entry 3663 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.started_datetime; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(started_datetime) ON TABLE reports FROM PUBLIC;
REVOKE ALL(started_datetime) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(started_datetime) ON TABLE reports TO analyst;


--
-- TOC entry 3664 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.completed_datetime; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(completed_datetime) ON TABLE reports FROM PUBLIC;
REVOKE ALL(completed_datetime) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(completed_datetime) ON TABLE reports TO analyst;


--
-- TOC entry 3665 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.success; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(success) ON TABLE reports FROM PUBLIC;
REVOKE ALL(success) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(success) ON TABLE reports TO analyst;


--
-- TOC entry 3666 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.truncated; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(truncated) ON TABLE reports FROM PUBLIC;
REVOKE ALL(truncated) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(truncated) ON TABLE reports TO analyst;


--
-- TOC entry 3667 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.processor_notes; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(processor_notes) ON TABLE reports FROM PUBLIC;
REVOKE ALL(processor_notes) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(processor_notes) ON TABLE reports TO analyst;


--
-- TOC entry 3668 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.user_comments; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(user_comments) ON TABLE reports FROM PUBLIC;
REVOKE ALL(user_comments) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(user_comments) ON TABLE reports TO analyst;


--
-- TOC entry 3669 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.app_notes; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(app_notes) ON TABLE reports FROM PUBLIC;
REVOKE ALL(app_notes) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(app_notes) ON TABLE reports TO analyst;


--
-- TOC entry 3670 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.distributor; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(distributor) ON TABLE reports FROM PUBLIC;
REVOKE ALL(distributor) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(distributor) ON TABLE reports TO analyst;


--
-- TOC entry 3671 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.distributor_version; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(distributor_version) ON TABLE reports FROM PUBLIC;
REVOKE ALL(distributor_version) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(distributor_version) ON TABLE reports TO analyst;


--
-- TOC entry 3672 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.topmost_filenames; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(topmost_filenames) ON TABLE reports FROM PUBLIC;
REVOKE ALL(topmost_filenames) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(topmost_filenames) ON TABLE reports TO analyst;


--
-- TOC entry 3673 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.addons_checked; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(addons_checked) ON TABLE reports FROM PUBLIC;
REVOKE ALL(addons_checked) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(addons_checked) ON TABLE reports TO analyst;


--
-- TOC entry 3674 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.flash_version; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(flash_version) ON TABLE reports FROM PUBLIC;
REVOKE ALL(flash_version) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(flash_version) ON TABLE reports TO analyst;


--
-- TOC entry 3675 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.hangid; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(hangid) ON TABLE reports FROM PUBLIC;
REVOKE ALL(hangid) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(hangid) ON TABLE reports TO analyst;


--
-- TOC entry 3676 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.process_type; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(process_type) ON TABLE reports FROM PUBLIC;
REVOKE ALL(process_type) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(process_type) ON TABLE reports TO analyst;


--
-- TOC entry 3677 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.release_channel; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(release_channel) ON TABLE reports FROM PUBLIC;
REVOKE ALL(release_channel) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(release_channel) ON TABLE reports TO analyst;


--
-- TOC entry 3678 (class 0 OID 0)
-- Dependencies: 220
-- Name: reports.productid; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(productid) ON TABLE reports FROM PUBLIC;
REVOKE ALL(productid) ON TABLE reports FROM breakpad_rw;
GRANT SELECT(productid) ON TABLE reports TO analyst;


--
-- TOC entry 3679 (class 0 OID 0)
-- Dependencies: 221
-- Name: reports_bad; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_bad FROM PUBLIC;
REVOKE ALL ON TABLE reports_bad FROM breakpad_rw;
GRANT ALL ON TABLE reports_bad TO breakpad_rw;
GRANT SELECT ON TABLE reports_bad TO breakpad_ro;
GRANT SELECT ON TABLE reports_bad TO breakpad;
GRANT ALL ON TABLE reports_bad TO monitor;
GRANT SELECT ON TABLE reports_bad TO analyst;


--
-- TOC entry 3680 (class 0 OID 0)
-- Dependencies: 222
-- Name: reports_clean; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_clean FROM PUBLIC;
REVOKE ALL ON TABLE reports_clean FROM breakpad_rw;
GRANT ALL ON TABLE reports_clean TO breakpad_rw;
GRANT SELECT ON TABLE reports_clean TO breakpad_ro;
GRANT SELECT ON TABLE reports_clean TO breakpad;
GRANT ALL ON TABLE reports_clean TO monitor;
GRANT SELECT ON TABLE reports_clean TO analyst;


--
-- TOC entry 3681 (class 0 OID 0)
-- Dependencies: 223
-- Name: reports_duplicates; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_duplicates FROM PUBLIC;
REVOKE ALL ON TABLE reports_duplicates FROM breakpad_rw;
GRANT ALL ON TABLE reports_duplicates TO breakpad_rw;
GRANT SELECT ON TABLE reports_duplicates TO breakpad_ro;
GRANT SELECT ON TABLE reports_duplicates TO breakpad;
GRANT SELECT ON TABLE reports_duplicates TO analyst;


--
-- TOC entry 3683 (class 0 OID 0)
-- Dependencies: 224
-- Name: reports_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE reports_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE reports_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE reports_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE reports_id_seq TO breakpad;


--
-- TOC entry 3684 (class 0 OID 0)
-- Dependencies: 225
-- Name: reports_user_info; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_user_info FROM PUBLIC;
REVOKE ALL ON TABLE reports_user_info FROM breakpad_rw;
GRANT ALL ON TABLE reports_user_info TO breakpad_rw;
GRANT SELECT ON TABLE reports_user_info TO breakpad_ro;
GRANT SELECT ON TABLE reports_user_info TO breakpad;
GRANT ALL ON TABLE reports_user_info TO monitor;


--
-- TOC entry 3685 (class 0 OID 0)
-- Dependencies: 225
-- Name: reports_user_info.uuid; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(uuid) ON TABLE reports_user_info FROM PUBLIC;
REVOKE ALL(uuid) ON TABLE reports_user_info FROM breakpad_rw;
GRANT SELECT(uuid) ON TABLE reports_user_info TO analyst;


--
-- TOC entry 3686 (class 0 OID 0)
-- Dependencies: 225
-- Name: reports_user_info.date_processed; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(date_processed) ON TABLE reports_user_info FROM PUBLIC;
REVOKE ALL(date_processed) ON TABLE reports_user_info FROM breakpad_rw;
GRANT SELECT(date_processed) ON TABLE reports_user_info TO analyst;


--
-- TOC entry 3687 (class 0 OID 0)
-- Dependencies: 225
-- Name: reports_user_info.user_comments; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(user_comments) ON TABLE reports_user_info FROM PUBLIC;
REVOKE ALL(user_comments) ON TABLE reports_user_info FROM breakpad_rw;
GRANT SELECT(user_comments) ON TABLE reports_user_info TO analyst;


--
-- TOC entry 3688 (class 0 OID 0)
-- Dependencies: 225
-- Name: reports_user_info.app_notes; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL(app_notes) ON TABLE reports_user_info FROM PUBLIC;
REVOKE ALL(app_notes) ON TABLE reports_user_info FROM breakpad_rw;
GRANT SELECT(app_notes) ON TABLE reports_user_info TO analyst;


--
-- TOC entry 3689 (class 0 OID 0)
-- Dependencies: 226
-- Name: seq_reports_id; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE seq_reports_id FROM PUBLIC;
REVOKE ALL ON SEQUENCE seq_reports_id FROM breakpad_rw;
GRANT ALL ON SEQUENCE seq_reports_id TO breakpad_rw;
GRANT SELECT ON SEQUENCE seq_reports_id TO breakpad;


--
-- TOC entry 3690 (class 0 OID 0)
-- Dependencies: 227
-- Name: server_status; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE server_status FROM PUBLIC;
REVOKE ALL ON TABLE server_status FROM breakpad_rw;
GRANT ALL ON TABLE server_status TO breakpad_rw;
GRANT SELECT ON TABLE server_status TO monitoring;
GRANT SELECT ON TABLE server_status TO breakpad_ro;
GRANT SELECT ON TABLE server_status TO breakpad;


--
-- TOC entry 3692 (class 0 OID 0)
-- Dependencies: 228
-- Name: server_status_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE server_status_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE server_status_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE server_status_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE server_status_id_seq TO breakpad;


--
-- TOC entry 3693 (class 0 OID 0)
-- Dependencies: 229
-- Name: sessions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE sessions FROM PUBLIC;
REVOKE ALL ON TABLE sessions FROM breakpad_rw;
GRANT ALL ON TABLE sessions TO breakpad_rw;
GRANT SELECT ON TABLE sessions TO breakpad_ro;
GRANT SELECT ON TABLE sessions TO breakpad;


--
-- TOC entry 3694 (class 0 OID 0)
-- Dependencies: 230
-- Name: signature_products; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signature_products FROM PUBLIC;
REVOKE ALL ON TABLE signature_products FROM breakpad_rw;
GRANT ALL ON TABLE signature_products TO breakpad_rw;
GRANT SELECT ON TABLE signature_products TO breakpad_ro;
GRANT SELECT ON TABLE signature_products TO breakpad;
GRANT ALL ON TABLE signature_products TO monitor;
GRANT SELECT ON TABLE signature_products TO analyst;


--
-- TOC entry 3695 (class 0 OID 0)
-- Dependencies: 231
-- Name: signature_products_rollup; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signature_products_rollup FROM PUBLIC;
REVOKE ALL ON TABLE signature_products_rollup FROM breakpad_rw;
GRANT ALL ON TABLE signature_products_rollup TO breakpad_rw;
GRANT SELECT ON TABLE signature_products_rollup TO breakpad_ro;
GRANT SELECT ON TABLE signature_products_rollup TO breakpad;
GRANT ALL ON TABLE signature_products_rollup TO monitor;
GRANT SELECT ON TABLE signature_products_rollup TO analyst;


--
-- TOC entry 3697 (class 0 OID 0)
-- Dependencies: 232
-- Name: signatures_signature_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE signatures_signature_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE signatures_signature_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE signatures_signature_id_seq TO breakpad_rw;
GRANT SELECT ON SEQUENCE signatures_signature_id_seq TO breakpad;


--
-- TOC entry 3698 (class 0 OID 0)
-- Dependencies: 233
-- Name: socorro_db_version; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE socorro_db_version FROM PUBLIC;
REVOKE ALL ON TABLE socorro_db_version FROM postgres;
GRANT ALL ON TABLE socorro_db_version TO postgres;
GRANT SELECT ON TABLE socorro_db_version TO breakpad_ro;
GRANT SELECT ON TABLE socorro_db_version TO breakpad;
GRANT ALL ON TABLE socorro_db_version TO monitor;
GRANT SELECT ON TABLE socorro_db_version TO analyst;


--
-- TOC entry 3699 (class 0 OID 0)
-- Dependencies: 234
-- Name: socorro_db_version_history; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE socorro_db_version_history FROM PUBLIC;
REVOKE ALL ON TABLE socorro_db_version_history FROM postgres;
GRANT ALL ON TABLE socorro_db_version_history TO postgres;
GRANT SELECT ON TABLE socorro_db_version_history TO breakpad_ro;
GRANT SELECT ON TABLE socorro_db_version_history TO breakpad;
GRANT ALL ON TABLE socorro_db_version_history TO monitor;


--
-- TOC entry 3700 (class 0 OID 0)
-- Dependencies: 235
-- Name: special_product_platforms; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE special_product_platforms FROM PUBLIC;
REVOKE ALL ON TABLE special_product_platforms FROM breakpad_rw;
GRANT ALL ON TABLE special_product_platforms TO breakpad_rw;
GRANT SELECT ON TABLE special_product_platforms TO breakpad_ro;
GRANT SELECT ON TABLE special_product_platforms TO breakpad;
GRANT ALL ON TABLE special_product_platforms TO monitor;
GRANT SELECT ON TABLE special_product_platforms TO analyst;


--
-- TOC entry 3701 (class 0 OID 0)
-- Dependencies: 236
-- Name: tcbs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE tcbs FROM PUBLIC;
REVOKE ALL ON TABLE tcbs FROM breakpad_rw;
GRANT ALL ON TABLE tcbs TO breakpad_rw;
GRANT SELECT ON TABLE tcbs TO breakpad_ro;
GRANT SELECT ON TABLE tcbs TO breakpad;
GRANT ALL ON TABLE tcbs TO monitor;
GRANT SELECT ON TABLE tcbs TO analyst;


--
-- TOC entry 3702 (class 0 OID 0)
-- Dependencies: 237
-- Name: transform_rules; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE transform_rules FROM PUBLIC;
REVOKE ALL ON TABLE transform_rules FROM breakpad_rw;
GRANT ALL ON TABLE transform_rules TO breakpad_rw;
GRANT SELECT ON TABLE transform_rules TO breakpad_ro;
GRANT SELECT ON TABLE transform_rules TO breakpad;
GRANT ALL ON TABLE transform_rules TO monitor;


--
-- TOC entry 3704 (class 0 OID 0)
-- Dependencies: 239
-- Name: uptime_levels; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE uptime_levels FROM PUBLIC;
REVOKE ALL ON TABLE uptime_levels FROM breakpad_rw;
GRANT ALL ON TABLE uptime_levels TO breakpad_rw;
GRANT SELECT ON TABLE uptime_levels TO breakpad_ro;
GRANT SELECT ON TABLE uptime_levels TO breakpad;
GRANT ALL ON TABLE uptime_levels TO monitor;
GRANT SELECT ON TABLE uptime_levels TO analyst;


--
-- TOC entry 3706 (class 0 OID 0)
-- Dependencies: 241
-- Name: windows_versions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE windows_versions FROM PUBLIC;
REVOKE ALL ON TABLE windows_versions FROM breakpad_rw;
GRANT ALL ON TABLE windows_versions TO breakpad_rw;
GRANT SELECT ON TABLE windows_versions TO breakpad_ro;
GRANT SELECT ON TABLE windows_versions TO breakpad;
GRANT ALL ON TABLE windows_versions TO monitor;
GRANT SELECT ON TABLE windows_versions TO analyst;


--
-- TOC entry 2715 (class 826 OID 82183)
-- Dependencies: 7
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES  FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES  FROM postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT ON TABLES  TO breakpad;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES  TO monitor;


-- Completed on 2012-07-25 14:19:19 PDT

--
-- PostgreSQL database dump complete
--

