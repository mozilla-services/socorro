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
-- Name: release_enum; Type: TYPE; Schema: public; Owner: breakpad_rw
--

CREATE TYPE release_enum AS ENUM (
    'major',
    'milestone',
    'development'
);


ALTER TYPE public.release_enum OWNER TO breakpad_rw;

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
-- Name: build_date(numeric); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION build_date(build_id numeric) RETURNS date
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
-- converts build number to a date
SELECT to_date(substr( $1::text, 1, 8 ),'YYYYMMDD');
$_$;


ALTER FUNCTION public.build_date(build_id numeric) OWNER TO postgres;

--
-- Name: build_numeric(character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION build_numeric(character varying) RETURNS numeric
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
-- safely converts a build number to a numeric type
-- if the build is not a number, returns NULL
SELECT CASE WHEN $1 ~ $x$^\d+$$x$ THEN
	$1::numeric
ELSE
	NULL::numeric
END;
$_$;


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
-- Name: daily_crash_code(text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION daily_crash_code(process_type text, hangid text) RETURNS character
    LANGUAGE sql IMMUTABLE
    AS $_$
SELECT CASE
WHEN $1 ILIKE 'content' THEN 'T'
WHEN $1 IS NULL AND $2 IS NULL THEN 'C'
WHEN $1 IS NULL AND $2 IS NOT NULL THEN 'c'
WHEN $1 ILIKE 'plugin' AND $2 IS NULL THEN 'P'
WHEN $1 ILIKE 'plugin' AND $2 IS NOT NULL THEN 'p'
ELSE 'C'
END
$_$;


ALTER FUNCTION public.daily_crash_code(process_type text, hangid text) OWNER TO postgres;

--
-- Name: drop_old_partitions(text, numeric); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION drop_old_partitions(sometable text, cutoffdate numeric) RETURNS boolean
    LANGUAGE plpgsql
    AS $_X$
declare oldpartition text;
begin

EXECUTE 'LOCK TABLE ' || sometable || ' IN ACCESS EXCLUSIVE MODE NOWAIT;';

FOR oldpartition IN EXECUTE $q$SELECT relname FROM pg_stat_user_tables
WHERE relname LIKE '$q$ || sometable || $q$_2%'
AND substring(relname FROM $x$_(\d+)$$x$)::numeric < $q$ || cutoffdate || $q$
ORDER BY relname$q$ LOOP

EXECUTE 'DROP TABLE ' || oldpartition;

RAISE NOTICE 'Dropping table %', oldpartition;

END LOOP;

RETURN TRUE;

EXCEPTION
WHEN lock_not_available THEN
RAISE NOTICE 'Could not lock %', sometable;
RETURN FALSE;
END;
$_X$;


ALTER FUNCTION public.drop_old_partitions(sometable text, cutoffdate numeric) OWNER TO postgres;

--
-- Name: edit_product_info(integer, citext, text, text, date, date, boolean, numeric); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION edit_product_info(prod_id integer, prod_name citext, prod_version text, prod_channel text, begin_visibility date, end_visibility date, is_featured boolean, crash_throttle numeric) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE which_t text;
	new_id INT;

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
	IF FOUND THEN
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


ALTER FUNCTION public.edit_product_info(prod_id integer, prod_name citext, prod_version text, prod_channel text, begin_visibility date, end_visibility date, is_featured boolean, crash_throttle numeric) OWNER TO postgres;

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
    LANGUAGE sql IMMUTABLE STRICT
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
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
-- converts a major_version string into a padded,
-- sortable string
select version_sort_digit( substring($1 from $x$^(\d+)$x$) )
	|| version_sort_digit( substring($1 from $x$^\d+\.(\d+)$x$) );
$_$;


ALTER FUNCTION public.major_version_sort(version text) OWNER TO postgres;

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
-- Name: translate(citext, citext, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION translate(citext, citext, text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
    SELECT pg_catalog.translate( pg_catalog.translate( $1::pg_catalog.text, pg_catalog.lower($2::pg_catalog.text), $3), pg_catalog.upper($2::pg_catalog.text), $3);
$_$;


ALTER FUNCTION public.translate(citext, citext, text) OWNER TO postgres;

--
-- Name: update_adu(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_adu(updateday date) RETURNS boolean
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
	RAISE EXCEPTION 'raw_adu not updated for %',updateday;
END IF;

-- check if ADU has already been run for the date

PERFORM 1 FROM product_adu
WHERE adu_date = updateday LIMIT 1;

IF FOUND THEN
	RAISE EXCEPTION 'update_adu has already been run for %', updateday;
END IF;

-- insert releases

INSERT INTO product_adu ( product_version_id, os_name,
		adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
	updateday,
	coalesce(sum(raw_adu.adu_count), 0)
FROM product_versions
	LEFT OUTER JOIN raw_adu
		ON product_versions.product_name = raw_adu.product_name
		AND product_versions.version_string = raw_adu.product_version
		AND product_versions.build_type ILIKE raw_adu.build_channel
		AND raw_adu.date = updateday
	LEFT OUTER JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'release'
GROUP BY product_version_id, os;

-- insert betas
-- does not include any missing beta counts; should resolve that later

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Windows') as os,
    updateday,
    coalesce(sum(raw_adu.adu_count), 0)
FROM product_versions
    JOIN raw_adu
        ON product_versions.product_name = raw_adu.product_name
        AND product_versions.release_version = raw_adu.product_version
        AND raw_adu.date = updateday
    JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN build_date AND ( sunset_date + 1 )
        AND product_versions.build_type = 'Beta'
        AND raw_adu.build_channel = 'beta'
        AND EXISTS ( SELECT 1
            FROM product_version_builds
            WHERE product_versions.product_version_id = product_version_builds.product_version_id
              AND product_version_builds.build_id = build_numeric(raw_adu.build)
            )
GROUP BY product_version_id, os;

-- insert old products

INSERT INTO product_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT productdims_id, coalesce(os_name,'Windows') as os,
	updateday, coalesce(sum(raw_adu.adu_count),0)
FROM productdims
	JOIN product_visibility ON productdims.id = product_visibility.productdims_id
	LEFT OUTER JOIN raw_adu
		ON productdims.product = raw_adu.product_name
		AND productdims.version = raw_adu.product_version
		AND raw_adu.date = updateday
    LEFT OUTER JOIN os_name_matches
    	ON raw_adu.product_os_platform ILIKE os_name_matches.match_string
WHERE updateday BETWEEN ( start_date - interval '1 day' )
	AND ( end_date + interval '1 day' )
GROUP BY productdims_id, os;

RETURN TRUE;
END; $$;


ALTER FUNCTION public.update_adu(updateday date) OWNER TO postgres;

--
-- Name: update_daily_crashes(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_daily_crashes(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
BEGIN
-- update the old daily crashes  yes, this is horrible
-- stuff, but until we overhaul the home page graph
-- we will continue to use it

-- apologies for badly written SQL, didn't want to rewrite it all from scratch

-- note: we are currently excluding crashes which are missing an OS_Name from the count

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
	date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
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
				date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
				AND updateday BETWEEN cfg.start_date and cfg.end_date
				AND hangid IS NOT NULL
                AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

-- insert crash counts for new products
-- non-beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code,
	product_versions.product_version_id,
	substring(os_name, 1, 3) AS os_short_name,
	updateday
FROM product_versions
JOIN reports on product_versions.product_name = reports.product
	AND product_versions.version_string = reports.version
WHERE
	date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
    AND ( lower(release_channel) NOT IN ( 'nightly', 'beta', 'aurora' )
        OR release_channel IS NULL )
	AND updateday BETWEEN product_versions.build_date and sunset_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
AND product_versions.build_type <> 'beta'
GROUP BY product_version_id, crash_code, os_short_name;

-- insert crash counts for new products
-- betas
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT COUNT(*) as count, daily_crash_code(process_type, hangid) as crash_code,
	product_versions.product_version_id,
	substring(os_name, 1, 3) AS os_short_name,
	updateday
FROM product_versions
JOIN reports on product_versions.product_name = reports.product
	AND product_versions.release_version = reports.version
WHERE date_processed >= utc_day_begins_pacific(updateday)
		AND date_processed < utc_day_ends_pacific(updateday)
    AND release_channel ILIKE 'beta'
	AND updateday BETWEEN product_versions.build_date and sunset_date
    AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
    AND EXISTS (SELECT 1
        FROM product_version_builds
        WHERE product_versions.product_version_id = product_version_builds.product_version_id
          AND product_version_builds.build_id = build_numeric(reports.build) )
AND product_versions.build_type = 'beta'
GROUP BY product_version_id, crash_code, os_short_name;

-- insert normalized hangs for new products
-- non-beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, product_version_id AS prod_id, substring(os_name, 1, 3) AS os_short_name
			FROM product_versions
			JOIN reports on product_versions.product_name = reports.product
				AND product_versions.version_string = reports.version
			WHERE date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
                AND ( lower(release_channel) NOT IN ( 'nightly', 'beta', 'aurora' )
                      or release_channel is null )
				AND updateday BETWEEN product_versions.build_date and sunset_date
			AND product_versions.build_type <> 'beta'
            AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

-- insert normalized hangs for new products
-- beta
INSERT INTO daily_crashes (count, report_type, productdims_id, os_short_name, adu_day)
SELECT count(subr.hangid) as count, 'H', subr.prod_id, subr.os_short_name,
	 updateday
FROM (
		   SELECT distinct hangid, product_version_id AS prod_id, substring(os_name, 1, 3) AS os_short_name
			FROM product_versions
			JOIN reports on product_versions.product_name = reports.product
				AND product_versions.release_version = reports.version
			WHERE date_processed >= utc_day_begins_pacific(updateday)
					AND date_processed < utc_day_ends_pacific(updateday)
                AND release_channel ILIKE 'beta'
				AND updateday BETWEEN product_versions.build_date and sunset_date
                AND EXISTS (SELECT 1
                    FROM product_version_builds
                    WHERE product_versions.product_version_id = product_version_builds.product_version_id
                      AND product_version_builds.build_id = build_numeric(reports.build) )
			AND product_versions.build_type = 'beta'
            AND lower(substring(os_name, 1, 3)) IN ('win','lin','mac')
		 ) AS subr
GROUP BY subr.prod_id, subr.os_short_name;

ANALYZE daily_crashes;

RETURN TRUE;

END;$$;


ALTER FUNCTION public.update_daily_crashes(updateday date) OWNER TO postgres;

--
-- Name: update_final_betas(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_final_betas(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $_$
BEGIN
-- this function adds "final" beta releases to the list of
-- products from the reports table
-- since the first time we see them would be in the
-- reports table

-- create a temporary table including all builds found

create temporary table orphan_betas
on commit drop as
select build_numeric(build) as build_id,
  version, product, os_name,
  count(*) as report_count
from reports
where date_processed BETWEEN utc_day_begins_pacific(updateday)
  AND utc_day_ends_pacific(updateday)
  AND release_channel = 'beta'
  and os_name <> ''
  and build ~ $x$^20\d{12}$$x$
  and version !~ $x$[a-zA-Z]$x$
group by build, version, product, os_name;

-- insert release versions into the betas

INSERT INTO orphan_betas
SELECT build_id, release_version, product_name, platform
FROM product_versions JOIN product_version_builds
  USING (product_version_id)
WHERE build_type = 'release';

-- purge all builds we've already seen

DELETE FROM orphan_betas
USING product_versions JOIN product_version_builds
  USING (product_version_id)
WHERE orphan_betas.product = product_versions.product_name
  AND orphan_betas.version = product_versions.release_version
  AND orphan_betas.build_id = product_version_builds.build_id
  AND product_versions.build_type <> 'release';

-- purge builds which are lower than an existing beta

DELETE FROM orphan_betas
USING product_versions JOIN product_version_builds
  USING (product_version_id)
WHERE orphan_betas.product = product_versions.product_name
  AND orphan_betas.version = product_versions.release_version
  AND orphan_betas.build_id < ( product_version_builds.build_id)
  AND product_versions.beta_number between 1 and 998
  AND product_versions.build_type = 'beta';

-- purge builds which are higher than a release

DELETE FROM orphan_betas
USING product_versions JOIN product_version_builds
  USING (product_version_id)
WHERE orphan_betas.product = product_versions.product_name
  AND orphan_betas.version = product_versions.release_version
  AND orphan_betas.build_id > ( product_version_builds.build_id + 2000000 )
  AND product_versions.build_type = 'release';

-- purge unused versions

DELETE FROM orphan_betas
WHERE product NOT IN (SELECT product_name
    FROM products
    WHERE major_version_sort(orphan_betas.version)
      >= major_version_sort(products.rapid_release_version) );

-- if no bfinal exists in product_versions, then create one

INSERT INTO product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type)
SELECT product,
  major_version(version),
  version,
  version || '(beta)',
  999,
  version_sort(version, 999),
  build_date(min(orphan_betas.build_id)),
  sunset_date(min(orphan_betas.build_id), 'beta'),
  'Beta'
FROM orphan_betas
  JOIN products ON orphan_betas.product = products.product_name
  LEFT OUTER JOIN product_versions
    ON orphan_betas.product = product_versions.product_name
    AND orphan_betas.version = product_versions.release_version
    AND product_versions.beta_number = 999
WHERE product_versions.product_name IS NULL
GROUP BY product, version;

-- add the buildids to product_version_builds
INSERT INTO product_version_builds (product_version_id, build_id, platform)
SELECT product_version_id, orphan_betas.build_id, os_name
FROM product_versions JOIN orphan_betas
  ON product_name = product
  AND product_versions.release_version = orphan_betas.version
WHERE beta_number = 999;

RETURN TRUE;

END; $_$;


ALTER FUNCTION public.update_final_betas(updateday date) OWNER TO postgres;

--
-- Name: update_os_versions(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_os_versions(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $_$
BEGIN
-- function for daily batch update of os_version information
-- pulls new data out of reports
-- errors if no data found

create temporary table new_os
on commit drop as
select os_name, os_version
from reports
where date_processed >= utc_day_begins_pacific(updateday)
	and date_processed <= utc_day_begins_pacific((updateday + 1))
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

insert into os_versions ( os_name, major_version, minor_version )
select os_name, major_version, minor_version
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
-- currently we are only adding releases and betas

insert into product_versions (
    product_name,
    major_version,
    release_version,
    version_string,
    beta_number,
    version_sort,
    build_date,
    sunset_date,
    build_type)
select products.product_name,
major_version(version),
version,
version_string(version, releases_raw.beta_number),
releases_raw.beta_number,
version_sort(version, releases_raw.beta_number),
build_date(min(build_id)),
sunset_date(min(build_id), releases_raw.build_type ),
releases_raw.build_type
from releases_raw
join products ON releases_raw.product_name = products.release_name
left outer join product_versions ON
( releases_raw.product_name = products.release_name
AND releases_raw.version = product_versions.release_version
AND releases_raw.beta_number IS NOT DISTINCT FROM product_versions.beta_number )
where major_version_sort(version) >= major_version_sort(rapid_release_version)
AND product_versions.product_name IS NULL
AND releases_raw.build_type IN ('release','beta')
group by products.product_name, version, releases_raw.beta_number, releases_raw.build_type;

insert into product_version_builds
select product_versions.product_version_id,
releases_raw.build_id,
releases_raw.platform
from releases_raw
    join products
        ON products.release_name = releases_raw.product_name
join product_versions
ON products.product_name = product_versions.product_name
AND releases_raw.version = product_versions.release_version
AND releases_raw.beta_number IS NOT DISTINCT FROM product_versions.beta_number
left outer join product_version_builds ON
product_versions.product_version_id = product_version_builds.product_version_id
AND releases_raw.build_id = product_version_builds.build_id
where product_version_builds.product_version_id is null;

return true;
end; $$;


ALTER FUNCTION public.update_product_versions() OWNER TO postgres;

--
-- Name: update_reports_duplicates(timestamp without time zone, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_reports_duplicates(start_time timestamp without time zone, end_time timestamp without time zone) RETURNS integer
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
	left outer join reports_duplicates USING (uuid)
where reports_duplicates.uuid IS NULL;

-- done return number of dups found and exit
RETURN new_dups;
end;$$;


ALTER FUNCTION public.update_reports_duplicates(start_time timestamp without time zone, end_time timestamp without time zone) OWNER TO postgres;

--
-- Name: update_signature_matviews(timestamp without time zone, integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_signature_matviews(currenttime timestamp without time zone, hours_back integer, hours_window integer) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN

-- this omnibus function is designed to be called by cron once per hour.
-- it updates all of the signature matviews: signature_productdims, signature_build,
-- and signature_first

-- create a temporary table of recent new reports

create temporary table signature_build_updates
on commit drop
as select signature, null::int as productdims_id, product::citext as product, version::citext as version, os_name::citext as os_name, build, min(date_processed) as first_report
from reports
where date_processed <= ( currenttime - ( interval '1 hour' * hours_back ) )
and date_processed > ( currenttime - ( interval '1 hour' * hours_back ) - (interval '1 hour' * hours_window ) )
and signature is not null
and product is not null
and version is not null
group by signature, product, version, os_name, build
order by signature, product, version, os_name, build;

-- update productdims column in signature_build

update signature_build_updates set productdims_id = productdims.id
from productdims
where productdims.product = signature_build_updates.product
and productdims.version = signature_build_updates.version;

-- remove any garbage rows

DELETE FROM signature_build_updates
WHERE productdims_id IS NULL
OR os_name IS NULL
OR build IS NULL;

-- insert new rows into signature_build

insert into signature_build (
signature, product, version, productdims_id, os_name, build, first_report )
select sbup.signature, sbup.product, sbup.version, sbup.productdims_id,
sbup.os_name, sbup.build, sbup.first_report
from signature_build_updates sbup
left outer join signature_build
using ( signature, product, version, os_name, build )
where signature_build.signature IS NULL;

-- add new rows to signature_productdims

insert into signature_productdims ( signature, productdims_id, first_report )
select newsigs.signature, newsigs.productdims_id, newsigs.first_report
from (
select signature, productdims_id, min(first_report) as first_report
from signature_build_updates
join productdims USING (product, version)
group by signature, productdims_id
order by signature, productdims_id
) as newsigs
left outer join signature_productdims oldsigs
using ( signature, productdims_id )
where oldsigs.signature IS NULL;

-- add new rows to signature_first

insert into signature_first (signature, productdims_id, osdims_id,
first_report, first_build )
select sbup.signature, sbup.productdims_id, osdims.id, min(sbup.first_report),
min(sbup.build)
from signature_build_updates sbup
join top_crashes_by_signature tcbs on
sbup.signature = tcbs.signature
and sbup.productdims_id = tcbs.productdims_id
join osdims ON tcbs.osdims_id = osdims.id
left outer join signature_first sfirst
on sbup.signature = sfirst.signature
and sbup.productdims_id = sfirst.productdims_id
and tcbs.osdims_id = sfirst.osdims_id
where sbup.os_name = osdims.os_name
and tcbs.window_end BETWEEN
( currenttime - ( interval '1 hour' * hours_back ) - (interval '1 hour' * hours_window ) )
AND ( currenttime - ( interval '1 hour' * hours_back ) )
and sfirst.signature IS NULL
group by sbup.signature, sbup.productdims_id, osdims.id;


RETURN TRUE;
END;
$$;


ALTER FUNCTION public.update_signature_matviews(currenttime timestamp without time zone, hours_back integer, hours_window integer) OWNER TO postgres;

--
-- Name: update_signatures(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_signatures(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
BEGIN

-- new function for updating signature information post-rapid-release
-- designed to be run once per UTC day.
-- running it repeatedly won't cause issues
-- combines NULL and empty signatures

-- create temporary table

create temporary table new_signatures
on commit drop as
select coalesce(signature,'') as signature, product, version, build, NULL::INT as product_version_id,
	min(date_processed) as first_report
from reports
where date_processed >= utc_day_begins_pacific(updateday)
	and date_processed <= utc_day_begins_pacific((updateday + 1))
group by signature, product, version, build;

PERFORM 1 FROM new_signatures;
IF NOT FOUND THEN
	RAISE EXCEPTION 'no signature data found in reports for date %',updateday;
END IF;

analyze new_signatures;

-- add product IDs
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
	and product_versions.build_type = 'release'
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

analyze signature_products_rollup;

-- recreate signature_bugs from scratch

DELETE FROM signature_bugs_rollup;

INSERT INTO signature_bugs_rollup (signature_id, bug_count, bug_list)
SELECT signature_id, count(*), array_accum(bug_id)
FROM signatures JOIN bug_associations USING (signature)
GROUP BY signature_id;

analyze signature_bugs_rollup;

return true;
end;
$$;


ALTER FUNCTION public.update_signatures(updateday date) OWNER TO postgres;

--
-- Name: update_tcbs(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION update_tcbs(updateday date) RETURNS boolean
    LANGUAGE plpgsql
    SET work_mem TO '512MB'
    SET temp_buffers TO '512MB'
    AS $$
BEGIN
-- this procedure goes throught the daily TCBS update for the
-- new TCBS table
-- designed to be run only once for each day
-- attempts to run it a second time will error
-- needs to be run last after most other updates

-- check that it hasn't already been run

PERFORM 1 FROM tcbs
WHERE report_date = updateday LIMIT 1;
IF FOUND THEN
	RAISE EXCEPTION 'TCBS has already been run for the day %.',updateday;
END IF;

-- create a temporary table

CREATE TEMPORARY TABLE new_tcbs
ON COMMIT DROP AS
SELECT signature, product, version, build,
	release_channel, os_name, os_version,
	process_type, count(*) as report_count,
	0::int as product_version_id,
	0::int as signature_id,
	null::citext as real_release_channel,
    SUM(case when hangid is not null then 1 else 0 end) as hang_count
FROM reports
WHERE date_processed >= utc_day_begins_pacific(updateday)
	and date_processed <= utc_day_begins_pacific((updateday + 1))
GROUP BY signature, product, version, build,
	release_channel, os_name, os_version,
	process_type;

PERFORM 1 FROM new_tcbs LIMIT 1;
IF NOT FOUND THEN
	RAISE EXCEPTION 'no report data found for TCBS for date %', updateday;
END IF;

ANALYZE new_tcbs;

-- clean process_type

UPDATE new_tcbs
SET process_type = 'Browser'
WHERE process_type IS NULL
	OR process_type = '';

-- clean release_channel

UPDATE new_tcbs
SET real_release_channel = release_channels.release_channel
FROM release_channels
	JOIN release_channel_matches ON
		release_channels.release_channel = release_channel_matches.release_channel
WHERE new_tcbs.release_channel ILIKE match_string;

UPDATE new_tcbs SET real_release_channel = 'Release'
WHERE real_release_channel IS NULL;

-- populate signature_id

UPDATE new_tcbs SET signature_id = signatures.signature_id
FROM signatures
WHERE COALESCE(new_tcbs.signature,'') = signatures.signature;

-- populate product_version_id for betas

UPDATE new_tcbs
SET product_version_id = product_versions.product_version_id
FROM product_versions
	JOIN product_version_builds ON product_versions.product_version_id = product_version_builds.product_version_id
WHERE product_versions.build_type = 'Beta'
    AND new_tcbs.real_release_channel = 'Beta'
	AND new_tcbs.product = product_versions.product_name
	AND new_tcbs.version = product_versions.release_version
	AND build_numeric(new_tcbs.build) = product_version_builds.build_id;

-- populate product_version_id for other builds

UPDATE new_tcbs
SET product_version_id = product_versions.product_version_id
FROM product_versions
WHERE product_versions.build_type <> 'Beta'
    AND new_tcbs.real_release_channel <> 'Beta'
	AND new_tcbs.product = product_versions.product_name
	AND new_tcbs.version = product_versions.release_version
	AND new_tcbs.product_version_id = 0;

-- if there's no product and version still, or no
-- signature, discard
-- since we can't report on it

DELETE FROM new_tcbs WHERE product_version_id = 0
  OR signature_id = 0;

-- fix os_name

UPDATE new_tcbs SET os_name = os_name_matches.os_name
FROM os_name_matches
WHERE new_tcbs.os_name ILIKE match_string;

-- populate the matview

INSERT INTO tcbs (
	signature_id, report_date, product_version_id,
	process_type, release_channel,
	report_count, win_count, mac_count, lin_count, hang_count
)
SELECT signature_id, updateday, product_version_id,
	process_type, real_release_channel,
	sum(report_count),
	sum(case when os_name = 'Windows' THEN report_count else 0 END),
	sum(case when os_name = 'Mac OS X' THEN report_count else 0 END),
	sum(case when os_name = 'Linux' THEN report_count else 0 END),
    sum(hang_count)
FROM new_tcbs
GROUP BY signature_id, updateday, product_version_id,
	process_type, real_release_channel;

ANALYZE tcbs;

-- update tcbs_ranking based on tcbs
-- this fills in per day for four aggregation levels

-- all crashes

INSERT INTO tcbs_ranking (
	product_version_id, signature_id,
	process_type, release_channel,
	aggregation_level,
	total_reports, rank_report_count )
SELECT product_version_id, signature_id,
	NULL, NULL,
	'All',
	sum(report_count) over () as total_count,
	dense_rank() over (order by report_count desc) as tcbs_rank
FROM (
	SELECT product_version_id, signature_id,
	sum(report_count) as report_count
	FROM tcbs
	WHERE report_date = updateday
	GROUP BY product_version_id, signature_id
) as tcbs_r;

-- group by process_type

INSERT INTO tcbs_ranking (
	product_version_id, signature_id,
	process_type, release_channel,
	aggregation_level,
	total_reports, rank_report_count )
SELECT product_version_id, signature_id,
	process_type, NULL,
	'process_type',
	sum(report_count) over () as total_count,
	dense_rank() over (order by report_count desc) as tcbs_rank
FROM (
	SELECT product_version_id, signature_id,
	process_type,
	sum(report_count) as report_count
	FROM tcbs
	WHERE report_date = updateday
	GROUP BY product_version_id, signature_id, process_type
) as tcbs_r;

-- group by release_channel

INSERT INTO tcbs_ranking (
	product_version_id, signature_id,
	process_type, release_channel,
	aggregation_level,
	total_reports, rank_report_count )
SELECT product_version_id, signature_id,
	NULL, release_channel,
	'All',
	sum(report_count) over () as total_count,
	dense_rank() over (order by report_count desc) as tcbs_rank
FROM (
	SELECT product_version_id, signature_id, release_channel,
	sum(report_count) as report_count
	FROM tcbs
	WHERE report_date = updateday
	GROUP BY product_version_id, signature_id, release_channel
) as tcbs_r;

-- group by process_type and release_channel

INSERT INTO tcbs_ranking (
	product_version_id, signature_id,
	process_type, release_channel,
	aggregation_level,
	total_reports, rank_report_count )
SELECT product_version_id, signature_id,
	NULL, NULL,
	'All',
	sum(report_count) over () as total_count,
	dense_rank() over (order by report_count desc) as tcbs_rank
FROM (
	SELECT product_version_id, signature_id,
		process_type, release_channel,
	sum(report_count) as report_count
	FROM tcbs
	WHERE report_date = updateday
	GROUP BY product_version_id, signature_id,
		process_type, release_channel
) as tcbs_r;

-- done
RETURN TRUE;
END;
$$;


ALTER FUNCTION public.update_tcbs(updateday date) OWNER TO postgres;

--
-- Name: utc_day_begins_pacific(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION utc_day_begins_pacific(date) RETURNS timestamp without time zone
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
-- does the tricky date math of converting a UTC date
-- into a Pacfic timestamp without time zone
-- for the beginning of the day
SELECT $1::timestamp without time zone at time zone 'Etc/UTC' at time zone 'America/Los_Angeles';
$_$;


ALTER FUNCTION public.utc_day_begins_pacific(date) OWNER TO postgres;

--
-- Name: utc_day_ends_pacific(date); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION utc_day_ends_pacific(date) RETURNS timestamp without time zone
    LANGUAGE sql IMMUTABLE STRICT
    AS $_$
-- does the tricky date math of converting a UTC date
-- into a Pacfic timestamp without time zone
-- for the end of the day
SELECT ( $1::timestamp without time zone at time zone 'Etc/UTC' at time zone 'America/Los_Angeles' ) + interval '1 day'
$_$;


ALTER FUNCTION public.utc_day_ends_pacific(date) OWNER TO postgres;

--
-- Name: version_number_elements(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_number_elements(version_string text) RETURNS text[]
    LANGUAGE sql IMMUTABLE
    AS $_$
-- breaks up the parts of a version string
-- into an array of elements
select regexp_matches($1,$x$^(\d+)\.(\d+)([a-zA-Z]?)(\d*)\.?(\d*)$x$);
$_$;


ALTER FUNCTION public.version_number_elements(version_string text) OWNER TO postgres;

--
-- Name: version_number_elements(text, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_number_elements(version text, beta_number integer) RETURNS text[]
    LANGUAGE sql
    AS $_$
-- breaks up the parts of a version string into an
-- array of elements.  if a beta number is present
-- includes that
select case when $2 <> 0 then
	   regexp_matches($1,$x$^(\d+)\.(\d+)$x$) || ARRAY [ 'b', $2::text, '' ]
    else
       regexp_matches($1,$x$^(\d+)\.(\d+)([a-zA-Z]?)(\d*)\.?(\d*)$x$)
    end;
$_$;


ALTER FUNCTION public.version_number_elements(version text, beta_number integer) OWNER TO postgres;

--
-- Name: version_sort(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_sort(version_string text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts a version string into a padded
-- sortable string
select version_sort_digit(vne[1])
	|| version_sort_digit(vne[2])
	|| CASE WHEN vne[3] = '' THEN 'z' ELSE vne[3] END
	|| version_sort_digit(vne[4])
	|| version_sort_digit(vne[5])
from ( select version_number_elements($1) as vne ) as vne;
$_$;


ALTER FUNCTION public.version_sort(version_string text) OWNER TO postgres;

--
-- Name: version_sort(text, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_sort(version text, beta_number integer) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
-- converts a version string with a beta number
-- into a padded
-- sortable string
select version_sort_digit(vne[1])
	|| version_sort_digit(vne[2])
	|| CASE WHEN vne[3] = '' THEN 'z' ELSE vne[3] END
	|| version_sort_digit(vne[4])
	|| version_sort_digit(vne[5])
from ( select version_number_elements($1, $2) as vne ) as vne;
$_$;


ALTER FUNCTION public.version_sort(version text, beta_number integer) OWNER TO postgres;

--
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
-- Name: version_sort_insert_trigger(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION version_sort_insert_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
-- updates productdims_version_sort and adds a sort_key
-- for sorting, renumbering all products-versions if
-- required

-- add new sort record
INSERT INTO productdims_version_sort (
id,
product,
version,
sec1_num1,sec1_string1,sec1_num2,sec1_string2,
sec2_num1,sec2_string1,sec2_num2,sec2_string2,
sec3_num1,sec3_string1,sec3_num2,sec3_string2,
extra )
SELECT
NEW.id,
NEW.product,
NEW.version,
s1n1,s1s1,s1n2,s1s2,
s2n1,s2s1,s2n2,s2s2,
s3n1,s3s1,s3n2,s3s2,
ext
FROM tokenize_version(NEW.version);

-- update sort key
PERFORM product_version_sort_number(NEW.product);

RETURN NEW;
END; $$;


ALTER FUNCTION public.version_sort_insert_trigger() OWNER TO postgres;

--
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
-- Name: array_accum(anyelement); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE array_accum(anyelement) (
    SFUNC = array_append,
    STYPE = anyarray,
    INITCOND = '{}'
);


ALTER AGGREGATE public.array_accum(anyelement) OWNER TO postgres;

--
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
-- Name: max(citext); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE max(citext) (
    SFUNC = citext_larger,
    STYPE = citext,
    SORTOP = >
);


ALTER AGGREGATE public.max(citext) OWNER TO postgres;

--
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
-- Name: min(citext); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE min(citext) (
    SFUNC = citext_smaller,
    STYPE = citext,
    SORTOP = <
);


ALTER AGGREGATE public.min(citext) OWNER TO postgres;

--
-- Name: plugin_count(citext, integer); Type: AGGREGATE; Schema: public; Owner: postgres
--

CREATE AGGREGATE plugin_count(citext, integer) (
    SFUNC = plugin_count_state,
    STYPE = integer,
    INITCOND = '0'
);


ALTER AGGREGATE public.plugin_count(citext, integer) OWNER TO postgres;

--
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
-- Name: citext_ops; Type: OPERATOR CLASS; Schema: public; Owner: postgres
--

CREATE OPERATOR CLASS citext_ops
    DEFAULT FOR TYPE citext USING hash AS
    OPERATOR 1 =(citext,citext) ,
    FUNCTION 1 citext_hash(citext);


ALTER OPERATOR CLASS public.citext_ops USING hash OWNER TO postgres;

SET search_path = pg_catalog;

--
-- Name: CAST (boolean AS public.citext); Type: CAST; Schema: pg_catalog; Owner:
--

CREATE CAST (boolean AS public.citext) WITH FUNCTION public.citext(boolean) AS ASSIGNMENT;


--
-- Name: CAST (character AS public.citext); Type: CAST; Schema: pg_catalog; Owner:
--

CREATE CAST (character AS public.citext) WITH FUNCTION public.citext(character) AS ASSIGNMENT;


--
-- Name: CAST (public.citext AS character); Type: CAST; Schema: pg_catalog; Owner:
--

CREATE CAST (public.citext AS character) WITHOUT FUNCTION AS ASSIGNMENT;


--
-- Name: CAST (public.citext AS text); Type: CAST; Schema: pg_catalog; Owner:
--

CREATE CAST (public.citext AS text) WITHOUT FUNCTION AS IMPLICIT;


--
-- Name: CAST (public.citext AS character varying); Type: CAST; Schema: pg_catalog; Owner:
--

CREATE CAST (public.citext AS character varying) WITHOUT FUNCTION AS IMPLICIT;


--
-- Name: CAST (inet AS public.citext); Type: CAST; Schema: pg_catalog; Owner:
--

CREATE CAST (inet AS public.citext) WITH FUNCTION public.citext(inet) AS ASSIGNMENT;


--
-- Name: CAST (text AS public.citext); Type: CAST; Schema: pg_catalog; Owner:
--

CREATE CAST (text AS public.citext) WITHOUT FUNCTION AS ASSIGNMENT;


--
-- Name: CAST (character varying AS public.citext); Type: CAST; Schema: pg_catalog; Owner:
--

CREATE CAST (character varying AS public.citext) WITHOUT FUNCTION AS ASSIGNMENT;


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: alexa_topsites; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE alexa_topsites (
    domain text NOT NULL,
    rank integer DEFAULT 10000,
    last_updated timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.alexa_topsites OWNER TO breakpad_rw;

--
-- Name: backfill_temp; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE backfill_temp (
    uuid text,
    release_channel citext
);


ALTER TABLE public.backfill_temp OWNER TO postgres;

--
-- Name: bloat; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW bloat AS
    SELECT sml.schemaname, sml.tablename, (sml.reltuples)::bigint AS reltuples, (sml.relpages)::bigint AS relpages, sml.otta, round(CASE WHEN (sml.otta = (0)::double precision) THEN 0.0 ELSE ((sml.relpages)::numeric / (sml.otta)::numeric) END, 1) AS tbloat, (((sml.relpages)::bigint)::double precision - sml.otta) AS wastedpages, (sml.bs * ((((sml.relpages)::double precision - sml.otta))::bigint)::numeric) AS wastedbytes, pg_size_pretty((((sml.bs)::double precision * ((sml.relpages)::double precision - sml.otta)))::bigint) AS wastedsize, sml.iname, (sml.ituples)::bigint AS ituples, (sml.ipages)::bigint AS ipages, sml.iotta, round(CASE WHEN ((sml.iotta = (0)::double precision) OR (sml.ipages = 0)) THEN 0.0 ELSE ((sml.ipages)::numeric / (sml.iotta)::numeric) END, 1) AS ibloat, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN (0)::double precision ELSE (((sml.ipages)::bigint)::double precision - sml.iotta) END AS wastedipages, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN (0)::double precision ELSE ((sml.bs)::double precision * ((sml.ipages)::double precision - sml.iotta)) END AS wastedibytes, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN pg_size_pretty((0)::bigint) ELSE pg_size_pretty((((sml.bs)::double precision * ((sml.ipages)::double precision - sml.iotta)))::bigint) END AS wastedisize FROM (SELECT rs.schemaname, rs.tablename, cc.reltuples, cc.relpages, rs.bs, ceil(((cc.reltuples * (((((rs.datahdr + (rs.ma)::numeric) - CASE WHEN ((rs.datahdr % (rs.ma)::numeric) = (0)::numeric) THEN (rs.ma)::numeric ELSE (rs.datahdr % (rs.ma)::numeric) END))::double precision + rs.nullhdr2) + (4)::double precision)) / ((rs.bs)::double precision - (20)::double precision))) AS otta, COALESCE(c2.relname, '?'::name) AS iname, COALESCE(c2.reltuples, (0)::real) AS ituples, COALESCE(c2.relpages, 0) AS ipages, COALESCE(ceil(((c2.reltuples * ((rs.datahdr - (12)::numeric))::double precision) / ((rs.bs)::double precision - (20)::double precision))), (0)::double precision) AS iotta FROM (((((SELECT foo.ma, foo.bs, foo.schemaname, foo.tablename, ((foo.datawidth + (((foo.hdr + foo.ma) - CASE WHEN ((foo.hdr % foo.ma) = 0) THEN foo.ma ELSE (foo.hdr % foo.ma) END))::double precision))::numeric AS datahdr, (foo.maxfracsum * (((foo.nullhdr + foo.ma) - CASE WHEN ((foo.nullhdr % (foo.ma)::bigint) = 0) THEN (foo.ma)::bigint ELSE (foo.nullhdr % (foo.ma)::bigint) END))::double precision) AS nullhdr2 FROM (SELECT s.schemaname, s.tablename, constants.hdr, constants.ma, constants.bs, sum((((1)::double precision - s.null_frac) * (s.avg_width)::double precision)) AS datawidth, max(s.null_frac) AS maxfracsum, (constants.hdr + (SELECT (1 + (count(*) / 8)) FROM pg_stats s2 WHERE (((s2.null_frac <> (0)::double precision) AND (s2.schemaname = s.schemaname)) AND (s2.tablename = s.tablename)))) AS nullhdr FROM pg_stats s, (SELECT (SELECT (current_setting('block_size'::text))::numeric AS current_setting) AS bs, CASE WHEN ("substring"(foo.v, 12, 3) = ANY (ARRAY['8.0'::text, '8.1'::text, '8.2'::text])) THEN 27 ELSE 23 END AS hdr, CASE WHEN (foo.v ~ 'mingw32'::text) THEN 8 ELSE 4 END AS ma FROM (SELECT version() AS v) foo) constants GROUP BY s.schemaname, s.tablename, constants.hdr, constants.ma, constants.bs) foo) rs JOIN pg_class cc ON ((cc.relname = rs.tablename))) JOIN pg_namespace nn ON (((cc.relnamespace = nn.oid) AND (nn.nspname = rs.schemaname)))) LEFT JOIN pg_index i ON ((i.indrelid = cc.oid))) LEFT JOIN pg_class c2 ON ((c2.oid = i.indexrelid)))) sml WHERE ((((sml.relpages)::double precision - sml.otta) > (0)::double precision) OR (((sml.ipages)::double precision - sml.iotta) > (10)::double precision)) ORDER BY (sml.bs * ((((sml.relpages)::double precision - sml.otta))::bigint)::numeric) DESC, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN (0)::double precision ELSE ((sml.bs)::double precision * ((sml.ipages)::double precision - sml.iotta)) END DESC;


ALTER TABLE public.bloat OWNER TO postgres;

--
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
    build_type citext DEFAULT 'release'::citext NOT NULL
);


ALTER TABLE public.product_versions OWNER TO breakpad_rw;

--
-- Name: productdims_id_seq1; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE productdims_id_seq1
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.productdims_id_seq1 OWNER TO breakpad_rw;

--
-- Name: productdims_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE productdims_id_seq1 OWNED BY product_versions.product_version_id;


--
-- Name: productdims; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE productdims (
    id integer DEFAULT nextval('productdims_id_seq1'::regclass) NOT NULL,
    product citext NOT NULL,
    version citext NOT NULL,
    branch text NOT NULL,
    release release_enum,
    sort_key integer
);


ALTER TABLE public.productdims OWNER TO breakpad_rw;

--
-- Name: branches; Type: VIEW; Schema: public; Owner: breakpad_rw
--

CREATE VIEW branches AS
    SELECT productdims.product, productdims.version, productdims.branch FROM productdims;


ALTER TABLE public.branches OWNER TO breakpad_rw;

--
-- Name: bug_associations; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE bug_associations (
    signature text NOT NULL,
    bug_id integer NOT NULL
);


ALTER TABLE public.bug_associations OWNER TO breakpad_rw;

--
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
-- Name: builds; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE builds (
    product citext,
    version citext,
    platform citext,
    buildid bigint,
    platform_changeset text,
    filename text,
    date timestamp without time zone DEFAULT now(),
    app_changeset_1 text,
    app_changeset_2 text
);


ALTER TABLE public.builds OWNER TO breakpad_rw;

--
-- Name: cronjobs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE cronjobs (
    cronjob text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    frequency interval,
    lag interval,
    last_success timestamp with time zone,
    last_target_time timestamp with time zone,
    last_failure timestamp with time zone,
    failure_message text,
    description text
);


ALTER TABLE public.cronjobs OWNER TO breakpad_rw;

--
-- Name: daily_crash_codes; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE daily_crash_codes (
    crash_code character(1) NOT NULL,
    crash_type citext
);


ALTER TABLE public.daily_crash_codes OWNER TO breakpad_rw;

--
-- Name: daily_crashes; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE daily_crashes (
    id integer NOT NULL,
    count integer DEFAULT 0 NOT NULL,
    report_type character(1) DEFAULT 'C'::bpchar NOT NULL,
    productdims_id integer,
    os_short_name character(3),
    adu_day timestamp without time zone NOT NULL
);


ALTER TABLE public.daily_crashes OWNER TO breakpad_rw;

--
-- Name: daily_crashes_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE daily_crashes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.daily_crashes_id_seq OWNER TO breakpad_rw;

--
-- Name: daily_crashes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE daily_crashes_id_seq OWNED BY daily_crashes.id;


--
-- Name: drop_fks; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE drop_fks (
    relname text,
    conname text,
    referencing text,
    condef text
);


ALTER TABLE public.drop_fks OWNER TO postgres;

--
-- Name: email_campaigns; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE email_campaigns (
    id integer NOT NULL,
    product text NOT NULL,
    versions text NOT NULL,
    signature text NOT NULL,
    subject text NOT NULL,
    body text NOT NULL,
    start_date timestamp without time zone NOT NULL,
    end_date timestamp without time zone NOT NULL,
    email_count integer DEFAULT 0,
    author text NOT NULL,
    date_created timestamp without time zone DEFAULT now() NOT NULL,
    status text DEFAULT 'stopped'::text NOT NULL
);


ALTER TABLE public.email_campaigns OWNER TO breakpad_rw;

--
-- Name: email_campaigns_contacts; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE email_campaigns_contacts (
    email_campaigns_id integer,
    email_contacts_id integer,
    status text DEFAULT 'stopped'::text NOT NULL
);


ALTER TABLE public.email_campaigns_contacts OWNER TO breakpad_rw;

--
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
-- Name: email_campaigns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE email_campaigns_id_seq OWNED BY email_campaigns.id;


--
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
-- Name: email_contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE email_contacts_id_seq OWNED BY email_contacts.id;


--
-- Name: extensions; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions (
    report_id integer NOT NULL,
    date_processed timestamp without time zone,
    extension_key integer NOT NULL,
    extension_id text NOT NULL,
    extension_version text
);


ALTER TABLE public.extensions OWNER TO breakpad_rw;

--
-- Name: extensions_20100607; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100607 (
    CONSTRAINT extensions_20100607_date_check CHECK ((('2010-06-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-14 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100607 OWNER TO breakpad_rw;

--
-- Name: extensions_20100614; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100614 (
    CONSTRAINT extensions_20100614_date_check CHECK ((('2010-06-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-21 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100614 OWNER TO breakpad_rw;

--
-- Name: extensions_20100621; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100621 (
    CONSTRAINT extensions_20100621_date_check CHECK ((('2010-06-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-28 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100621 OWNER TO breakpad_rw;

--
-- Name: extensions_20100628; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100628 (
    CONSTRAINT extensions_20100628_date_check CHECK ((('2010-06-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-05 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100628 OWNER TO breakpad_rw;

--
-- Name: extensions_20100705; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100705 (
    CONSTRAINT extensions_20100705_date_check CHECK ((('2010-07-05 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-12 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100705 OWNER TO breakpad_rw;

--
-- Name: extensions_20100712; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100712 (
    CONSTRAINT extensions_20100712_date_check CHECK ((('2010-07-12 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-19 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100712 OWNER TO breakpad_rw;

--
-- Name: extensions_20100719; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100719 (
    CONSTRAINT extensions_20100719_date_check CHECK ((('2010-07-19 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-26 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100719 OWNER TO breakpad_rw;

--
-- Name: extensions_20100726; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100726 (
    CONSTRAINT extensions_20100726_date_check CHECK ((('2010-07-26 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-02 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100726 OWNER TO breakpad_rw;

--
-- Name: extensions_20100802; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100802 (
    CONSTRAINT extensions_20100802_date_check CHECK ((('2010-08-02 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-09 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100802 OWNER TO breakpad_rw;

--
-- Name: extensions_20100809; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100809 (
    CONSTRAINT extensions_20100809_date_check CHECK ((('2010-08-09 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-16 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100809 OWNER TO breakpad_rw;

--
-- Name: extensions_20100816; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100816 (
    CONSTRAINT extensions_20100816_date_check CHECK ((('2010-08-16 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-23 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100816 OWNER TO breakpad_rw;

--
-- Name: extensions_20100823; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100823 (
    CONSTRAINT extensions_20100823_date_check CHECK ((('2010-08-23 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-30 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100823 OWNER TO breakpad_rw;

--
-- Name: extensions_20100830; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100830 (
    CONSTRAINT extensions_20100830_date_check CHECK ((('2010-08-30 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-06 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100830 OWNER TO breakpad_rw;

--
-- Name: extensions_20100906; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100906 (
    CONSTRAINT extensions_20100906_date_check CHECK ((('2010-09-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-13 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100906 OWNER TO breakpad_rw;

--
-- Name: extensions_20100913; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100913 (
    CONSTRAINT extensions_20100913_date_check CHECK ((('2010-09-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-20 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100913 OWNER TO breakpad_rw;

--
-- Name: extensions_20100920; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100920 (
    CONSTRAINT extensions_20100920_date_check CHECK ((('2010-09-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-27 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100920 OWNER TO breakpad_rw;

--
-- Name: extensions_20100927; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20100927 (
    CONSTRAINT extensions_20100927_date_check CHECK ((('2010-09-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-04 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20100927 OWNER TO breakpad_rw;

--
-- Name: extensions_20101004; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101004 (
    CONSTRAINT extensions_20101004_date_check CHECK ((('2010-10-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-11 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101004 OWNER TO breakpad_rw;

--
-- Name: extensions_20101011; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101011 (
    CONSTRAINT extensions_20101011_date_check CHECK ((('2010-10-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-18 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101011 OWNER TO breakpad_rw;

--
-- Name: extensions_20101018; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101018 (
    CONSTRAINT extensions_20101018_date_check CHECK ((('2010-10-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-25 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101018 OWNER TO breakpad_rw;

--
-- Name: extensions_20101025; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101025 (
    CONSTRAINT extensions_20101025_date_check CHECK ((('2010-10-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-01 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101025 OWNER TO breakpad_rw;

--
-- Name: extensions_20101101; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101101 (
    CONSTRAINT extensions_20101101_date_check CHECK ((('2010-11-01 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-08 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101101 OWNER TO breakpad_rw;

--
-- Name: extensions_20101108; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101108 (
    CONSTRAINT extensions_20101108_date_check CHECK ((('2010-11-08 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-15 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101108 OWNER TO breakpad_rw;

--
-- Name: extensions_20101115; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101115 (
    CONSTRAINT extensions_20101115_date_check CHECK ((('2010-11-15 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-22 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101115 OWNER TO breakpad_rw;

--
-- Name: extensions_20101122; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101122 (
    CONSTRAINT extensions_20101122_date_check CHECK ((('2010-11-22 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-29 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101122 OWNER TO breakpad_rw;

--
-- Name: extensions_20101129; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101129 (
    CONSTRAINT extensions_20101129_date_check CHECK ((('2010-11-29 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-06 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101129 OWNER TO breakpad_rw;

--
-- Name: extensions_20101206; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101206 (
    CONSTRAINT extensions_20101206_date_check CHECK ((('2010-12-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-13 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101206 OWNER TO breakpad_rw;

--
-- Name: extensions_20101213; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101213 (
    CONSTRAINT extensions_20101213_date_check CHECK ((('2010-12-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-20 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101213 OWNER TO breakpad_rw;

--
-- Name: extensions_20101220; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101220 (
    CONSTRAINT extensions_20101220_date_check CHECK ((('2010-12-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-27 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101220 OWNER TO breakpad_rw;

--
-- Name: extensions_20101227; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20101227 (
    CONSTRAINT extensions_20101227_date_check CHECK ((('2010-12-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-03 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20101227 OWNER TO breakpad_rw;

--
-- Name: extensions_20110103; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110103 (
    CONSTRAINT extensions_20110103_date_check CHECK ((('2011-01-03 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-10 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110103 OWNER TO breakpad_rw;

--
-- Name: extensions_20110110; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110110 (
    CONSTRAINT extensions_20110110_date_check CHECK ((('2011-01-10 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-17 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110110 OWNER TO breakpad_rw;

--
-- Name: extensions_20110117; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110117 (
    CONSTRAINT extensions_20110117_date_check CHECK ((('2011-01-17 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-24 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110117 OWNER TO breakpad_rw;

--
-- Name: extensions_20110124; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110124 (
    CONSTRAINT extensions_20110124_date_check CHECK ((('2011-01-24 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-31 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110124 OWNER TO breakpad_rw;

--
-- Name: extensions_20110131; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110131 (
    CONSTRAINT extensions_20110131_date_check CHECK ((('2011-01-31 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-07 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110131 OWNER TO breakpad_rw;

--
-- Name: extensions_20110207; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110207 (
    CONSTRAINT extensions_20110207_date_check CHECK ((('2011-02-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-14 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110207 OWNER TO breakpad_rw;

--
-- Name: extensions_20110214; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110214 (
    CONSTRAINT extensions_20110214_date_check CHECK ((('2011-02-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-21 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110214 OWNER TO breakpad_rw;

--
-- Name: extensions_20110221; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110221 (
    CONSTRAINT extensions_20110221_date_check CHECK ((('2011-02-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-28 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110221 OWNER TO breakpad_rw;

--
-- Name: extensions_20110228; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110228 (
    CONSTRAINT extensions_20110228_date_check CHECK ((('2011-02-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-07 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110228 OWNER TO breakpad_rw;

--
-- Name: extensions_20110307; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110307 (
    CONSTRAINT extensions_20110307_date_check CHECK ((('2011-03-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-14 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110307 OWNER TO breakpad_rw;

--
-- Name: extensions_20110314; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110314 (
    CONSTRAINT extensions_20110314_date_check CHECK ((('2011-03-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-21 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110314 OWNER TO breakpad_rw;

--
-- Name: extensions_20110321; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110321 (
    CONSTRAINT extensions_20110321_date_check CHECK ((('2011-03-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-28 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110321 OWNER TO breakpad_rw;

--
-- Name: extensions_20110328; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110328 (
    CONSTRAINT extensions_20110328_date_check CHECK ((('2011-03-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-04 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110328 OWNER TO breakpad_rw;

--
-- Name: extensions_20110404; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110404 (
    CONSTRAINT extensions_20110404_date_check CHECK ((('2011-04-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-11 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110404 OWNER TO breakpad_rw;

--
-- Name: extensions_20110411; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110411 (
    CONSTRAINT extensions_20110411_date_check CHECK ((('2011-04-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-18 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110411 OWNER TO breakpad_rw;

--
-- Name: extensions_20110418; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110418 (
    CONSTRAINT extensions_20110418_date_check CHECK ((('2011-04-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-25 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110418 OWNER TO breakpad_rw;

--
-- Name: extensions_20110425; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110425 (
    CONSTRAINT extensions_20110425_date_check CHECK ((('2011-04-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-02 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110425 OWNER TO breakpad_rw;

--
-- Name: extensions_20110502; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110502 (
    CONSTRAINT extensions_20110502_date_check CHECK ((('2011-05-02 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-09 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110502 OWNER TO breakpad_rw;

--
-- Name: extensions_20110509; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110509 (
    CONSTRAINT extensions_20110509_date_check CHECK ((('2011-05-09 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-16 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110509 OWNER TO breakpad_rw;

--
-- Name: extensions_20110516; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110516 (
    CONSTRAINT extensions_20110516_date_check CHECK ((('2011-05-16 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-23 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110516 OWNER TO breakpad_rw;

--
-- Name: extensions_20110523; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110523 (
    CONSTRAINT extensions_20110523_date_check CHECK ((('2011-05-23 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-30 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110523 OWNER TO breakpad_rw;

--
-- Name: extensions_20110530; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110530 (
    CONSTRAINT extensions_20110530_date_check CHECK ((('2011-05-30 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-06 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110530 OWNER TO breakpad_rw;

--
-- Name: extensions_20110606; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110606 (
    CONSTRAINT extensions_20110606_date_check CHECK ((('2011-06-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-13 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110606 OWNER TO breakpad_rw;

--
-- Name: extensions_20110613; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110613 (
    CONSTRAINT extensions_20110613_date_check CHECK ((('2011-06-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-20 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110613 OWNER TO breakpad_rw;

--
-- Name: extensions_20110620; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110620 (
    CONSTRAINT extensions_20110620_date_check CHECK ((('2011-06-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-27 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110620 OWNER TO breakpad_rw;

--
-- Name: extensions_20110627; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110627 (
    CONSTRAINT extensions_20110627_date_check CHECK ((('2011-06-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-04 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110627 OWNER TO breakpad_rw;

--
-- Name: extensions_20110704; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110704 (
    CONSTRAINT extensions_20110704_date_check CHECK ((('2011-07-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-11 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110704 OWNER TO breakpad_rw;

--
-- Name: extensions_20110711; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110711 (
    CONSTRAINT extensions_20110711_date_check CHECK ((('2011-07-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-18 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110711 OWNER TO breakpad_rw;

--
-- Name: extensions_20110718; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110718 (
    CONSTRAINT extensions_20110718_date_check CHECK ((('2011-07-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-25 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110718 OWNER TO breakpad_rw;

--
-- Name: extensions_20110725; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110725 (
    CONSTRAINT extensions_20110725_date_check CHECK ((('2011-07-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-01 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110725 OWNER TO breakpad_rw;

--
-- Name: extensions_20110801; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110801 (
    CONSTRAINT extensions_20110801_date_check CHECK ((('2011-08-01 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-08 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110801 OWNER TO breakpad_rw;

--
-- Name: extensions_20110808; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110808 (
    CONSTRAINT extensions_20110808_date_check CHECK ((('2011-08-08 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-15 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110808 OWNER TO breakpad_rw;

--
-- Name: extensions_20110815; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110815 (
    CONSTRAINT extensions_20110815_date_check CHECK ((('2011-08-15 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-22 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110815 OWNER TO breakpad_rw;

--
-- Name: extensions_20110822; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110822 (
    CONSTRAINT extensions_20110822_date_check CHECK ((('2011-08-22 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-29 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110822 OWNER TO breakpad_rw;

--
-- Name: extensions_20110829; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110829 (
    CONSTRAINT extensions_20110829_date_check CHECK ((('2011-08-29 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-09-05 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110829 OWNER TO breakpad_rw;

--
-- Name: extensions_20110905; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions_20110905 (
    CONSTRAINT extensions_20110905_date_check CHECK ((('2011-09-05 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-09-12 00:00:00'::timestamp without time zone)))
)
INHERITS (extensions);


ALTER TABLE public.extensions_20110905 OWNER TO breakpad_rw;

--
-- Name: frames; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames (
    report_id integer NOT NULL,
    date_processed timestamp without time zone,
    frame_num integer NOT NULL,
    signature character varying(255)
);


ALTER TABLE public.frames OWNER TO breakpad_rw;

--
-- Name: frames_20100607; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100607 (
    CONSTRAINT frames_20100607_date_check CHECK ((('2010-06-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-14 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100607 OWNER TO breakpad_rw;

--
-- Name: frames_20100614; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100614 (
    CONSTRAINT frames_20100614_date_check CHECK ((('2010-06-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-21 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100614 OWNER TO breakpad_rw;

--
-- Name: frames_20100621; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100621 (
    CONSTRAINT frames_20100621_date_check CHECK ((('2010-06-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-28 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100621 OWNER TO breakpad_rw;

--
-- Name: frames_20100628; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100628 (
    CONSTRAINT frames_20100628_date_check CHECK ((('2010-06-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-05 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100628 OWNER TO breakpad_rw;

--
-- Name: frames_20100705; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100705 (
    CONSTRAINT frames_20100705_date_check CHECK ((('2010-07-05 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-12 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100705 OWNER TO breakpad_rw;

--
-- Name: frames_20100712; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100712 (
    CONSTRAINT frames_20100712_date_check CHECK ((('2010-07-12 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-19 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100712 OWNER TO breakpad_rw;

--
-- Name: frames_20100719; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100719 (
    CONSTRAINT frames_20100719_date_check CHECK ((('2010-07-19 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-26 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100719 OWNER TO breakpad_rw;

--
-- Name: frames_20100726; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100726 (
    CONSTRAINT frames_20100726_date_check CHECK ((('2010-07-26 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-02 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100726 OWNER TO breakpad_rw;

--
-- Name: frames_20100802; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100802 (
    CONSTRAINT frames_20100802_date_check CHECK ((('2010-08-02 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-09 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100802 OWNER TO breakpad_rw;

--
-- Name: frames_20100809; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100809 (
    CONSTRAINT frames_20100809_date_check CHECK ((('2010-08-09 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-16 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100809 OWNER TO breakpad_rw;

--
-- Name: frames_20100816; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100816 (
    CONSTRAINT frames_20100816_date_check CHECK ((('2010-08-16 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-23 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100816 OWNER TO breakpad_rw;

--
-- Name: frames_20100823; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100823 (
    CONSTRAINT frames_20100823_date_check CHECK ((('2010-08-23 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-30 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100823 OWNER TO breakpad_rw;

--
-- Name: frames_20100830; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100830 (
    CONSTRAINT frames_20100830_date_check CHECK ((('2010-08-30 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-06 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100830 OWNER TO breakpad_rw;

--
-- Name: frames_20100906; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100906 (
    CONSTRAINT frames_20100906_date_check CHECK ((('2010-09-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-13 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100906 OWNER TO breakpad_rw;

--
-- Name: frames_20100913; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100913 (
    CONSTRAINT frames_20100913_date_check CHECK ((('2010-09-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-20 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100913 OWNER TO breakpad_rw;

--
-- Name: frames_20100920; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100920 (
    CONSTRAINT frames_20100920_date_check CHECK ((('2010-09-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-27 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100920 OWNER TO breakpad_rw;

--
-- Name: frames_20100927; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20100927 (
    CONSTRAINT frames_20100927_date_check CHECK ((('2010-09-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-04 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20100927 OWNER TO breakpad_rw;

--
-- Name: frames_20101004; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101004 (
    CONSTRAINT frames_20101004_date_check CHECK ((('2010-10-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-11 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101004 OWNER TO breakpad_rw;

--
-- Name: frames_20101011; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101011 (
    CONSTRAINT frames_20101011_date_check CHECK ((('2010-10-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-18 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101011 OWNER TO breakpad_rw;

--
-- Name: frames_20101018; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101018 (
    CONSTRAINT frames_20101018_date_check CHECK ((('2010-10-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-25 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101018 OWNER TO breakpad_rw;

--
-- Name: frames_20101025; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101025 (
    CONSTRAINT frames_20101025_date_check CHECK ((('2010-10-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-01 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101025 OWNER TO breakpad_rw;

--
-- Name: frames_20101101; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101101 (
    CONSTRAINT frames_20101101_date_check CHECK ((('2010-11-01 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-08 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101101 OWNER TO breakpad_rw;

--
-- Name: frames_20101108; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101108 (
    CONSTRAINT frames_20101108_date_check CHECK ((('2010-11-08 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-15 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101108 OWNER TO breakpad_rw;

--
-- Name: frames_20101115; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101115 (
    CONSTRAINT frames_20101115_date_check CHECK ((('2010-11-15 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-22 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101115 OWNER TO breakpad_rw;

--
-- Name: frames_20101122; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101122 (
    CONSTRAINT frames_20101122_date_check CHECK ((('2010-11-22 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-29 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101122 OWNER TO breakpad_rw;

--
-- Name: frames_20101129; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101129 (
    CONSTRAINT frames_20101129_date_check CHECK ((('2010-11-29 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-06 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101129 OWNER TO breakpad_rw;

--
-- Name: frames_20101206; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101206 (
    CONSTRAINT frames_20101206_date_check CHECK ((('2010-12-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-13 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101206 OWNER TO breakpad_rw;

--
-- Name: frames_20101213; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101213 (
    CONSTRAINT frames_20101213_date_check CHECK ((('2010-12-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-20 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101213 OWNER TO breakpad_rw;

--
-- Name: frames_20101220; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101220 (
    CONSTRAINT frames_20101220_date_check CHECK ((('2010-12-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-27 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101220 OWNER TO breakpad_rw;

--
-- Name: frames_20101227; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20101227 (
    CONSTRAINT frames_20101227_date_check CHECK ((('2010-12-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-03 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20101227 OWNER TO breakpad_rw;

--
-- Name: frames_20110103; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110103 (
    CONSTRAINT frames_20110103_date_check CHECK ((('2011-01-03 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-10 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110103 OWNER TO breakpad_rw;

--
-- Name: frames_20110110; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110110 (
    CONSTRAINT frames_20110110_date_check CHECK ((('2011-01-10 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-17 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110110 OWNER TO breakpad_rw;

--
-- Name: frames_20110117; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110117 (
    CONSTRAINT frames_20110117_date_check CHECK ((('2011-01-17 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-24 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110117 OWNER TO breakpad_rw;

--
-- Name: frames_20110124; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110124 (
    CONSTRAINT frames_20110124_date_check CHECK ((('2011-01-24 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-31 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110124 OWNER TO breakpad_rw;

--
-- Name: frames_20110131; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110131 (
    CONSTRAINT frames_20110131_date_check CHECK ((('2011-01-31 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-07 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110131 OWNER TO breakpad_rw;

--
-- Name: frames_20110207; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110207 (
    CONSTRAINT frames_20110207_date_check CHECK ((('2011-02-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-14 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110207 OWNER TO breakpad_rw;

--
-- Name: frames_20110214; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110214 (
    CONSTRAINT frames_20110214_date_check CHECK ((('2011-02-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-21 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110214 OWNER TO breakpad_rw;

--
-- Name: frames_20110221; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110221 (
    CONSTRAINT frames_20110221_date_check CHECK ((('2011-02-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-28 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110221 OWNER TO breakpad_rw;

--
-- Name: frames_20110228; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110228 (
    CONSTRAINT frames_20110228_date_check CHECK ((('2011-02-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-07 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110228 OWNER TO breakpad_rw;

--
-- Name: frames_20110307; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110307 (
    CONSTRAINT frames_20110307_date_check CHECK ((('2011-03-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-14 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110307 OWNER TO breakpad_rw;

--
-- Name: frames_20110314; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110314 (
    CONSTRAINT frames_20110314_date_check CHECK ((('2011-03-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-21 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110314 OWNER TO breakpad_rw;

--
-- Name: frames_20110321; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110321 (
    CONSTRAINT frames_20110321_date_check CHECK ((('2011-03-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-28 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110321 OWNER TO breakpad_rw;

--
-- Name: frames_20110328; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110328 (
    CONSTRAINT frames_20110328_date_check CHECK ((('2011-03-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-04 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110328 OWNER TO breakpad_rw;

--
-- Name: frames_20110404; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110404 (
    CONSTRAINT frames_20110404_date_check CHECK ((('2011-04-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-11 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110404 OWNER TO breakpad_rw;

--
-- Name: frames_20110411; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110411 (
    CONSTRAINT frames_20110411_date_check CHECK ((('2011-04-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-18 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110411 OWNER TO breakpad_rw;

--
-- Name: frames_20110418; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110418 (
    CONSTRAINT frames_20110418_date_check CHECK ((('2011-04-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-25 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110418 OWNER TO breakpad_rw;

--
-- Name: frames_20110425; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110425 (
    CONSTRAINT frames_20110425_date_check CHECK ((('2011-04-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-02 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110425 OWNER TO breakpad_rw;

--
-- Name: frames_20110502; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110502 (
    CONSTRAINT frames_20110502_date_check CHECK ((('2011-05-02 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-09 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110502 OWNER TO breakpad_rw;

--
-- Name: frames_20110509; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110509 (
    CONSTRAINT frames_20110509_date_check CHECK ((('2011-05-09 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-16 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110509 OWNER TO breakpad_rw;

--
-- Name: frames_20110516; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110516 (
    CONSTRAINT frames_20110516_date_check CHECK ((('2011-05-16 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-23 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110516 OWNER TO breakpad_rw;

--
-- Name: frames_20110523; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110523 (
    CONSTRAINT frames_20110523_date_check CHECK ((('2011-05-23 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-30 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110523 OWNER TO breakpad_rw;

--
-- Name: frames_20110530; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110530 (
    CONSTRAINT frames_20110530_date_check CHECK ((('2011-05-30 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-06 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110530 OWNER TO breakpad_rw;

--
-- Name: frames_20110606; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110606 (
    CONSTRAINT frames_20110606_date_check CHECK ((('2011-06-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-13 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110606 OWNER TO breakpad_rw;

--
-- Name: frames_20110613; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110613 (
    CONSTRAINT frames_20110613_date_check CHECK ((('2011-06-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-20 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110613 OWNER TO breakpad_rw;

--
-- Name: frames_20110620; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110620 (
    CONSTRAINT frames_20110620_date_check CHECK ((('2011-06-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-27 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110620 OWNER TO breakpad_rw;

--
-- Name: frames_20110627; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110627 (
    CONSTRAINT frames_20110627_date_check CHECK ((('2011-06-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-04 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110627 OWNER TO breakpad_rw;

--
-- Name: frames_20110704; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110704 (
    CONSTRAINT frames_20110704_date_check CHECK ((('2011-07-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-11 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110704 OWNER TO breakpad_rw;

--
-- Name: frames_20110711; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110711 (
    CONSTRAINT frames_20110711_date_check CHECK ((('2011-07-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-18 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110711 OWNER TO breakpad_rw;

--
-- Name: frames_20110718; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110718 (
    CONSTRAINT frames_20110718_date_check CHECK ((('2011-07-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-25 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110718 OWNER TO breakpad_rw;

--
-- Name: frames_20110725; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110725 (
    CONSTRAINT frames_20110725_date_check CHECK ((('2011-07-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-01 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110725 OWNER TO breakpad_rw;

--
-- Name: frames_20110801; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110801 (
    CONSTRAINT frames_20110801_date_check CHECK ((('2011-08-01 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-08 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110801 OWNER TO breakpad_rw;

--
-- Name: frames_20110808; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110808 (
    CONSTRAINT frames_20110808_date_check CHECK ((('2011-08-08 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-15 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110808 OWNER TO breakpad_rw;

--
-- Name: frames_20110815; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110815 (
    CONSTRAINT frames_20110815_date_check CHECK ((('2011-08-15 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-22 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110815 OWNER TO breakpad_rw;

--
-- Name: frames_20110822; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110822 (
    CONSTRAINT frames_20110822_date_check CHECK ((('2011-08-22 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-29 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110822 OWNER TO breakpad_rw;

--
-- Name: frames_20110829; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110829 (
    CONSTRAINT frames_20110829_date_check CHECK ((('2011-08-29 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-09-05 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110829 OWNER TO breakpad_rw;

--
-- Name: frames_20110905; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames_20110905 (
    CONSTRAINT frames_20110905_date_check CHECK ((('2011-09-05 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-09-12 00:00:00'::timestamp without time zone)))
)
INHERITS (frames);


ALTER TABLE public.frames_20110905 OWNER TO breakpad_rw;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE jobs (
    id integer NOT NULL,
    pathname character varying(1024) NOT NULL,
    uuid character varying(50) NOT NULL,
    owner integer,
    priority integer DEFAULT 0,
    queueddatetime timestamp without time zone,
    starteddatetime timestamp without time zone,
    completeddatetime timestamp without time zone,
    success boolean,
    message text
);


ALTER TABLE public.jobs OWNER TO breakpad_rw;

--
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
-- Name: jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE jobs_id_seq OWNED BY jobs.id;


--
-- Name: jobs_in_queue; Type: VIEW; Schema: public; Owner: monitoring
--

CREATE VIEW jobs_in_queue AS
    SELECT count(*) AS count FROM jobs WHERE (jobs.completeddatetime IS NULL);


ALTER TABLE public.jobs_in_queue OWNER TO monitoring;

--
-- Name: last_backfill_temp; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE last_backfill_temp (
    last_date date
);


ALTER TABLE public.last_backfill_temp OWNER TO postgres;

--
-- Name: last_tcbsig; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE last_tcbsig (
    id integer,
    count integer,
    uptime real,
    signature text,
    productdims_id integer,
    osdims_id integer,
    window_end timestamp without time zone,
    window_size interval,
    hang_count integer,
    plugin_count integer
);


ALTER TABLE public.last_tcbsig OWNER TO postgres;

--
-- Name: last_tcburl; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE last_tcburl (
    id integer,
    count integer,
    urldims_id integer,
    productdims_id integer,
    osdims_id integer,
    window_end timestamp without time zone,
    window_size interval
);


ALTER TABLE public.last_tcburl OWNER TO postgres;

--
-- Name: last_urlsig; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE last_urlsig (
    top_crashes_by_url_id integer,
    signature text,
    count integer
);


ALTER TABLE public.last_urlsig OWNER TO postgres;

--
-- Name: os_name_matches; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE os_name_matches (
    os_name citext NOT NULL,
    match_string text NOT NULL
);


ALTER TABLE public.os_name_matches OWNER TO breakpad_rw;

--
-- Name: os_names; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE os_names (
    os_name citext NOT NULL,
    os_short_name citext NOT NULL
);


ALTER TABLE public.os_names OWNER TO breakpad_rw;

--
-- Name: os_versions; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE os_versions (
    os_version_id integer NOT NULL,
    os_name citext NOT NULL,
    major_version integer NOT NULL,
    minor_version integer NOT NULL
);


ALTER TABLE public.os_versions OWNER TO breakpad_rw;

--
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
-- Name: os_versions_os_version_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE os_versions_os_version_id_seq OWNED BY os_versions.os_version_id;


--
-- Name: osdims; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE osdims (
    id integer NOT NULL,
    os_name character varying(100),
    os_version character varying(100)
);


ALTER TABLE public.osdims OWNER TO breakpad_rw;

--
-- Name: osdims_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE osdims_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.osdims_id_seq OWNER TO breakpad_rw;

--
-- Name: osdims_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE osdims_id_seq OWNED BY osdims.id;


--
-- Name: top_crashes_by_signature; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE top_crashes_by_signature (
    id integer NOT NULL,
    count integer,
    uptime real,
    signature text,
    productdims_id integer,
    osdims_id integer,
    window_end timestamp without time zone,
    window_size interval,
    hang_count integer,
    plugin_count integer
);


ALTER TABLE public.top_crashes_by_signature OWNER TO breakpad_rw;

--
-- Name: performance_check_1; Type: VIEW; Schema: public; Owner: monitoring
--

CREATE VIEW performance_check_1 AS
    SELECT productdims.product, top_crashes_by_signature.signature, count(*) AS count FROM (top_crashes_by_signature JOIN productdims ON ((top_crashes_by_signature.productdims_id = productdims.id))) WHERE (top_crashes_by_signature.window_end > (now() - '1 day'::interval)) GROUP BY productdims.product, top_crashes_by_signature.signature ORDER BY count(*) LIMIT 50;


ALTER TABLE public.performance_check_1 OWNER TO monitoring;

--
-- Name: pg_stat_statements; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW pg_stat_statements AS
    SELECT pg_stat_statements.userid, pg_stat_statements.dbid, pg_stat_statements.query, pg_stat_statements.calls, pg_stat_statements.total_time, pg_stat_statements.rows, pg_stat_statements.shared_blks_hit, pg_stat_statements.shared_blks_read, pg_stat_statements.shared_blks_written, pg_stat_statements.local_blks_hit, pg_stat_statements.local_blks_read, pg_stat_statements.local_blks_written, pg_stat_statements.temp_blks_read, pg_stat_statements.temp_blks_written FROM pg_stat_statements() pg_stat_statements(userid, dbid, query, calls, total_time, rows, shared_blks_hit, shared_blks_read, shared_blks_written, local_blks_hit, local_blks_read, local_blks_written, temp_blks_read, temp_blks_written);


ALTER TABLE public.pg_stat_statements OWNER TO postgres;

--
-- Name: plugins; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins (
    id integer NOT NULL,
    filename text NOT NULL,
    name text NOT NULL
);


ALTER TABLE public.plugins OWNER TO breakpad_rw;

--
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
-- Name: plugins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE plugins_id_seq OWNED BY plugins.id;


--
-- Name: plugins_reports; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports (
    report_id integer NOT NULL,
    plugin_id integer NOT NULL,
    date_processed timestamp without time zone,
    version text NOT NULL
);


ALTER TABLE public.plugins_reports OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100607; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100607 (
    CONSTRAINT plugins_reports_20100607_date_check CHECK ((('2010-06-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-14 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100607 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100614; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100614 (
    CONSTRAINT plugins_reports_20100614_date_check CHECK ((('2010-06-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-21 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100614 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100621; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100621 (
    CONSTRAINT plugins_reports_20100621_date_check CHECK ((('2010-06-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-28 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100621 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100628; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100628 (
    CONSTRAINT plugins_reports_20100628_date_check CHECK ((('2010-06-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-05 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100628 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100705; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100705 (
    CONSTRAINT plugins_reports_20100705_date_check CHECK ((('2010-07-05 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-12 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100705 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100712; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100712 (
    CONSTRAINT plugins_reports_20100712_date_check CHECK ((('2010-07-12 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-19 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100712 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100719; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100719 (
    CONSTRAINT plugins_reports_20100719_date_check CHECK ((('2010-07-19 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-26 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100719 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100726; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100726 (
    CONSTRAINT plugins_reports_20100726_date_check CHECK ((('2010-07-26 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-02 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100726 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100802; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100802 (
    CONSTRAINT plugins_reports_20100802_date_check CHECK ((('2010-08-02 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-09 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100802 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100809; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100809 (
    CONSTRAINT plugins_reports_20100809_date_check CHECK ((('2010-08-09 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-16 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100809 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100816; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100816 (
    CONSTRAINT plugins_reports_20100816_date_check CHECK ((('2010-08-16 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-23 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100816 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100823; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100823 (
    CONSTRAINT plugins_reports_20100823_date_check CHECK ((('2010-08-23 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-30 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100823 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100830; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100830 (
    CONSTRAINT plugins_reports_20100830_date_check CHECK ((('2010-08-30 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-06 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100830 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100906; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100906 (
    CONSTRAINT plugins_reports_20100906_date_check CHECK ((('2010-09-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-13 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100906 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100913; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100913 (
    CONSTRAINT plugins_reports_20100913_date_check CHECK ((('2010-09-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-20 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100913 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100920; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100920 (
    CONSTRAINT plugins_reports_20100920_date_check CHECK ((('2010-09-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-27 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100920 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20100927; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20100927 (
    CONSTRAINT plugins_reports_20100927_date_check CHECK ((('2010-09-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-04 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20100927 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101004; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101004 (
    CONSTRAINT plugins_reports_20101004_date_check CHECK ((('2010-10-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-11 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101004 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101011; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101011 (
    CONSTRAINT plugins_reports_20101011_date_check CHECK ((('2010-10-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-18 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101011 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101018; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101018 (
    CONSTRAINT plugins_reports_20101018_date_check CHECK ((('2010-10-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-25 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101018 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101025; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101025 (
    CONSTRAINT plugins_reports_20101025_date_check CHECK ((('2010-10-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-01 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101025 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101101; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101101 (
    CONSTRAINT plugins_reports_20101101_date_check CHECK ((('2010-11-01 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-08 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101101 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101108; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101108 (
    CONSTRAINT plugins_reports_20101108_date_check CHECK ((('2010-11-08 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-15 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101108 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101115; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101115 (
    CONSTRAINT plugins_reports_20101115_date_check CHECK ((('2010-11-15 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-22 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101115 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101122; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101122 (
    CONSTRAINT plugins_reports_20101122_date_check CHECK ((('2010-11-22 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-29 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101122 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101129; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101129 (
    CONSTRAINT plugins_reports_20101129_date_check CHECK ((('2010-11-29 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-06 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101129 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101206; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101206 (
    CONSTRAINT plugins_reports_20101206_date_check CHECK ((('2010-12-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-13 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101206 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101213; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101213 (
    CONSTRAINT plugins_reports_20101213_date_check CHECK ((('2010-12-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-20 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101213 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101220; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101220 (
    CONSTRAINT plugins_reports_20101220_date_check CHECK ((('2010-12-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-27 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101220 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20101227; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20101227 (
    CONSTRAINT plugins_reports_20101227_date_check CHECK ((('2010-12-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-03 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20101227 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110103; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110103 (
    CONSTRAINT plugins_reports_20110103_date_check CHECK ((('2011-01-03 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-10 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110103 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110110; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110110 (
    CONSTRAINT plugins_reports_20110110_date_check CHECK ((('2011-01-10 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-17 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110110 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110117; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110117 (
    CONSTRAINT plugins_reports_20110117_date_check CHECK ((('2011-01-17 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-24 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110117 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110124; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110124 (
    CONSTRAINT plugins_reports_20110124_date_check CHECK ((('2011-01-24 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-31 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110124 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110131; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110131 (
    CONSTRAINT plugins_reports_20110131_date_check CHECK ((('2011-01-31 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-07 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110131 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110207; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110207 (
    CONSTRAINT plugins_reports_20110207_date_check CHECK ((('2011-02-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-14 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110207 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110214; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110214 (
    CONSTRAINT plugins_reports_20110214_date_check CHECK ((('2011-02-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-21 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110214 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110221; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110221 (
    CONSTRAINT plugins_reports_20110221_date_check CHECK ((('2011-02-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-28 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110221 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110228; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110228 (
    CONSTRAINT plugins_reports_20110228_date_check CHECK ((('2011-02-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-07 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110228 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110307; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110307 (
    CONSTRAINT plugins_reports_20110307_date_check CHECK ((('2011-03-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-14 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110307 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110314; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110314 (
    CONSTRAINT plugins_reports_20110314_date_check CHECK ((('2011-03-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-21 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110314 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110321; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110321 (
    CONSTRAINT plugins_reports_20110321_date_check CHECK ((('2011-03-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-28 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110321 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110328; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110328 (
    CONSTRAINT plugins_reports_20110328_date_check CHECK ((('2011-03-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-04 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110328 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110404; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110404 (
    CONSTRAINT plugins_reports_20110404_date_check CHECK ((('2011-04-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-11 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110404 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110411; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110411 (
    CONSTRAINT plugins_reports_20110411_date_check CHECK ((('2011-04-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-18 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110411 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110418; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110418 (
    CONSTRAINT plugins_reports_20110418_date_check CHECK ((('2011-04-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-25 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110418 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110425; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110425 (
    CONSTRAINT plugins_reports_20110425_date_check CHECK ((('2011-04-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-02 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110425 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110502; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110502 (
    CONSTRAINT plugins_reports_20110502_date_check CHECK ((('2011-05-02 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-09 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110502 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110509; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110509 (
    CONSTRAINT plugins_reports_20110509_date_check CHECK ((('2011-05-09 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-16 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110509 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110516; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110516 (
    CONSTRAINT plugins_reports_20110516_date_check CHECK ((('2011-05-16 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-23 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110516 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110523; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110523 (
    CONSTRAINT plugins_reports_20110523_date_check CHECK ((('2011-05-23 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-30 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110523 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110530; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110530 (
    CONSTRAINT plugins_reports_20110530_date_check CHECK ((('2011-05-30 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-06 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110530 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110606; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110606 (
    CONSTRAINT plugins_reports_20110606_date_check CHECK ((('2011-06-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-13 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110606 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110613; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110613 (
    CONSTRAINT plugins_reports_20110613_date_check CHECK ((('2011-06-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-20 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110613 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110620; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110620 (
    CONSTRAINT plugins_reports_20110620_date_check CHECK ((('2011-06-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-27 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110620 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110627; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110627 (
    CONSTRAINT plugins_reports_20110627_date_check CHECK ((('2011-06-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-04 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110627 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110704; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110704 (
    CONSTRAINT plugins_reports_20110704_date_check CHECK ((('2011-07-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-11 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110704 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110711; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110711 (
    CONSTRAINT plugins_reports_20110711_date_check CHECK ((('2011-07-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-18 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110711 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110718; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110718 (
    CONSTRAINT plugins_reports_20110718_date_check CHECK ((('2011-07-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-25 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110718 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110725; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110725 (
    CONSTRAINT plugins_reports_20110725_date_check CHECK ((('2011-07-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-01 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110725 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110801; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110801 (
    CONSTRAINT plugins_reports_20110801_date_check CHECK ((('2011-08-01 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-08 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110801 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110808; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110808 (
    CONSTRAINT plugins_reports_20110808_date_check CHECK ((('2011-08-08 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-15 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110808 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110815; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110815 (
    CONSTRAINT plugins_reports_20110815_date_check CHECK ((('2011-08-15 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-22 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110815 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110822; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110822 (
    CONSTRAINT plugins_reports_20110822_date_check CHECK ((('2011-08-22 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-29 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110822 OWNER TO breakpad_rw;

--
-- Name: plugins_reports_20110829; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE plugins_reports_20110829 (
    CONSTRAINT plugins_reports_20110829_date_check CHECK ((('2011-08-29 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-09-05 00:00:00'::timestamp without time zone)))
)
INHERITS (plugins_reports);


ALTER TABLE public.plugins_reports_20110829 OWNER TO breakpad_rw;

--
-- Name: priority_jobs_1445; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1445 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1445 OWNER TO processor;

--
-- Name: priority_jobs_1447; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1447 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1447 OWNER TO processor;

--
-- Name: priority_jobs_1449; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1449 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1449 OWNER TO processor;

--
-- Name: priority_jobs_1450; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1450 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1450 OWNER TO processor;

--
-- Name: priority_jobs_1451; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1451 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1451 OWNER TO processor;

--
-- Name: priority_jobs_1452; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1452 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1452 OWNER TO processor;

--
-- Name: priority_jobs_1453; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1453 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1453 OWNER TO processor;

--
-- Name: priority_jobs_1454; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1454 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1454 OWNER TO processor;

--
-- Name: priority_jobs_1455; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1455 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1455 OWNER TO processor;

--
-- Name: priority_jobs_1456; Type: TABLE; Schema: public; Owner: processor; Tablespace:
--

CREATE TABLE priority_jobs_1456 (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priority_jobs_1456 OWNER TO processor;

--
-- Name: priorityjobs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE priorityjobs (
    uuid character varying(255) NOT NULL
);


ALTER TABLE public.priorityjobs OWNER TO breakpad_rw;

--
-- Name: priorityjobs_log; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE priorityjobs_log (
    uuid character varying(255)
);


ALTER TABLE public.priorityjobs_log OWNER TO postgres;

--
-- Name: priorityjobs_log_sjc_backup; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE priorityjobs_log_sjc_backup (
    uuid character varying(255)
);


ALTER TABLE public.priorityjobs_log_sjc_backup OWNER TO postgres;

--
-- Name: priorityjobs_logging_switch; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE priorityjobs_logging_switch (
    log_jobs boolean NOT NULL
);


ALTER TABLE public.priorityjobs_logging_switch OWNER TO postgres;

--
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
-- Name: processors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE processors_id_seq OWNED BY processors.id;


--
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
-- Name: product_release_channels; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE product_release_channels (
    product_name citext NOT NULL,
    release_channel citext NOT NULL,
    throttle numeric DEFAULT 1.0 NOT NULL
);


ALTER TABLE public.product_release_channels OWNER TO breakpad_rw;

--
-- Name: product_visibility; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE product_visibility (
    productdims_id integer NOT NULL,
    start_date timestamp without time zone,
    end_date timestamp without time zone,
    ignore boolean DEFAULT false,
    featured boolean DEFAULT false,
    throttle numeric(5,2) DEFAULT 0.00
);


ALTER TABLE public.product_visibility OWNER TO breakpad_rw;

--
-- Name: release_build_type_map; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE release_build_type_map (
    release release_enum NOT NULL,
    build_type citext NOT NULL
);


ALTER TABLE public.release_build_type_map OWNER TO breakpad_rw;

--
-- Name: product_info; Type: VIEW; Schema: public; Owner: breakpad_rw
--

CREATE VIEW product_info AS
    SELECT product_versions.product_version_id, product_versions.product_name, product_versions.version_string, 'new'::text AS which_table, product_versions.build_date AS start_date, product_versions.sunset_date AS end_date, product_versions.featured_version AS is_featured, product_versions.build_type, ((product_release_channels.throttle * (100)::numeric))::numeric(5,2) AS throttle FROM (product_versions JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) WHERE (product_versions.build_type = ANY (ARRAY['Release'::citext, 'Beta'::citext])) UNION ALL SELECT productdims.id AS product_version_id, productdims.product AS product_name, productdims.version AS version_string, 'old'::text AS which_table, product_visibility.start_date, product_visibility.end_date, product_visibility.featured AS is_featured, release_build_type_map.build_type, product_visibility.throttle FROM (((productdims JOIN product_visibility ON ((productdims.id = product_visibility.productdims_id))) JOIN release_build_type_map ON ((productdims.release = release_build_type_map.release))) LEFT JOIN product_versions ON (((productdims.product = product_versions.product_name) AND (productdims.version = product_versions.release_version)))) WHERE (product_versions.product_name IS NULL) ORDER BY 2, 3;


ALTER TABLE public.product_info OWNER TO breakpad_rw;

--
-- Name: product_selector; Type: VIEW; Schema: public; Owner: breakpad_rw
--

CREATE VIEW product_selector AS
    SELECT product_versions.product_name, product_versions.version_string, 'new'::text AS which_table FROM product_versions WHERE ((now() <= product_versions.sunset_date) AND (product_versions.build_type = ANY (ARRAY['Release'::citext, 'Beta'::citext]))) UNION ALL SELECT productdims.product AS product_name, productdims.version AS version_string, 'old'::text AS which_table FROM ((productdims JOIN product_visibility ON ((productdims.id = product_visibility.productdims_id))) LEFT JOIN product_versions ON (((productdims.product = product_versions.product_name) AND (productdims.version = product_versions.release_version)))) WHERE ((product_versions.product_name IS NULL) AND ((now() >= product_visibility.start_date) AND (now() <= (product_visibility.end_date + '1 day'::interval)))) ORDER BY 1, 2;


ALTER TABLE public.product_selector OWNER TO breakpad_rw;

--
-- Name: product_version_builds; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE product_version_builds (
    product_version_id integer NOT NULL,
    build_id numeric NOT NULL,
    platform text NOT NULL
);


ALTER TABLE public.product_version_builds OWNER TO breakpad_rw;

--
-- Name: productdims_version_sort; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE productdims_version_sort (
    id integer NOT NULL,
    product citext NOT NULL,
    version citext NOT NULL,
    sec1_num1 integer,
    sec1_string1 text,
    sec1_num2 integer,
    sec1_string2 text,
    sec2_num1 integer,
    sec2_string1 text,
    sec2_num2 integer,
    sec2_string2 text,
    sec3_num1 integer,
    sec3_string1 text,
    sec3_num2 integer,
    sec3_string2 text,
    extra text
);


ALTER TABLE public.productdims_version_sort OWNER TO breakpad_rw;

--
-- Name: products; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE products (
    product_name citext NOT NULL,
    sort smallint DEFAULT 0 NOT NULL,
    rapid_release_version major_version,
    release_name citext NOT NULL
);


ALTER TABLE public.products OWNER TO breakpad_rw;

--
-- Name: raw_adu; Type: TABLE; Schema: public; Owner: breakpad_metrics; Tablespace:
--

CREATE TABLE raw_adu (
    adu_count integer,
    date timestamp without time zone,
    product_name text,
    product_os_platform text,
    product_os_version text,
    product_version text,
    build text,
    build_channel text
);


ALTER TABLE public.raw_adu OWNER TO breakpad_metrics;

--
-- Name: release_channel_matches; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE release_channel_matches (
    release_channel citext NOT NULL,
    match_string text NOT NULL
);


ALTER TABLE public.release_channel_matches OWNER TO breakpad_rw;

--
-- Name: release_channels; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE release_channels (
    release_channel citext NOT NULL,
    sort smallint DEFAULT 0 NOT NULL
);


ALTER TABLE public.release_channels OWNER TO breakpad_rw;

--
-- Name: releasechannel_backfill; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE releasechannel_backfill (
    uuid text,
    release_channel citext
);


ALTER TABLE public.releasechannel_backfill OWNER TO postgres;

--
-- Name: releases_raw; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE releases_raw (
    product_name citext NOT NULL,
    version text NOT NULL,
    platform text NOT NULL,
    build_id numeric NOT NULL,
    build_type citext NOT NULL,
    beta_number integer
);


ALTER TABLE public.releases_raw OWNER TO breakpad_rw;

--
-- Name: replication_test; Type: TABLE; Schema: public; Owner: monitoring; Tablespace:
--

CREATE TABLE replication_test (
    id smallint,
    test boolean
);


ALTER TABLE public.replication_test OWNER TO monitoring;

--
-- Name: reports; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports (
    id integer NOT NULL,
    client_crash_date timestamp with time zone,
    date_processed timestamp without time zone,
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
    build_date timestamp without time zone,
    user_id character varying(50),
    started_datetime timestamp without time zone,
    completed_datetime timestamp without time zone,
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
    release_channel text
);


ALTER TABLE public.reports OWNER TO breakpad_rw;

--
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
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE reports_id_seq OWNED BY reports.id;


--
-- Name: reports_20100607; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100607 (
    CONSTRAINT reports_20100607_date_check CHECK ((('2010-06-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-14 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100607 OWNER TO breakpad_rw;

--
-- Name: reports_20100614; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100614 (
    CONSTRAINT reports_20100614_date_check CHECK ((('2010-06-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-21 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100614 OWNER TO breakpad_rw;

--
-- Name: reports_20100621; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100621 (
    CONSTRAINT reports_20100621_date_check CHECK ((('2010-06-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-06-28 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100621 OWNER TO breakpad_rw;

--
-- Name: reports_20100628; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100628 (
    CONSTRAINT reports_20100628_date_check CHECK ((('2010-06-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-05 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100628 OWNER TO breakpad_rw;

--
-- Name: reports_20100705; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100705 (
    CONSTRAINT reports_20100705_date_check CHECK ((('2010-07-05 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-12 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100705 OWNER TO breakpad_rw;

--
-- Name: reports_20100712; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100712 (
    CONSTRAINT reports_20100712_date_check CHECK ((('2010-07-12 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-19 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100712 OWNER TO breakpad_rw;

--
-- Name: reports_20100719; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100719 (
    CONSTRAINT reports_20100719_date_check CHECK ((('2010-07-19 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-07-26 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100719 OWNER TO breakpad_rw;

--
-- Name: reports_20100726; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100726 (
    CONSTRAINT reports_20100726_date_check CHECK ((('2010-07-26 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-02 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100726 OWNER TO breakpad_rw;

--
-- Name: reports_20100802; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100802 (
    CONSTRAINT reports_20100802_date_check CHECK ((('2010-08-02 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-09 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100802 OWNER TO breakpad_rw;

--
-- Name: reports_20100809; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100809 (
    CONSTRAINT reports_20100809_date_check CHECK ((('2010-08-09 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-16 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100809 OWNER TO breakpad_rw;

--
-- Name: reports_20100816; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100816 (
    CONSTRAINT reports_20100816_date_check CHECK ((('2010-08-16 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-23 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100816 OWNER TO breakpad_rw;

--
-- Name: reports_20100823; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100823 (
    CONSTRAINT reports_20100823_date_check CHECK ((('2010-08-23 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-08-30 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100823 OWNER TO breakpad_rw;

--
-- Name: reports_20100830; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100830 (
    CONSTRAINT reports_20100830_date_check CHECK ((('2010-08-30 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-06 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100830 OWNER TO breakpad_rw;

--
-- Name: reports_20100906; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100906 (
    CONSTRAINT reports_20100906_date_check CHECK ((('2010-09-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-13 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100906 OWNER TO breakpad_rw;

--
-- Name: reports_20100913; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100913 (
    CONSTRAINT reports_20100913_date_check CHECK ((('2010-09-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-20 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100913 OWNER TO breakpad_rw;

--
-- Name: reports_20100920; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100920 (
    CONSTRAINT reports_20100920_date_check CHECK ((('2010-09-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-09-27 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100920 OWNER TO breakpad_rw;

--
-- Name: reports_20100927; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20100927 (
    CONSTRAINT reports_20100927_date_check CHECK ((('2010-09-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-04 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20100927 OWNER TO breakpad_rw;

--
-- Name: reports_20101004; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101004 (
    CONSTRAINT reports_20101004_date_check CHECK ((('2010-10-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-11 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101004 OWNER TO breakpad_rw;

--
-- Name: reports_20101011; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101011 (
    CONSTRAINT reports_20101011_date_check CHECK ((('2010-10-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-18 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101011 OWNER TO breakpad_rw;

--
-- Name: reports_20101018; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101018 (
    CONSTRAINT reports_20101018_date_check CHECK ((('2010-10-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-10-25 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101018 OWNER TO breakpad_rw;

--
-- Name: reports_20101025; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101025 (
    CONSTRAINT reports_20101025_date_check CHECK ((('2010-10-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101025 OWNER TO breakpad_rw;

--
-- Name: reports_20101101; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101101 (
    CONSTRAINT reports_20101101_date_check CHECK ((('2010-11-01 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-08 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101101 OWNER TO breakpad_rw;

--
-- Name: reports_20101108; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101108 (
    CONSTRAINT reports_20101108_date_check CHECK ((('2010-11-08 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-15 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101108 OWNER TO breakpad_rw;

--
-- Name: reports_20101115; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101115 (
    CONSTRAINT reports_20101115_date_check CHECK ((('2010-11-15 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-22 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101115 OWNER TO breakpad_rw;

--
-- Name: reports_20101122; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101122 (
    CONSTRAINT reports_20101122_date_check CHECK ((('2010-11-22 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-11-29 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101122 OWNER TO breakpad_rw;

--
-- Name: reports_20101129; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101129 (
    CONSTRAINT reports_20101129_date_check CHECK ((('2010-11-29 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-06 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101129 OWNER TO breakpad_rw;

--
-- Name: reports_20101206; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101206 (
    CONSTRAINT reports_20101206_date_check CHECK ((('2010-12-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-13 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101206 OWNER TO breakpad_rw;

--
-- Name: reports_20101213; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101213 (
    CONSTRAINT reports_20101213_date_check CHECK ((('2010-12-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-20 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101213 OWNER TO breakpad_rw;

--
-- Name: reports_20101220; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101220 (
    CONSTRAINT reports_20101220_date_check CHECK ((('2010-12-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2010-12-27 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101220 OWNER TO breakpad_rw;

--
-- Name: reports_20101227; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20101227 (
    CONSTRAINT reports_20101227_date_check CHECK ((('2010-12-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-03 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20101227 OWNER TO breakpad_rw;

--
-- Name: reports_20110103; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110103 (
    CONSTRAINT reports_20110103_date_check CHECK ((('2011-01-03 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-10 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110103 OWNER TO breakpad_rw;

--
-- Name: reports_20110110; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110110 (
    CONSTRAINT reports_20110110_date_check CHECK ((('2011-01-10 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-17 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110110 OWNER TO breakpad_rw;

--
-- Name: reports_20110117; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110117 (
    CONSTRAINT reports_20110117_date_check CHECK ((('2011-01-17 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-24 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110117 OWNER TO breakpad_rw;

--
-- Name: reports_20110124; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110124 (
    CONSTRAINT reports_20110124_date_check CHECK ((('2011-01-24 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-01-31 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110124 OWNER TO breakpad_rw;

--
-- Name: reports_20110131; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110131 (
    CONSTRAINT reports_20110131_date_check CHECK ((('2011-01-31 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-07 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110131 OWNER TO breakpad_rw;

--
-- Name: reports_20110207; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110207 (
    CONSTRAINT reports_20110207_date_check CHECK ((('2011-02-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-14 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110207 OWNER TO breakpad_rw;

--
-- Name: reports_20110214; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110214 (
    CONSTRAINT reports_20110214_date_check CHECK ((('2011-02-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-21 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110214 OWNER TO breakpad_rw;

--
-- Name: reports_20110221; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110221 (
    CONSTRAINT reports_20110221_date_check CHECK ((('2011-02-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-02-28 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110221 OWNER TO breakpad_rw;

--
-- Name: reports_20110228; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110228 (
    CONSTRAINT reports_20110228_date_check CHECK ((('2011-02-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-07 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110228 OWNER TO breakpad_rw;

--
-- Name: reports_20110307; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110307 (
    CONSTRAINT reports_20110307_date_check CHECK ((('2011-03-07 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-14 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110307 OWNER TO breakpad_rw;

--
-- Name: reports_20110314; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110314 (
    CONSTRAINT reports_20110314_date_check CHECK ((('2011-03-14 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-21 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110314 OWNER TO breakpad_rw;

--
-- Name: reports_20110321; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110321 (
    CONSTRAINT reports_20110321_date_check CHECK ((('2011-03-21 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-03-28 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110321 OWNER TO breakpad_rw;

--
-- Name: reports_20110328; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110328 (
    CONSTRAINT reports_20110328_date_check CHECK ((('2011-03-28 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-04 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110328 OWNER TO breakpad_rw;

--
-- Name: reports_20110404; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110404 (
    CONSTRAINT reports_20110404_date_check CHECK ((('2011-04-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-11 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110404 OWNER TO breakpad_rw;

--
-- Name: reports_20110411; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110411 (
    CONSTRAINT reports_20110411_date_check CHECK ((('2011-04-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-18 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110411 OWNER TO breakpad_rw;

--
-- Name: reports_20110418; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110418 (
    CONSTRAINT reports_20110418_date_check CHECK ((('2011-04-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-04-25 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110418 OWNER TO breakpad_rw;

--
-- Name: reports_20110425; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110425 (
    CONSTRAINT reports_20110425_date_check CHECK ((('2011-04-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-02 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110425 OWNER TO breakpad_rw;

--
-- Name: reports_20110502; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110502 (
    CONSTRAINT reports_20110502_date_check CHECK ((('2011-05-02 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-09 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110502 OWNER TO breakpad_rw;

--
-- Name: reports_20110509; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110509 (
    CONSTRAINT reports_20110509_date_check CHECK ((('2011-05-09 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-16 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110509 OWNER TO breakpad_rw;

--
-- Name: reports_20110516; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110516 (
    CONSTRAINT reports_20110516_date_check CHECK ((('2011-05-16 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-23 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110516 OWNER TO breakpad_rw;

--
-- Name: reports_20110523; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110523 (
    CONSTRAINT reports_20110523_date_check CHECK ((('2011-05-23 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-05-30 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110523 OWNER TO breakpad_rw;

--
-- Name: reports_20110530; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110530 (
    CONSTRAINT reports_20110530_date_check CHECK ((('2011-05-30 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-06 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110530 OWNER TO breakpad_rw;

--
-- Name: reports_20110606; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110606 (
    CONSTRAINT reports_20110606_date_check CHECK ((('2011-06-06 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-13 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110606 OWNER TO breakpad_rw;

--
-- Name: reports_20110613; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110613 (
    CONSTRAINT reports_20110613_date_check CHECK ((('2011-06-13 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-20 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110613 OWNER TO breakpad_rw;

--
-- Name: reports_20110620; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110620 (
    CONSTRAINT reports_20110620_date_check CHECK ((('2011-06-20 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-06-27 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110620 OWNER TO breakpad_rw;

--
-- Name: reports_20110627; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110627 (
    CONSTRAINT reports_20110627_date_check CHECK ((('2011-06-27 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-04 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110627 OWNER TO breakpad_rw;

--
-- Name: reports_20110704; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110704 (
    CONSTRAINT reports_20110704_date_check CHECK ((('2011-07-04 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-11 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110704 OWNER TO breakpad_rw;

--
-- Name: reports_20110711; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110711 (
    CONSTRAINT reports_20110711_date_check CHECK ((('2011-07-11 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-18 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110711 OWNER TO breakpad_rw;

--
-- Name: reports_20110718; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110718 (
    CONSTRAINT reports_20110718_date_check CHECK ((('2011-07-18 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-07-25 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110718 OWNER TO breakpad_rw;

--
-- Name: reports_20110725; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110725 (
    CONSTRAINT reports_20110725_date_check CHECK ((('2011-07-25 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110725 OWNER TO breakpad_rw;

--
-- Name: reports_20110801; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110801 (
    CONSTRAINT reports_20110801_date_check CHECK ((('2011-08-01 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-08 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110801 OWNER TO breakpad_rw;

--
-- Name: reports_20110808; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110808 (
    CONSTRAINT reports_20110808_date_check CHECK ((('2011-08-08 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-15 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110808 OWNER TO breakpad_rw;

--
-- Name: reports_20110815; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110815 (
    CONSTRAINT reports_20110815_date_check CHECK ((('2011-08-15 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-22 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110815 OWNER TO breakpad_rw;

--
-- Name: reports_20110822; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110822 (
    CONSTRAINT reports_20110822_date_check CHECK ((('2011-08-22 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-08-29 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110822 OWNER TO breakpad_rw;

--
-- Name: reports_20110829; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110829 (
    CONSTRAINT reports_20110829_date_check CHECK ((('2011-08-29 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-09-05 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110829 OWNER TO breakpad_rw;

--
-- Name: reports_20110905; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_20110905 (
    CONSTRAINT reports_20110905_date_check CHECK ((('2011-09-05 00:00:00'::timestamp without time zone <= date_processed) AND (date_processed < '2011-09-12 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_20110905 OWNER TO breakpad_rw;

--
-- Name: reports_duplicates; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports_duplicates (
    uuid text NOT NULL,
    duplicate_of text NOT NULL,
    date_processed timestamp without time zone NOT NULL
);


ALTER TABLE public.reports_duplicates OWNER TO breakpad_rw;

--
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
-- Name: sequence_numbers; Type: TABLE; Schema: public; Owner: postgres; Tablespace:
--

CREATE TABLE sequence_numbers (
    relname text,
    current_num bigint
);


ALTER TABLE public.sequence_numbers OWNER TO postgres;

--
-- Name: server_status; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE server_status (
    id integer NOT NULL,
    date_recently_completed timestamp without time zone,
    date_oldest_job_queued timestamp without time zone,
    avg_process_sec real,
    avg_wait_sec real,
    waiting_job_count integer NOT NULL,
    processors_count integer NOT NULL,
    date_created timestamp without time zone NOT NULL
);


ALTER TABLE public.server_status OWNER TO breakpad_rw;

--
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
-- Name: server_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE server_status_id_seq OWNED BY server_status.id;


--
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
-- Name: signature_bugs_rollup; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE signature_bugs_rollup (
    signature_id integer NOT NULL,
    bug_count integer DEFAULT 0 NOT NULL,
    bug_list integer[] DEFAULT '{}'::integer[] NOT NULL
);


ALTER TABLE public.signature_bugs_rollup OWNER TO breakpad_rw;

--
-- Name: signature_build; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE signature_build (
    signature character varying(255),
    productdims_id integer,
    product citext,
    version citext,
    os_name citext,
    build character varying(30),
    first_report timestamp without time zone
);


ALTER TABLE public.signature_build OWNER TO breakpad_rw;

--
-- Name: signature_first; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE signature_first (
    signature text NOT NULL,
    productdims_id integer NOT NULL,
    osdims_id integer NOT NULL,
    first_report timestamp without time zone,
    first_build text
);


ALTER TABLE public.signature_first OWNER TO breakpad_rw;

--
-- Name: signature_productdims; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE signature_productdims (
    signature text NOT NULL,
    productdims_id integer NOT NULL,
    first_report timestamp with time zone
);


ALTER TABLE public.signature_productdims OWNER TO breakpad_rw;

--
-- Name: signature_products; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE signature_products (
    signature_id integer NOT NULL,
    product_version_id integer NOT NULL,
    first_report timestamp without time zone
);


ALTER TABLE public.signature_products OWNER TO breakpad_rw;

--
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
-- Name: signatures; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE signatures (
    signature_id integer NOT NULL,
    signature text,
    first_report timestamp without time zone,
    first_build numeric
);


ALTER TABLE public.signatures OWNER TO breakpad_rw;

--
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
-- Name: signatures_signature_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE signatures_signature_id_seq OWNED BY signatures.signature_id;


--
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
    hang_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.tcbs OWNER TO breakpad_rw;

--
-- Name: tcbs_ranking; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE tcbs_ranking (
    product_version_id integer NOT NULL,
    signature_id integer NOT NULL,
    process_type citext,
    release_channel citext,
    aggregation_level citext,
    total_reports bigint,
    rank_report_count integer,
    percent_of_total numeric
);


ALTER TABLE public.tcbs_ranking OWNER TO breakpad_rw;

--
-- Name: top_crashes_by_signature_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE top_crashes_by_signature_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.top_crashes_by_signature_id_seq OWNER TO breakpad_rw;

--
-- Name: top_crashes_by_signature_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE top_crashes_by_signature_id_seq OWNED BY top_crashes_by_signature.id;


--
-- Name: top_crashes_by_url; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE top_crashes_by_url (
    id integer NOT NULL,
    count integer,
    urldims_id integer,
    productdims_id integer,
    osdims_id integer,
    window_end timestamp without time zone,
    window_size interval
);


ALTER TABLE public.top_crashes_by_url OWNER TO breakpad_rw;

--
-- Name: top_crashes_by_url_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE top_crashes_by_url_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.top_crashes_by_url_id_seq OWNER TO breakpad_rw;

--
-- Name: top_crashes_by_url_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE top_crashes_by_url_id_seq OWNED BY top_crashes_by_url.id;


--
-- Name: top_crashes_by_url_signature; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE top_crashes_by_url_signature (
    top_crashes_by_url_id integer NOT NULL,
    signature text NOT NULL,
    count integer
);


ALTER TABLE public.top_crashes_by_url_signature OWNER TO breakpad_rw;

--
-- Name: topcrashurlfactsreports; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE topcrashurlfactsreports (
    id integer NOT NULL,
    uuid character varying(50) NOT NULL,
    comments text,
    topcrashurlfacts_id integer
);


ALTER TABLE public.topcrashurlfactsreports OWNER TO breakpad_rw;

--
-- Name: topcrashurlfactsreports_id_seq1; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE topcrashurlfactsreports_id_seq1
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.topcrashurlfactsreports_id_seq1 OWNER TO breakpad_rw;

--
-- Name: topcrashurlfactsreports_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE topcrashurlfactsreports_id_seq1 OWNED BY topcrashurlfactsreports.id;


--
-- Name: urldims; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE urldims (
    id integer NOT NULL,
    domain text NOT NULL,
    url text NOT NULL
);


ALTER TABLE public.urldims OWNER TO breakpad_rw;

--
-- Name: urldims_id_seq1; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE urldims_id_seq1
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.urldims_id_seq1 OWNER TO breakpad_rw;

--
-- Name: urldims_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE urldims_id_seq1 OWNED BY urldims.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE daily_crashes ALTER COLUMN id SET DEFAULT nextval('daily_crashes_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE email_campaigns ALTER COLUMN id SET DEFAULT nextval('email_campaigns_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE email_contacts ALTER COLUMN id SET DEFAULT nextval('email_contacts_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE jobs ALTER COLUMN id SET DEFAULT nextval('jobs_id_seq'::regclass);


--
-- Name: os_version_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE os_versions ALTER COLUMN os_version_id SET DEFAULT nextval('os_versions_os_version_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE osdims ALTER COLUMN id SET DEFAULT nextval('osdims_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE plugins ALTER COLUMN id SET DEFAULT nextval('plugins_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE processors ALTER COLUMN id SET DEFAULT nextval('processors_id_seq'::regclass);


--
-- Name: product_version_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE product_versions ALTER COLUMN product_version_id SET DEFAULT nextval('productdims_id_seq1'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE reports ALTER COLUMN id SET DEFAULT nextval('reports_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE server_status ALTER COLUMN id SET DEFAULT nextval('server_status_id_seq'::regclass);


--
-- Name: signature_id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE signatures ALTER COLUMN signature_id SET DEFAULT nextval('signatures_signature_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE top_crashes_by_signature ALTER COLUMN id SET DEFAULT nextval('top_crashes_by_signature_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE top_crashes_by_url ALTER COLUMN id SET DEFAULT nextval('top_crashes_by_url_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE topcrashurlfactsreports ALTER COLUMN id SET DEFAULT nextval('topcrashurlfactsreports_id_seq1'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE urldims ALTER COLUMN id SET DEFAULT nextval('urldims_id_seq1'::regclass);


--
-- Name: alexa_topsites_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY alexa_topsites
    ADD CONSTRAINT alexa_topsites_pkey PRIMARY KEY (domain);


--
-- Name: bug_associations_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY bug_associations
    ADD CONSTRAINT bug_associations_pkey PRIMARY KEY (signature, bug_id);


--
-- Name: bugs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY bugs
    ADD CONSTRAINT bugs_pkey PRIMARY KEY (id);


--
-- Name: cronjobs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY cronjobs
    ADD CONSTRAINT cronjobs_pkey PRIMARY KEY (cronjob);


--
-- Name: daily_crash_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY daily_crash_codes
    ADD CONSTRAINT daily_crash_codes_pkey PRIMARY KEY (crash_code);


--
-- Name: daily_crashes_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY daily_crashes
    ADD CONSTRAINT daily_crashes_pkey PRIMARY KEY (id);


--
-- Name: day_product_os_report_type_unique; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY daily_crashes
    ADD CONSTRAINT day_product_os_report_type_unique UNIQUE (adu_day, productdims_id, os_short_name, report_type);


--
-- Name: email_campaigns_contacts_mapping_unique; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY email_campaigns_contacts
    ADD CONSTRAINT email_campaigns_contacts_mapping_unique UNIQUE (email_campaigns_id, email_contacts_id);


--
-- Name: email_campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY email_campaigns
    ADD CONSTRAINT email_campaigns_pkey PRIMARY KEY (id);


--
-- Name: email_contacts_email_unique; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY email_contacts
    ADD CONSTRAINT email_contacts_email_unique UNIQUE (email);


--
-- Name: email_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY email_contacts
    ADD CONSTRAINT email_contacts_pkey PRIMARY KEY (id);


--
-- Name: email_contacts_token_unique; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY email_contacts
    ADD CONSTRAINT email_contacts_token_unique UNIQUE (subscribe_token);


--
-- Name: extensions_20100607_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100607
    ADD CONSTRAINT extensions_20100607_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100614_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100614
    ADD CONSTRAINT extensions_20100614_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100621_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100621
    ADD CONSTRAINT extensions_20100621_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100628_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100628
    ADD CONSTRAINT extensions_20100628_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100705_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100705
    ADD CONSTRAINT extensions_20100705_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100712_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100712
    ADD CONSTRAINT extensions_20100712_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100719_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100719
    ADD CONSTRAINT extensions_20100719_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100726_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100726
    ADD CONSTRAINT extensions_20100726_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100802_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100802
    ADD CONSTRAINT extensions_20100802_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100809_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100809
    ADD CONSTRAINT extensions_20100809_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100816_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100816
    ADD CONSTRAINT extensions_20100816_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100823_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100823
    ADD CONSTRAINT extensions_20100823_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100830_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100830
    ADD CONSTRAINT extensions_20100830_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100906_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100906
    ADD CONSTRAINT extensions_20100906_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100913_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100913
    ADD CONSTRAINT extensions_20100913_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100920_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100920
    ADD CONSTRAINT extensions_20100920_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20100927_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20100927
    ADD CONSTRAINT extensions_20100927_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101004_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101004
    ADD CONSTRAINT extensions_20101004_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101011_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101011
    ADD CONSTRAINT extensions_20101011_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101018_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101018
    ADD CONSTRAINT extensions_20101018_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101025_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101025
    ADD CONSTRAINT extensions_20101025_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101101_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101101
    ADD CONSTRAINT extensions_20101101_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101108_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101108
    ADD CONSTRAINT extensions_20101108_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101115_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101115
    ADD CONSTRAINT extensions_20101115_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101122_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101122
    ADD CONSTRAINT extensions_20101122_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101129_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101129
    ADD CONSTRAINT extensions_20101129_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101206_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101206
    ADD CONSTRAINT extensions_20101206_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101213_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101213
    ADD CONSTRAINT extensions_20101213_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101220_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101220
    ADD CONSTRAINT extensions_20101220_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20101227_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20101227
    ADD CONSTRAINT extensions_20101227_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110103_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110103
    ADD CONSTRAINT extensions_20110103_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110110_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110110
    ADD CONSTRAINT extensions_20110110_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110117_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110117
    ADD CONSTRAINT extensions_20110117_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110124_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110124
    ADD CONSTRAINT extensions_20110124_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110131_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110131
    ADD CONSTRAINT extensions_20110131_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110207_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110207
    ADD CONSTRAINT extensions_20110207_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110214_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110214
    ADD CONSTRAINT extensions_20110214_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110221_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110221
    ADD CONSTRAINT extensions_20110221_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110228_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110228
    ADD CONSTRAINT extensions_20110228_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110307_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110307
    ADD CONSTRAINT extensions_20110307_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110314_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110314
    ADD CONSTRAINT extensions_20110314_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110321_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110321
    ADD CONSTRAINT extensions_20110321_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110328_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110328
    ADD CONSTRAINT extensions_20110328_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110404_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110404
    ADD CONSTRAINT extensions_20110404_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110411_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110411
    ADD CONSTRAINT extensions_20110411_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110418_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110418
    ADD CONSTRAINT extensions_20110418_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110425_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110425
    ADD CONSTRAINT extensions_20110425_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110502_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110502
    ADD CONSTRAINT extensions_20110502_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110509_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110509
    ADD CONSTRAINT extensions_20110509_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110516_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110516
    ADD CONSTRAINT extensions_20110516_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110523_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110523
    ADD CONSTRAINT extensions_20110523_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110530_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110530
    ADD CONSTRAINT extensions_20110530_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110606_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110606
    ADD CONSTRAINT extensions_20110606_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110613_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110613
    ADD CONSTRAINT extensions_20110613_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110620_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110620
    ADD CONSTRAINT extensions_20110620_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110627_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110627
    ADD CONSTRAINT extensions_20110627_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110704_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110704
    ADD CONSTRAINT extensions_20110704_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110711_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110711
    ADD CONSTRAINT extensions_20110711_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110718_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110718
    ADD CONSTRAINT extensions_20110718_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110725_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110725
    ADD CONSTRAINT extensions_20110725_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110801_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110801
    ADD CONSTRAINT extensions_20110801_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110808_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110808
    ADD CONSTRAINT extensions_20110808_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110815_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110815
    ADD CONSTRAINT extensions_20110815_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110822_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110822
    ADD CONSTRAINT extensions_20110822_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110829_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110829
    ADD CONSTRAINT extensions_20110829_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_20110905_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY extensions_20110905
    ADD CONSTRAINT extensions_20110905_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: filename_name_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins
    ADD CONSTRAINT filename_name_key UNIQUE (filename, name);


--
-- Name: frames_20100607_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100607
    ADD CONSTRAINT frames_20100607_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100614_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100614
    ADD CONSTRAINT frames_20100614_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100621_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100621
    ADD CONSTRAINT frames_20100621_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100628_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100628
    ADD CONSTRAINT frames_20100628_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100705_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100705
    ADD CONSTRAINT frames_20100705_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100712_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100712
    ADD CONSTRAINT frames_20100712_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100719_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100719
    ADD CONSTRAINT frames_20100719_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100726_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100726
    ADD CONSTRAINT frames_20100726_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100802_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100802
    ADD CONSTRAINT frames_20100802_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100809_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100809
    ADD CONSTRAINT frames_20100809_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100816_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100816
    ADD CONSTRAINT frames_20100816_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100823_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100823
    ADD CONSTRAINT frames_20100823_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100830_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100830
    ADD CONSTRAINT frames_20100830_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100906_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100906
    ADD CONSTRAINT frames_20100906_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100913_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100913
    ADD CONSTRAINT frames_20100913_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100920_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100920
    ADD CONSTRAINT frames_20100920_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20100927_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20100927
    ADD CONSTRAINT frames_20100927_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101004_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101004
    ADD CONSTRAINT frames_20101004_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101011_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101011
    ADD CONSTRAINT frames_20101011_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101018_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101018
    ADD CONSTRAINT frames_20101018_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101025_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101025
    ADD CONSTRAINT frames_20101025_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101101_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101101
    ADD CONSTRAINT frames_20101101_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101108_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101108
    ADD CONSTRAINT frames_20101108_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101115_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101115
    ADD CONSTRAINT frames_20101115_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101122_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101122
    ADD CONSTRAINT frames_20101122_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101129_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101129
    ADD CONSTRAINT frames_20101129_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101206_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101206
    ADD CONSTRAINT frames_20101206_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101213_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101213
    ADD CONSTRAINT frames_20101213_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101220_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101220
    ADD CONSTRAINT frames_20101220_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20101227_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20101227
    ADD CONSTRAINT frames_20101227_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110103_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110103
    ADD CONSTRAINT frames_20110103_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110110_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110110
    ADD CONSTRAINT frames_20110110_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110117_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110117
    ADD CONSTRAINT frames_20110117_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110124_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110124
    ADD CONSTRAINT frames_20110124_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110131_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110131
    ADD CONSTRAINT frames_20110131_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110207_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110207
    ADD CONSTRAINT frames_20110207_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110214_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110214
    ADD CONSTRAINT frames_20110214_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110221_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110221
    ADD CONSTRAINT frames_20110221_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110228_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110228
    ADD CONSTRAINT frames_20110228_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110307_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110307
    ADD CONSTRAINT frames_20110307_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110314_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110314
    ADD CONSTRAINT frames_20110314_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110321_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110321
    ADD CONSTRAINT frames_20110321_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110328_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110328
    ADD CONSTRAINT frames_20110328_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110404_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110404
    ADD CONSTRAINT frames_20110404_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110411_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110411
    ADD CONSTRAINT frames_20110411_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110418_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110418
    ADD CONSTRAINT frames_20110418_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110425_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110425
    ADD CONSTRAINT frames_20110425_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110502_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110502
    ADD CONSTRAINT frames_20110502_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110509_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110509
    ADD CONSTRAINT frames_20110509_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110516_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110516
    ADD CONSTRAINT frames_20110516_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110523_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110523
    ADD CONSTRAINT frames_20110523_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110530_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110530
    ADD CONSTRAINT frames_20110530_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110606_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110606
    ADD CONSTRAINT frames_20110606_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110613_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110613
    ADD CONSTRAINT frames_20110613_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110620_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110620
    ADD CONSTRAINT frames_20110620_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110627_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110627
    ADD CONSTRAINT frames_20110627_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110704_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110704
    ADD CONSTRAINT frames_20110704_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110711_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110711
    ADD CONSTRAINT frames_20110711_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110718_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110718
    ADD CONSTRAINT frames_20110718_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110725_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110725
    ADD CONSTRAINT frames_20110725_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110801_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110801
    ADD CONSTRAINT frames_20110801_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110808_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110808
    ADD CONSTRAINT frames_20110808_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110815_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110815
    ADD CONSTRAINT frames_20110815_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110822_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110822
    ADD CONSTRAINT frames_20110822_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110829_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110829
    ADD CONSTRAINT frames_20110829_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_20110905_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY frames_20110905
    ADD CONSTRAINT frames_20110905_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: jobs_uuid_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_uuid_key UNIQUE (uuid);


--
-- Name: os_name_matches_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY os_name_matches
    ADD CONSTRAINT os_name_matches_key PRIMARY KEY (os_name, match_string);


--
-- Name: os_names_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY os_names
    ADD CONSTRAINT os_names_pkey PRIMARY KEY (os_name);


--
-- Name: os_versions_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY os_versions
    ADD CONSTRAINT os_versions_key UNIQUE (os_name, major_version, minor_version);


--
-- Name: os_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY os_versions
    ADD CONSTRAINT os_versions_pkey PRIMARY KEY (os_version_id);


--
-- Name: osdims_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY osdims
    ADD CONSTRAINT osdims_pkey PRIMARY KEY (id);


--
-- Name: plugins_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins
    ADD CONSTRAINT plugins_pkey PRIMARY KEY (id);


--
-- Name: plugins_reports_20100607_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100607
    ADD CONSTRAINT plugins_reports_20100607_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100614_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100614
    ADD CONSTRAINT plugins_reports_20100614_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100621_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100621
    ADD CONSTRAINT plugins_reports_20100621_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100628_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100628
    ADD CONSTRAINT plugins_reports_20100628_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100705_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100705
    ADD CONSTRAINT plugins_reports_20100705_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100712_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100712
    ADD CONSTRAINT plugins_reports_20100712_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100719_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100719
    ADD CONSTRAINT plugins_reports_20100719_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100726_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100726
    ADD CONSTRAINT plugins_reports_20100726_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100802_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100802
    ADD CONSTRAINT plugins_reports_20100802_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100809_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100809
    ADD CONSTRAINT plugins_reports_20100809_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100816_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100816
    ADD CONSTRAINT plugins_reports_20100816_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100823_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100823
    ADD CONSTRAINT plugins_reports_20100823_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100830_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100830
    ADD CONSTRAINT plugins_reports_20100830_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100906_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100906
    ADD CONSTRAINT plugins_reports_20100906_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100913_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100913
    ADD CONSTRAINT plugins_reports_20100913_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100920_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100920
    ADD CONSTRAINT plugins_reports_20100920_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20100927_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20100927
    ADD CONSTRAINT plugins_reports_20100927_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101004_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101004
    ADD CONSTRAINT plugins_reports_20101004_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101011_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101011
    ADD CONSTRAINT plugins_reports_20101011_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101018_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101018
    ADD CONSTRAINT plugins_reports_20101018_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101025_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101025
    ADD CONSTRAINT plugins_reports_20101025_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101101_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101101
    ADD CONSTRAINT plugins_reports_20101101_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101108_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101108
    ADD CONSTRAINT plugins_reports_20101108_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101115_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101115
    ADD CONSTRAINT plugins_reports_20101115_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101122_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101122
    ADD CONSTRAINT plugins_reports_20101122_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101129_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101129
    ADD CONSTRAINT plugins_reports_20101129_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101206_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101206
    ADD CONSTRAINT plugins_reports_20101206_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101213_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101213
    ADD CONSTRAINT plugins_reports_20101213_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101220_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101220
    ADD CONSTRAINT plugins_reports_20101220_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20101227_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20101227
    ADD CONSTRAINT plugins_reports_20101227_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110103_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110103
    ADD CONSTRAINT plugins_reports_20110103_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110110_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110110
    ADD CONSTRAINT plugins_reports_20110110_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110117_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110117
    ADD CONSTRAINT plugins_reports_20110117_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110124_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110124
    ADD CONSTRAINT plugins_reports_20110124_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110131_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110131
    ADD CONSTRAINT plugins_reports_20110131_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110207_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110207
    ADD CONSTRAINT plugins_reports_20110207_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110214_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110214
    ADD CONSTRAINT plugins_reports_20110214_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110221_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110221
    ADD CONSTRAINT plugins_reports_20110221_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110228_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110228
    ADD CONSTRAINT plugins_reports_20110228_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110307_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110307
    ADD CONSTRAINT plugins_reports_20110307_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110314_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110314
    ADD CONSTRAINT plugins_reports_20110314_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110321_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110321
    ADD CONSTRAINT plugins_reports_20110321_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110328_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110328
    ADD CONSTRAINT plugins_reports_20110328_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110404_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110404
    ADD CONSTRAINT plugins_reports_20110404_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110411_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110411
    ADD CONSTRAINT plugins_reports_20110411_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110418_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110418
    ADD CONSTRAINT plugins_reports_20110418_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110425_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110425
    ADD CONSTRAINT plugins_reports_20110425_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110502_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110502
    ADD CONSTRAINT plugins_reports_20110502_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110509_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110509
    ADD CONSTRAINT plugins_reports_20110509_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110516_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110516
    ADD CONSTRAINT plugins_reports_20110516_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110523_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110523
    ADD CONSTRAINT plugins_reports_20110523_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110530_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110530
    ADD CONSTRAINT plugins_reports_20110530_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110606_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110606
    ADD CONSTRAINT plugins_reports_20110606_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110613_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110613
    ADD CONSTRAINT plugins_reports_20110613_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110620_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110620
    ADD CONSTRAINT plugins_reports_20110620_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110627_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110627
    ADD CONSTRAINT plugins_reports_20110627_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110704_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110704
    ADD CONSTRAINT plugins_reports_20110704_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110711_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110711
    ADD CONSTRAINT plugins_reports_20110711_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110718_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110718
    ADD CONSTRAINT plugins_reports_20110718_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110725_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110725
    ADD CONSTRAINT plugins_reports_20110725_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110801_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110801
    ADD CONSTRAINT plugins_reports_20110801_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110808_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110808
    ADD CONSTRAINT plugins_reports_20110808_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110815_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110815
    ADD CONSTRAINT plugins_reports_20110815_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110822_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110822
    ADD CONSTRAINT plugins_reports_20110822_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: plugins_reports_20110829_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY plugins_reports_20110829
    ADD CONSTRAINT plugins_reports_20110829_pkey PRIMARY KEY (report_id, plugin_id);


--
-- Name: priority_jobs_1445_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1445
    ADD CONSTRAINT priority_jobs_1445_pkey PRIMARY KEY (uuid);


--
-- Name: priority_jobs_1447_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1447
    ADD CONSTRAINT priority_jobs_1447_pkey PRIMARY KEY (uuid);


--
-- Name: priority_jobs_1449_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1449
    ADD CONSTRAINT priority_jobs_1449_pkey PRIMARY KEY (uuid);


--
-- Name: priority_jobs_1450_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1450
    ADD CONSTRAINT priority_jobs_1450_pkey PRIMARY KEY (uuid);


--
-- Name: priority_jobs_1451_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1451
    ADD CONSTRAINT priority_jobs_1451_pkey PRIMARY KEY (uuid);


--
-- Name: priority_jobs_1452_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1452
    ADD CONSTRAINT priority_jobs_1452_pkey PRIMARY KEY (uuid);


--
-- Name: priority_jobs_1453_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1453
    ADD CONSTRAINT priority_jobs_1453_pkey PRIMARY KEY (uuid);


--
-- Name: priority_jobs_1454_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1454
    ADD CONSTRAINT priority_jobs_1454_pkey PRIMARY KEY (uuid);


--
-- Name: priority_jobs_1455_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1455
    ADD CONSTRAINT priority_jobs_1455_pkey PRIMARY KEY (uuid);


--
-- Name: priority_jobs_1456_pkey; Type: CONSTRAINT; Schema: public; Owner: processor; Tablespace:
--

ALTER TABLE ONLY priority_jobs_1456
    ADD CONSTRAINT priority_jobs_1456_pkey PRIMARY KEY (uuid);


--
-- Name: priorityjobs_logging_switch_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace:
--

ALTER TABLE ONLY priorityjobs_logging_switch
    ADD CONSTRAINT priorityjobs_logging_switch_pkey PRIMARY KEY (log_jobs);


--
-- Name: priorityjobs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY priorityjobs
    ADD CONSTRAINT priorityjobs_pkey PRIMARY KEY (uuid);


--
-- Name: processors_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY processors
    ADD CONSTRAINT processors_pkey PRIMARY KEY (id);


--
-- Name: product_adu_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY product_adu
    ADD CONSTRAINT product_adu_key PRIMARY KEY (product_version_id, adu_date, os_name);


--
-- Name: product_release_channels_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY product_release_channels
    ADD CONSTRAINT product_release_channels_key PRIMARY KEY (product_name, release_channel);


--
-- Name: product_version_builds_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY product_version_builds
    ADD CONSTRAINT product_version_builds_key PRIMARY KEY (product_version_id, build_id, platform);


--
-- Name: product_version_version_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY product_versions
    ADD CONSTRAINT product_version_version_key UNIQUE (product_name, version_string);


--
-- Name: product_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY product_versions
    ADD CONSTRAINT product_versions_pkey PRIMARY KEY (product_version_id);


--
-- Name: product_visibility_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY product_visibility
    ADD CONSTRAINT product_visibility_pkey PRIMARY KEY (productdims_id);


--
-- Name: productdims_pkey1; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY productdims
    ADD CONSTRAINT productdims_pkey1 PRIMARY KEY (id);


--
-- Name: productdims_version_sort_id_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY productdims_version_sort
    ADD CONSTRAINT productdims_version_sort_id_key UNIQUE (id);


--
-- Name: productdims_version_sort_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY productdims_version_sort
    ADD CONSTRAINT productdims_version_sort_key PRIMARY KEY (product, version);


--
-- Name: products_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY products
    ADD CONSTRAINT products_pkey PRIMARY KEY (product_name);


--
-- Name: release_build_type_map_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY release_build_type_map
    ADD CONSTRAINT release_build_type_map_pkey PRIMARY KEY (release);


--
-- Name: release_channel_matches_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY release_channel_matches
    ADD CONSTRAINT release_channel_matches_key PRIMARY KEY (release_channel, match_string);


--
-- Name: release_channels_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY release_channels
    ADD CONSTRAINT release_channels_pkey PRIMARY KEY (release_channel);


--
-- Name: release_raw_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY releases_raw
    ADD CONSTRAINT release_raw_key PRIMARY KEY (product_name, version, build_id, build_type, platform);


--
-- Name: reports_20100607_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100607
    ADD CONSTRAINT reports_20100607_pkey PRIMARY KEY (id);


--
-- Name: reports_20100607_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100607
    ADD CONSTRAINT reports_20100607_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100614_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100614
    ADD CONSTRAINT reports_20100614_pkey PRIMARY KEY (id);


--
-- Name: reports_20100614_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100614
    ADD CONSTRAINT reports_20100614_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100621_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100621
    ADD CONSTRAINT reports_20100621_pkey PRIMARY KEY (id);


--
-- Name: reports_20100621_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100621
    ADD CONSTRAINT reports_20100621_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100628_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100628
    ADD CONSTRAINT reports_20100628_pkey PRIMARY KEY (id);


--
-- Name: reports_20100628_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100628
    ADD CONSTRAINT reports_20100628_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100705_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100705
    ADD CONSTRAINT reports_20100705_pkey PRIMARY KEY (id);


--
-- Name: reports_20100705_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100705
    ADD CONSTRAINT reports_20100705_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100712_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100712
    ADD CONSTRAINT reports_20100712_pkey PRIMARY KEY (id);


--
-- Name: reports_20100712_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100712
    ADD CONSTRAINT reports_20100712_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100719_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100719
    ADD CONSTRAINT reports_20100719_pkey PRIMARY KEY (id);


--
-- Name: reports_20100719_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100719
    ADD CONSTRAINT reports_20100719_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100726_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100726
    ADD CONSTRAINT reports_20100726_pkey PRIMARY KEY (id);


--
-- Name: reports_20100726_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100726
    ADD CONSTRAINT reports_20100726_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100802_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100802
    ADD CONSTRAINT reports_20100802_pkey PRIMARY KEY (id);


--
-- Name: reports_20100802_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100802
    ADD CONSTRAINT reports_20100802_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100809_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100809
    ADD CONSTRAINT reports_20100809_pkey PRIMARY KEY (id);


--
-- Name: reports_20100809_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100809
    ADD CONSTRAINT reports_20100809_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100816_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100816
    ADD CONSTRAINT reports_20100816_pkey PRIMARY KEY (id);


--
-- Name: reports_20100816_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100816
    ADD CONSTRAINT reports_20100816_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100823_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100823
    ADD CONSTRAINT reports_20100823_pkey PRIMARY KEY (id);


--
-- Name: reports_20100823_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100823
    ADD CONSTRAINT reports_20100823_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100830_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100830
    ADD CONSTRAINT reports_20100830_pkey PRIMARY KEY (id);


--
-- Name: reports_20100830_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100830
    ADD CONSTRAINT reports_20100830_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100906_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100906
    ADD CONSTRAINT reports_20100906_pkey PRIMARY KEY (id);


--
-- Name: reports_20100906_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100906
    ADD CONSTRAINT reports_20100906_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100913_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100913
    ADD CONSTRAINT reports_20100913_pkey PRIMARY KEY (id);


--
-- Name: reports_20100913_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100913
    ADD CONSTRAINT reports_20100913_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100920_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100920
    ADD CONSTRAINT reports_20100920_pkey PRIMARY KEY (id);


--
-- Name: reports_20100920_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100920
    ADD CONSTRAINT reports_20100920_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20100927_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100927
    ADD CONSTRAINT reports_20100927_pkey PRIMARY KEY (id);


--
-- Name: reports_20100927_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20100927
    ADD CONSTRAINT reports_20100927_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101004_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101004
    ADD CONSTRAINT reports_20101004_pkey PRIMARY KEY (id);


--
-- Name: reports_20101004_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101004
    ADD CONSTRAINT reports_20101004_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101011_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101011
    ADD CONSTRAINT reports_20101011_pkey PRIMARY KEY (id);


--
-- Name: reports_20101011_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101011
    ADD CONSTRAINT reports_20101011_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101018_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101018
    ADD CONSTRAINT reports_20101018_pkey PRIMARY KEY (id);


--
-- Name: reports_20101018_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101018
    ADD CONSTRAINT reports_20101018_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101025_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101025
    ADD CONSTRAINT reports_20101025_pkey PRIMARY KEY (id);


--
-- Name: reports_20101025_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101025
    ADD CONSTRAINT reports_20101025_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101101_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101101
    ADD CONSTRAINT reports_20101101_pkey PRIMARY KEY (id);


--
-- Name: reports_20101101_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101101
    ADD CONSTRAINT reports_20101101_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101108_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101108
    ADD CONSTRAINT reports_20101108_pkey PRIMARY KEY (id);


--
-- Name: reports_20101108_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101108
    ADD CONSTRAINT reports_20101108_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101115_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101115
    ADD CONSTRAINT reports_20101115_pkey PRIMARY KEY (id);


--
-- Name: reports_20101115_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101115
    ADD CONSTRAINT reports_20101115_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101122_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101122
    ADD CONSTRAINT reports_20101122_pkey PRIMARY KEY (id);


--
-- Name: reports_20101122_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101122
    ADD CONSTRAINT reports_20101122_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101129_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101129
    ADD CONSTRAINT reports_20101129_pkey PRIMARY KEY (id);


--
-- Name: reports_20101129_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101129
    ADD CONSTRAINT reports_20101129_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101206_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101206
    ADD CONSTRAINT reports_20101206_pkey PRIMARY KEY (id);


--
-- Name: reports_20101206_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101206
    ADD CONSTRAINT reports_20101206_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101213_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101213
    ADD CONSTRAINT reports_20101213_pkey PRIMARY KEY (id);


--
-- Name: reports_20101213_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101213
    ADD CONSTRAINT reports_20101213_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101220_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101220
    ADD CONSTRAINT reports_20101220_pkey PRIMARY KEY (id);


--
-- Name: reports_20101220_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101220
    ADD CONSTRAINT reports_20101220_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20101227_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101227
    ADD CONSTRAINT reports_20101227_pkey PRIMARY KEY (id);


--
-- Name: reports_20101227_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20101227
    ADD CONSTRAINT reports_20101227_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110103_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110103
    ADD CONSTRAINT reports_20110103_pkey PRIMARY KEY (id);


--
-- Name: reports_20110103_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110103
    ADD CONSTRAINT reports_20110103_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110110_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110110
    ADD CONSTRAINT reports_20110110_pkey PRIMARY KEY (id);


--
-- Name: reports_20110110_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110110
    ADD CONSTRAINT reports_20110110_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110117_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110117
    ADD CONSTRAINT reports_20110117_pkey PRIMARY KEY (id);


--
-- Name: reports_20110117_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110117
    ADD CONSTRAINT reports_20110117_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110124_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110124
    ADD CONSTRAINT reports_20110124_pkey PRIMARY KEY (id);


--
-- Name: reports_20110124_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110124
    ADD CONSTRAINT reports_20110124_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110131_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110131
    ADD CONSTRAINT reports_20110131_pkey PRIMARY KEY (id);


--
-- Name: reports_20110131_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110131
    ADD CONSTRAINT reports_20110131_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110207_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110207
    ADD CONSTRAINT reports_20110207_pkey PRIMARY KEY (id);


--
-- Name: reports_20110207_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110207
    ADD CONSTRAINT reports_20110207_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110214_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110214
    ADD CONSTRAINT reports_20110214_pkey PRIMARY KEY (id);


--
-- Name: reports_20110214_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110214
    ADD CONSTRAINT reports_20110214_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110221_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110221
    ADD CONSTRAINT reports_20110221_pkey PRIMARY KEY (id);


--
-- Name: reports_20110221_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110221
    ADD CONSTRAINT reports_20110221_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110228_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110228
    ADD CONSTRAINT reports_20110228_pkey PRIMARY KEY (id);


--
-- Name: reports_20110228_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110228
    ADD CONSTRAINT reports_20110228_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110307_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110307
    ADD CONSTRAINT reports_20110307_pkey PRIMARY KEY (id);


--
-- Name: reports_20110307_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110307
    ADD CONSTRAINT reports_20110307_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110314_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110314
    ADD CONSTRAINT reports_20110314_pkey PRIMARY KEY (id);


--
-- Name: reports_20110314_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110314
    ADD CONSTRAINT reports_20110314_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110321_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110321
    ADD CONSTRAINT reports_20110321_pkey PRIMARY KEY (id);


--
-- Name: reports_20110321_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110321
    ADD CONSTRAINT reports_20110321_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110328_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110328
    ADD CONSTRAINT reports_20110328_pkey PRIMARY KEY (id);


--
-- Name: reports_20110328_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110328
    ADD CONSTRAINT reports_20110328_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110404_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110404
    ADD CONSTRAINT reports_20110404_pkey PRIMARY KEY (id);


--
-- Name: reports_20110404_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110404
    ADD CONSTRAINT reports_20110404_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110411_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110411
    ADD CONSTRAINT reports_20110411_pkey PRIMARY KEY (id);


--
-- Name: reports_20110411_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110411
    ADD CONSTRAINT reports_20110411_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110418_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110418
    ADD CONSTRAINT reports_20110418_pkey PRIMARY KEY (id);


--
-- Name: reports_20110418_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110418
    ADD CONSTRAINT reports_20110418_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110425_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110425
    ADD CONSTRAINT reports_20110425_pkey PRIMARY KEY (id);


--
-- Name: reports_20110425_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110425
    ADD CONSTRAINT reports_20110425_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110502_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110502
    ADD CONSTRAINT reports_20110502_pkey PRIMARY KEY (id);


--
-- Name: reports_20110502_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110502
    ADD CONSTRAINT reports_20110502_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110509_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110509
    ADD CONSTRAINT reports_20110509_pkey PRIMARY KEY (id);


--
-- Name: reports_20110509_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110509
    ADD CONSTRAINT reports_20110509_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110516_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110516
    ADD CONSTRAINT reports_20110516_pkey PRIMARY KEY (id);


--
-- Name: reports_20110516_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110516
    ADD CONSTRAINT reports_20110516_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110523_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110523
    ADD CONSTRAINT reports_20110523_pkey PRIMARY KEY (id);


--
-- Name: reports_20110523_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110523
    ADD CONSTRAINT reports_20110523_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110530_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110530
    ADD CONSTRAINT reports_20110530_pkey PRIMARY KEY (id);


--
-- Name: reports_20110530_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110530
    ADD CONSTRAINT reports_20110530_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110606_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110606
    ADD CONSTRAINT reports_20110606_pkey PRIMARY KEY (id);


--
-- Name: reports_20110606_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110606
    ADD CONSTRAINT reports_20110606_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110613_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110613
    ADD CONSTRAINT reports_20110613_pkey PRIMARY KEY (id);


--
-- Name: reports_20110613_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110613
    ADD CONSTRAINT reports_20110613_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110620_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110620
    ADD CONSTRAINT reports_20110620_pkey PRIMARY KEY (id);


--
-- Name: reports_20110620_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110620
    ADD CONSTRAINT reports_20110620_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110627_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110627
    ADD CONSTRAINT reports_20110627_pkey PRIMARY KEY (id);


--
-- Name: reports_20110627_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110627
    ADD CONSTRAINT reports_20110627_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110704_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110704
    ADD CONSTRAINT reports_20110704_pkey PRIMARY KEY (id);


--
-- Name: reports_20110704_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110704
    ADD CONSTRAINT reports_20110704_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110711_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110711
    ADD CONSTRAINT reports_20110711_pkey PRIMARY KEY (id);


--
-- Name: reports_20110711_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110711
    ADD CONSTRAINT reports_20110711_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110718_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110718
    ADD CONSTRAINT reports_20110718_pkey PRIMARY KEY (id);


--
-- Name: reports_20110718_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110718
    ADD CONSTRAINT reports_20110718_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110725_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110725
    ADD CONSTRAINT reports_20110725_pkey PRIMARY KEY (id);


--
-- Name: reports_20110725_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110725
    ADD CONSTRAINT reports_20110725_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110801_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110801
    ADD CONSTRAINT reports_20110801_pkey PRIMARY KEY (id);


--
-- Name: reports_20110801_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110801
    ADD CONSTRAINT reports_20110801_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110808_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110808
    ADD CONSTRAINT reports_20110808_pkey PRIMARY KEY (id);


--
-- Name: reports_20110808_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110808
    ADD CONSTRAINT reports_20110808_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110815_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110815
    ADD CONSTRAINT reports_20110815_pkey PRIMARY KEY (id);


--
-- Name: reports_20110815_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110815
    ADD CONSTRAINT reports_20110815_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110822_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110822
    ADD CONSTRAINT reports_20110822_pkey PRIMARY KEY (id);


--
-- Name: reports_20110822_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110822
    ADD CONSTRAINT reports_20110822_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110829_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110829
    ADD CONSTRAINT reports_20110829_pkey PRIMARY KEY (id);


--
-- Name: reports_20110829_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110829
    ADD CONSTRAINT reports_20110829_unique_uuid UNIQUE (uuid);


--
-- Name: reports_20110905_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110905
    ADD CONSTRAINT reports_20110905_pkey PRIMARY KEY (id);


--
-- Name: reports_20110905_unique_uuid; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_20110905
    ADD CONSTRAINT reports_20110905_unique_uuid UNIQUE (uuid);


--
-- Name: reports_duplicates_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY reports_duplicates
    ADD CONSTRAINT reports_duplicates_pkey PRIMARY KEY (uuid);


--
-- Name: server_status_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY server_status
    ADD CONSTRAINT server_status_pkey PRIMARY KEY (id);


--
-- Name: session_id_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY sessions
    ADD CONSTRAINT session_id_pkey PRIMARY KEY (session_id);


--
-- Name: signature_bugs_rollup_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY signature_bugs_rollup
    ADD CONSTRAINT signature_bugs_rollup_pkey PRIMARY KEY (signature_id);


--
-- Name: signature_first_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY signature_first
    ADD CONSTRAINT signature_first_key PRIMARY KEY (signature, productdims_id, osdims_id);


--
-- Name: signature_productdims_signature_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY signature_productdims
    ADD CONSTRAINT signature_productdims_signature_key UNIQUE (signature, productdims_id);


--
-- Name: signature_products_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY signature_products
    ADD CONSTRAINT signature_products_key PRIMARY KEY (signature_id, product_version_id);


--
-- Name: signature_products_rollup_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY signature_products_rollup
    ADD CONSTRAINT signature_products_rollup_key PRIMARY KEY (signature_id, product_name);


--
-- Name: signatures_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY signatures
    ADD CONSTRAINT signatures_pkey PRIMARY KEY (signature_id);

ALTER TABLE signatures CLUSTER ON signatures_pkey;


--
-- Name: signatures_signature_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY signatures
    ADD CONSTRAINT signatures_signature_key UNIQUE (signature);


--
-- Name: tcbs_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY tcbs
    ADD CONSTRAINT tcbs_key PRIMARY KEY (signature_id, report_date, product_version_id, process_type, release_channel);


--
-- Name: top_crashes_by_signature2_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY top_crashes_by_signature
    ADD CONSTRAINT top_crashes_by_signature2_pkey PRIMARY KEY (id);


--
-- Name: top_crashes_by_url2_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY top_crashes_by_url
    ADD CONSTRAINT top_crashes_by_url2_pkey PRIMARY KEY (id);


--
-- Name: top_crashes_by_url_signature2_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY top_crashes_by_url_signature
    ADD CONSTRAINT top_crashes_by_url_signature2_pkey PRIMARY KEY (top_crashes_by_url_id, signature);


--
-- Name: topcrashurlfactsreports_pkey1; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY topcrashurlfactsreports
    ADD CONSTRAINT topcrashurlfactsreports_pkey1 PRIMARY KEY (id);


--
-- Name: urldims_pkey1; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY urldims
    ADD CONSTRAINT urldims_pkey1 PRIMARY KEY (id);


--
-- Name: builds_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE UNIQUE INDEX builds_key ON builds USING btree (product, version, platform, buildid);


--
-- Name: email_campaigns_product_signature_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX email_campaigns_product_signature_key ON email_campaigns USING btree (product, signature);


--
-- Name: extensions_20100607_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100607_report_id_date_key ON extensions_20100607 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100614_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100614_report_id_date_key ON extensions_20100614 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100621_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100621_report_id_date_key ON extensions_20100621 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100628_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100628_report_id_date_key ON extensions_20100628 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100705_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100705_report_id_date_key ON extensions_20100705 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100712_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100712_report_id_date_key ON extensions_20100712 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100719_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100719_report_id_date_key ON extensions_20100719 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100726_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100726_report_id_date_key ON extensions_20100726 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100802_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100802_report_id_date_key ON extensions_20100802 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100809_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100809_report_id_date_key ON extensions_20100809 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100816_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100816_report_id_date_key ON extensions_20100816 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100823_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100823_report_id_date_key ON extensions_20100823 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100830_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100830_report_id_date_key ON extensions_20100830 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100906_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100906_report_id_date_key ON extensions_20100906 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100913_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100913_report_id_date_key ON extensions_20100913 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100920_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100920_report_id_date_key ON extensions_20100920 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20100927_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20100927_report_id_date_key ON extensions_20100927 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101004_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101004_report_id_date_key ON extensions_20101004 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101011_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101011_report_id_date_key ON extensions_20101011 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101018_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101018_report_id_date_key ON extensions_20101018 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101025_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101025_report_id_date_key ON extensions_20101025 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101101_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101101_report_id_date_key ON extensions_20101101 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101108_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101108_report_id_date_key ON extensions_20101108 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101115_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101115_report_id_date_key ON extensions_20101115 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101122_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101122_report_id_date_key ON extensions_20101122 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101129_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101129_report_id_date_key ON extensions_20101129 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101206_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101206_report_id_date_key ON extensions_20101206 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101213_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101213_report_id_date_key ON extensions_20101213 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101220_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101220_report_id_date_key ON extensions_20101220 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20101227_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20101227_report_id_date_key ON extensions_20101227 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110103_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110103_report_id_date_key ON extensions_20110103 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110110_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110110_report_id_date_key ON extensions_20110110 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110117_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110117_report_id_date_key ON extensions_20110117 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110124_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110124_report_id_date_key ON extensions_20110124 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110131_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110131_report_id_date_key ON extensions_20110131 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110207_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110207_report_id_date_key ON extensions_20110207 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110214_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110214_report_id_date_key ON extensions_20110214 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110221_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110221_report_id_date_key ON extensions_20110221 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110228_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110228_report_id_date_key ON extensions_20110228 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110307_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110307_report_id_date_key ON extensions_20110307 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110314_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110314_report_id_date_key ON extensions_20110314 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110321_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110321_report_id_date_key ON extensions_20110321 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110328_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110328_report_id_date_key ON extensions_20110328 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110404_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110404_report_id_date_key ON extensions_20110404 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110411_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110411_report_id_date_key ON extensions_20110411 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110418_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110418_report_id_date_key ON extensions_20110418 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110425_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110425_report_id_date_key ON extensions_20110425 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110502_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110502_report_id_date_key ON extensions_20110502 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110509_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110509_report_id_date_key ON extensions_20110509 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110516_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110516_report_id_date_key ON extensions_20110516 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110523_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110523_report_id_date_key ON extensions_20110523 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110530_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110530_report_id_date_key ON extensions_20110530 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110606_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110606_report_id_date_key ON extensions_20110606 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110613_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110613_report_id_date_key ON extensions_20110613 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110620_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110620_report_id_date_key ON extensions_20110620 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110627_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110627_report_id_date_key ON extensions_20110627 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110704_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110704_extension_id_extension_version_idx ON extensions_20110704 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110704_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110704_report_id_date_key ON extensions_20110704 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110711_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110711_extension_id_extension_version_idx ON extensions_20110711 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110711_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110711_report_id_date_key ON extensions_20110711 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110718_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110718_extension_id_extension_version_idx ON extensions_20110718 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110718_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110718_report_id_date_key ON extensions_20110718 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110725_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110725_extension_id_extension_version_idx ON extensions_20110725 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110725_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110725_report_id_date_key ON extensions_20110725 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110801_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110801_extension_id_extension_version_idx ON extensions_20110801 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110801_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110801_report_id_date_key ON extensions_20110801 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110808_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110808_extension_id_extension_version_idx ON extensions_20110808 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110808_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110808_report_id_date_key ON extensions_20110808 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110815_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110815_extension_id_extension_version_idx ON extensions_20110815 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110815_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110815_report_id_date_key ON extensions_20110815 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110822_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110822_extension_id_extension_version_idx ON extensions_20110822 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110822_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110822_report_id_date_key ON extensions_20110822 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110829_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110829_extension_id_extension_version_idx ON extensions_20110829 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110829_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110829_report_id_date_key ON extensions_20110829 USING btree (report_id, date_processed, extension_key);


--
-- Name: extensions_20110905_extension_id_extension_version_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110905_extension_id_extension_version_idx ON extensions_20110905 USING btree (extension_id, extension_version);


--
-- Name: extensions_20110905_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX extensions_20110905_report_id_date_key ON extensions_20110905 USING btree (report_id, date_processed, extension_key);


--
-- Name: frames_20100607_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100607_report_id_date_key ON frames_20100607 USING btree (report_id, date_processed);


--
-- Name: frames_20100614_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100614_report_id_date_key ON frames_20100614 USING btree (report_id, date_processed);


--
-- Name: frames_20100621_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100621_report_id_date_key ON frames_20100621 USING btree (report_id, date_processed);


--
-- Name: frames_20100628_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100628_report_id_date_key ON frames_20100628 USING btree (report_id, date_processed);


--
-- Name: frames_20100705_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100705_report_id_date_key ON frames_20100705 USING btree (report_id, date_processed);


--
-- Name: frames_20100712_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100712_report_id_date_key ON frames_20100712 USING btree (report_id, date_processed);


--
-- Name: frames_20100719_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100719_report_id_date_key ON frames_20100719 USING btree (report_id, date_processed);


--
-- Name: frames_20100726_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100726_report_id_date_key ON frames_20100726 USING btree (report_id, date_processed);


--
-- Name: frames_20100802_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100802_report_id_date_key ON frames_20100802 USING btree (report_id, date_processed);


--
-- Name: frames_20100809_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100809_report_id_date_key ON frames_20100809 USING btree (report_id, date_processed);


--
-- Name: frames_20100816_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100816_report_id_date_key ON frames_20100816 USING btree (report_id, date_processed);


--
-- Name: frames_20100823_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100823_report_id_date_key ON frames_20100823 USING btree (report_id, date_processed);


--
-- Name: frames_20100830_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100830_report_id_date_key ON frames_20100830 USING btree (report_id, date_processed);


--
-- Name: frames_20100906_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100906_report_id_date_key ON frames_20100906 USING btree (report_id, date_processed);


--
-- Name: frames_20100913_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100913_report_id_date_key ON frames_20100913 USING btree (report_id, date_processed);


--
-- Name: frames_20100920_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100920_report_id_date_key ON frames_20100920 USING btree (report_id, date_processed);


--
-- Name: frames_20100927_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20100927_report_id_date_key ON frames_20100927 USING btree (report_id, date_processed);


--
-- Name: frames_20101004_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101004_report_id_date_key ON frames_20101004 USING btree (report_id, date_processed);


--
-- Name: frames_20101011_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101011_report_id_date_key ON frames_20101011 USING btree (report_id, date_processed);


--
-- Name: frames_20101018_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101018_report_id_date_key ON frames_20101018 USING btree (report_id, date_processed);


--
-- Name: frames_20101025_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101025_report_id_date_key ON frames_20101025 USING btree (report_id, date_processed);


--
-- Name: frames_20101101_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101101_report_id_date_key ON frames_20101101 USING btree (report_id, date_processed);


--
-- Name: frames_20101108_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101108_report_id_date_key ON frames_20101108 USING btree (report_id, date_processed);


--
-- Name: frames_20101115_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101115_report_id_date_key ON frames_20101115 USING btree (report_id, date_processed);


--
-- Name: frames_20101122_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101122_report_id_date_key ON frames_20101122 USING btree (report_id, date_processed);


--
-- Name: frames_20101129_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101129_report_id_date_key ON frames_20101129 USING btree (report_id, date_processed);


--
-- Name: frames_20101206_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101206_report_id_date_key ON frames_20101206 USING btree (report_id, date_processed);


--
-- Name: frames_20101213_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101213_report_id_date_key ON frames_20101213 USING btree (report_id, date_processed);


--
-- Name: frames_20101220_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101220_report_id_date_key ON frames_20101220 USING btree (report_id, date_processed);


--
-- Name: frames_20101227_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20101227_report_id_date_key ON frames_20101227 USING btree (report_id, date_processed);


--
-- Name: frames_20110103_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110103_report_id_date_key ON frames_20110103 USING btree (report_id, date_processed);


--
-- Name: frames_20110110_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110110_report_id_date_key ON frames_20110110 USING btree (report_id, date_processed);


--
-- Name: frames_20110117_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110117_report_id_date_key ON frames_20110117 USING btree (report_id, date_processed);


--
-- Name: frames_20110124_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110124_report_id_date_key ON frames_20110124 USING btree (report_id, date_processed);


--
-- Name: frames_20110131_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110131_report_id_date_key ON frames_20110131 USING btree (report_id, date_processed);


--
-- Name: frames_20110207_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110207_report_id_date_key ON frames_20110207 USING btree (report_id, date_processed);


--
-- Name: frames_20110214_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110214_report_id_date_key ON frames_20110214 USING btree (report_id, date_processed);


--
-- Name: frames_20110221_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110221_report_id_date_key ON frames_20110221 USING btree (report_id, date_processed);


--
-- Name: frames_20110228_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110228_report_id_date_key ON frames_20110228 USING btree (report_id, date_processed);


--
-- Name: frames_20110307_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110307_report_id_date_key ON frames_20110307 USING btree (report_id, date_processed);


--
-- Name: frames_20110314_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110314_report_id_date_key ON frames_20110314 USING btree (report_id, date_processed);


--
-- Name: frames_20110321_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110321_report_id_date_key ON frames_20110321 USING btree (report_id, date_processed);


--
-- Name: frames_20110328_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110328_report_id_date_key ON frames_20110328 USING btree (report_id, date_processed);


--
-- Name: frames_20110404_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110404_report_id_date_key ON frames_20110404 USING btree (report_id, date_processed);


--
-- Name: frames_20110411_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110411_report_id_date_key ON frames_20110411 USING btree (report_id, date_processed);


--
-- Name: frames_20110418_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110418_report_id_date_key ON frames_20110418 USING btree (report_id, date_processed);


--
-- Name: frames_20110425_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110425_report_id_date_key ON frames_20110425 USING btree (report_id, date_processed);


--
-- Name: frames_20110502_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110502_report_id_date_key ON frames_20110502 USING btree (report_id, date_processed);


--
-- Name: frames_20110509_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110509_report_id_date_key ON frames_20110509 USING btree (report_id, date_processed);


--
-- Name: frames_20110516_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110516_report_id_date_key ON frames_20110516 USING btree (report_id, date_processed);


--
-- Name: frames_20110523_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110523_report_id_date_key ON frames_20110523 USING btree (report_id, date_processed);


--
-- Name: frames_20110530_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110530_report_id_date_key ON frames_20110530 USING btree (report_id, date_processed);


--
-- Name: frames_20110606_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110606_report_id_date_key ON frames_20110606 USING btree (report_id, date_processed);


--
-- Name: frames_20110613_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110613_report_id_date_key ON frames_20110613 USING btree (report_id, date_processed);


--
-- Name: frames_20110620_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110620_report_id_date_key ON frames_20110620 USING btree (report_id, date_processed);


--
-- Name: frames_20110627_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110627_report_id_date_key ON frames_20110627 USING btree (report_id, date_processed);


--
-- Name: frames_20110704_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110704_report_id_date_key ON frames_20110704 USING btree (report_id, date_processed);


--
-- Name: frames_20110711_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110711_report_id_date_key ON frames_20110711 USING btree (report_id, date_processed);


--
-- Name: frames_20110718_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110718_report_id_date_key ON frames_20110718 USING btree (report_id, date_processed);


--
-- Name: frames_20110725_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110725_report_id_date_key ON frames_20110725 USING btree (report_id, date_processed);


--
-- Name: frames_20110801_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110801_report_id_date_key ON frames_20110801 USING btree (report_id, date_processed);


--
-- Name: frames_20110808_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110808_report_id_date_key ON frames_20110808 USING btree (report_id, date_processed);


--
-- Name: frames_20110815_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110815_report_id_date_key ON frames_20110815 USING btree (report_id, date_processed);


--
-- Name: frames_20110822_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110822_report_id_date_key ON frames_20110822 USING btree (report_id, date_processed);


--
-- Name: frames_20110829_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110829_report_id_date_key ON frames_20110829 USING btree (report_id, date_processed);


--
-- Name: frames_20110905_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX frames_20110905_report_id_date_key ON frames_20110905 USING btree (report_id, date_processed);


--
-- Name: idx_bug_associations_bug_id; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX idx_bug_associations_bug_id ON bug_associations USING btree (bug_id);


--
-- Name: idx_server_status_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX idx_server_status_date ON server_status USING btree (date_created, id);


--
-- Name: jobs_completeddatetime_queueddatetime_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX jobs_completeddatetime_queueddatetime_key ON jobs USING btree (completeddatetime, queueddatetime);


--
-- Name: jobs_owner_starteddatetime_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX jobs_owner_starteddatetime_key ON jobs USING btree (owner, starteddatetime);

ALTER TABLE jobs CLUSTER ON jobs_owner_starteddatetime_key;


--
-- Name: osdims_name_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX osdims_name_version_key ON osdims USING btree (os_name, os_version);


--
-- Name: plugins_reports_20100607_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100607_report_id_date_key ON plugins_reports_20100607 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100614_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100614_report_id_date_key ON plugins_reports_20100614 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100621_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100621_report_id_date_key ON plugins_reports_20100621 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100628_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100628_report_id_date_key ON plugins_reports_20100628 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100705_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100705_report_id_date_key ON plugins_reports_20100705 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100712_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100712_report_id_date_key ON plugins_reports_20100712 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100719_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100719_report_id_date_key ON plugins_reports_20100719 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100726_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100726_report_id_date_key ON plugins_reports_20100726 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100802_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100802_report_id_date_key ON plugins_reports_20100802 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100809_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100809_report_id_date_key ON plugins_reports_20100809 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100816_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100816_report_id_date_key ON plugins_reports_20100816 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100823_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100823_report_id_date_key ON plugins_reports_20100823 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100830_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100830_report_id_date_key ON plugins_reports_20100830 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100906_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100906_report_id_date_key ON plugins_reports_20100906 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100913_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100913_report_id_date_key ON plugins_reports_20100913 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100920_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100920_report_id_date_key ON plugins_reports_20100920 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20100927_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20100927_report_id_date_key ON plugins_reports_20100927 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101004_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101004_report_id_date_key ON plugins_reports_20101004 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101011_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101011_report_id_date_key ON plugins_reports_20101011 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101018_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101018_report_id_date_key ON plugins_reports_20101018 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101025_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101025_report_id_date_key ON plugins_reports_20101025 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101101_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101101_report_id_date_key ON plugins_reports_20101101 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101108_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101108_report_id_date_key ON plugins_reports_20101108 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101115_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101115_report_id_date_key ON plugins_reports_20101115 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101122_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101122_report_id_date_key ON plugins_reports_20101122 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101129_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101129_report_id_date_key ON plugins_reports_20101129 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101206_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101206_report_id_date_key ON plugins_reports_20101206 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101213_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101213_report_id_date_key ON plugins_reports_20101213 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101220_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101220_report_id_date_key ON plugins_reports_20101220 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20101227_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20101227_report_id_date_key ON plugins_reports_20101227 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110103_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110103_report_id_date_key ON plugins_reports_20110103 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110110_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110110_report_id_date_key ON plugins_reports_20110110 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110117_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110117_report_id_date_key ON plugins_reports_20110117 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110124_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110124_report_id_date_key ON plugins_reports_20110124 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110131_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110131_report_id_date_key ON plugins_reports_20110131 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110207_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110207_report_id_date_key ON plugins_reports_20110207 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110214_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110214_report_id_date_key ON plugins_reports_20110214 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110221_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110221_report_id_date_key ON plugins_reports_20110221 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110228_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110228_report_id_date_key ON plugins_reports_20110228 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110307_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110307_report_id_date_key ON plugins_reports_20110307 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110314_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110314_report_id_date_key ON plugins_reports_20110314 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110321_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110321_report_id_date_key ON plugins_reports_20110321 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110328_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110328_report_id_date_key ON plugins_reports_20110328 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110404_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110404_report_id_date_key ON plugins_reports_20110404 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110411_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110411_report_id_date_key ON plugins_reports_20110411 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110418_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110418_report_id_date_key ON plugins_reports_20110418 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110425_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110425_report_id_date_key ON plugins_reports_20110425 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110502_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110502_report_id_date_key ON plugins_reports_20110502 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110509_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110509_report_id_date_key ON plugins_reports_20110509 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110516_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110516_report_id_date_key ON plugins_reports_20110516 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110523_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110523_report_id_date_key ON plugins_reports_20110523 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110530_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110530_report_id_date_key ON plugins_reports_20110530 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110606_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110606_report_id_date_key ON plugins_reports_20110606 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110613_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110613_report_id_date_key ON plugins_reports_20110613 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110620_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110620_report_id_date_key ON plugins_reports_20110620 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110627_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110627_report_id_date_key ON plugins_reports_20110627 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110704_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110704_report_id_date_key ON plugins_reports_20110704 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110711_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110711_report_id_date_key ON plugins_reports_20110711 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110718_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110718_report_id_date_key ON plugins_reports_20110718 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110725_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110725_report_id_date_key ON plugins_reports_20110725 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110801_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110801_report_id_date_key ON plugins_reports_20110801 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110808_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110808_report_id_date_key ON plugins_reports_20110808 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110815_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110815_report_id_date_key ON plugins_reports_20110815 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110822_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110822_report_id_date_key ON plugins_reports_20110822 USING btree (report_id, date_processed, plugin_id);


--
-- Name: plugins_reports_20110829_report_id_date_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX plugins_reports_20110829_report_id_date_key ON plugins_reports_20110829 USING btree (report_id, date_processed, plugin_id);


--
-- Name: product_version_unique_beta; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE UNIQUE INDEX product_version_unique_beta ON product_versions USING btree (product_name, major_version, beta_number) WHERE (beta_number IS NOT NULL);


--
-- Name: product_versions_major_version; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX product_versions_major_version ON product_versions USING btree (major_version);


--
-- Name: product_versions_product_name; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX product_versions_product_name ON product_versions USING btree (product_name);


--
-- Name: product_versions_version_sort; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX product_versions_version_sort ON product_versions USING btree (version_sort);


--
-- Name: product_visibility_end_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX product_visibility_end_date ON product_visibility USING btree (end_date);


--
-- Name: product_visibility_start_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX product_visibility_start_date ON product_visibility USING btree (start_date);


--
-- Name: productdims_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE UNIQUE INDEX productdims_product_version_key ON productdims USING btree (product, version);


--
-- Name: productdims_sort_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX productdims_sort_key ON productdims USING btree (product, sort_key);


--
-- Name: r_b_i; Type: INDEX; Schema: public; Owner: postgres; Tablespace:
--

CREATE INDEX r_b_i ON releasechannel_backfill USING btree (uuid);


--
-- Name: raw_adu_1_idx; Type: INDEX; Schema: public; Owner: breakpad_metrics; Tablespace:
--

CREATE INDEX raw_adu_1_idx ON raw_adu USING btree (date, product_name, product_version, product_os_platform, product_os_version);


--
-- Name: reports_20100607_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100607_build_key ON reports_20100607 USING btree (build);


--
-- Name: reports_20100607_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100607_date_processed_key ON reports_20100607 USING btree (date_processed);


--
-- Name: reports_20100607_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100607_product_version_key ON reports_20100607 USING btree (product, version);


--
-- Name: reports_20100607_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100607_reason ON reports_20100607 USING btree (reason);


--
-- Name: reports_20100607_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100607_signature_date_processed_build_key ON reports_20100607 USING btree (signature, date_processed, build);


--
-- Name: reports_20100607_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100607_url_key ON reports_20100607 USING btree (url);


--
-- Name: reports_20100614_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100614_build_key ON reports_20100614 USING btree (build);


--
-- Name: reports_20100614_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100614_date_processed_key ON reports_20100614 USING btree (date_processed);


--
-- Name: reports_20100614_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100614_product_version_key ON reports_20100614 USING btree (product, version);


--
-- Name: reports_20100614_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100614_reason ON reports_20100614 USING btree (reason);


--
-- Name: reports_20100614_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100614_signature_date_processed_build_key ON reports_20100614 USING btree (signature, date_processed, build);


--
-- Name: reports_20100614_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100614_url_key ON reports_20100614 USING btree (url);


--
-- Name: reports_20100621_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100621_build_key ON reports_20100621 USING btree (build);


--
-- Name: reports_20100621_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100621_date_processed_key ON reports_20100621 USING btree (date_processed);


--
-- Name: reports_20100621_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100621_product_version_key ON reports_20100621 USING btree (product, version);


--
-- Name: reports_20100621_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100621_reason ON reports_20100621 USING btree (reason);


--
-- Name: reports_20100621_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100621_signature_date_processed_build_key ON reports_20100621 USING btree (signature, date_processed, build);


--
-- Name: reports_20100621_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100621_url_key ON reports_20100621 USING btree (url);


--
-- Name: reports_20100628_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100628_build_key ON reports_20100628 USING btree (build);


--
-- Name: reports_20100628_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100628_date_processed_key ON reports_20100628 USING btree (date_processed);


--
-- Name: reports_20100628_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100628_hangid_idx ON reports_20100628 USING btree (hangid);


--
-- Name: reports_20100628_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100628_product_version_key ON reports_20100628 USING btree (product, version);


--
-- Name: reports_20100628_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100628_reason ON reports_20100628 USING btree (reason);


--
-- Name: reports_20100628_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100628_signature_date_processed_build_key ON reports_20100628 USING btree (signature, date_processed, build);


--
-- Name: reports_20100628_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100628_url_key ON reports_20100628 USING btree (url);


--
-- Name: reports_20100705_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100705_build_key ON reports_20100705 USING btree (build);


--
-- Name: reports_20100705_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100705_date_processed_key ON reports_20100705 USING btree (date_processed);


--
-- Name: reports_20100705_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100705_hangid_idx ON reports_20100705 USING btree (hangid);


--
-- Name: reports_20100705_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100705_product_version_key ON reports_20100705 USING btree (product, version);


--
-- Name: reports_20100705_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100705_reason ON reports_20100705 USING btree (reason);


--
-- Name: reports_20100705_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100705_signature_date_processed_build_key ON reports_20100705 USING btree (signature, date_processed, build);


--
-- Name: reports_20100705_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100705_url_key ON reports_20100705 USING btree (url);


--
-- Name: reports_20100712_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100712_build_key ON reports_20100712 USING btree (build);


--
-- Name: reports_20100712_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100712_date_processed_key ON reports_20100712 USING btree (date_processed);


--
-- Name: reports_20100712_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100712_hangid_idx ON reports_20100712 USING btree (hangid);


--
-- Name: reports_20100712_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100712_product_version_key ON reports_20100712 USING btree (product, version);


--
-- Name: reports_20100712_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100712_reason ON reports_20100712 USING btree (reason);


--
-- Name: reports_20100712_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100712_signature_date_processed_build_key ON reports_20100712 USING btree (signature, date_processed, build);


--
-- Name: reports_20100712_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100712_url_key ON reports_20100712 USING btree (url);


--
-- Name: reports_20100719_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100719_build_key ON reports_20100719 USING btree (build);


--
-- Name: reports_20100719_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100719_date_processed_key ON reports_20100719 USING btree (date_processed);


--
-- Name: reports_20100719_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100719_product_version_key ON reports_20100719 USING btree (product, version);


--
-- Name: reports_20100719_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100719_reason ON reports_20100719 USING btree (reason);


--
-- Name: reports_20100719_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100719_signature_date_processed_build_key ON reports_20100719 USING btree (signature, date_processed, build);


--
-- Name: reports_20100719_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100719_url_key ON reports_20100719 USING btree (url);


--
-- Name: reports_20100726_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100726_build_key ON reports_20100726 USING btree (build);


--
-- Name: reports_20100726_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100726_date_processed_key ON reports_20100726 USING btree (date_processed);


--
-- Name: reports_20100726_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100726_hangid_idx ON reports_20100726 USING btree (hangid);


--
-- Name: reports_20100726_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100726_product_version_key ON reports_20100726 USING btree (product, version);


--
-- Name: reports_20100726_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100726_reason ON reports_20100726 USING btree (reason);


--
-- Name: reports_20100726_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100726_signature_date_processed_build_key ON reports_20100726 USING btree (signature, date_processed, build);


--
-- Name: reports_20100726_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100726_url_key ON reports_20100726 USING btree (url);


--
-- Name: reports_20100802_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100802_build_key ON reports_20100802 USING btree (build);


--
-- Name: reports_20100802_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100802_date_processed_key ON reports_20100802 USING btree (date_processed);


--
-- Name: reports_20100802_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100802_hangid_idx ON reports_20100802 USING btree (hangid);


--
-- Name: reports_20100802_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100802_product_version_key ON reports_20100802 USING btree (product, version);


--
-- Name: reports_20100802_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100802_reason ON reports_20100802 USING btree (reason);


--
-- Name: reports_20100802_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100802_signature_date_processed_build_key ON reports_20100802 USING btree (signature, date_processed, build);


--
-- Name: reports_20100802_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100802_url_key ON reports_20100802 USING btree (url);


--
-- Name: reports_20100809_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100809_build_key ON reports_20100809 USING btree (build);


--
-- Name: reports_20100809_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100809_date_processed_key ON reports_20100809 USING btree (date_processed);


--
-- Name: reports_20100809_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100809_hangid_idx ON reports_20100809 USING btree (hangid);


--
-- Name: reports_20100809_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100809_product_version_key ON reports_20100809 USING btree (product, version);


--
-- Name: reports_20100809_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100809_reason ON reports_20100809 USING btree (reason);


--
-- Name: reports_20100809_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100809_signature_date_processed_build_key ON reports_20100809 USING btree (signature, date_processed, build);


--
-- Name: reports_20100809_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100809_url_key ON reports_20100809 USING btree (url);


--
-- Name: reports_20100816_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100816_build_key ON reports_20100816 USING btree (build);


--
-- Name: reports_20100816_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100816_date_processed_key ON reports_20100816 USING btree (date_processed);


--
-- Name: reports_20100816_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100816_hangid_idx ON reports_20100816 USING btree (hangid);


--
-- Name: reports_20100816_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100816_product_version_key ON reports_20100816 USING btree (product, version);


--
-- Name: reports_20100816_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100816_reason ON reports_20100816 USING btree (reason);


--
-- Name: reports_20100816_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100816_signature_date_processed_build_key ON reports_20100816 USING btree (signature, date_processed, build);


--
-- Name: reports_20100816_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100816_url_key ON reports_20100816 USING btree (url);


--
-- Name: reports_20100823_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100823_build_key ON reports_20100823 USING btree (build);


--
-- Name: reports_20100823_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100823_date_processed_key ON reports_20100823 USING btree (date_processed);


--
-- Name: reports_20100823_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100823_product_version_key ON reports_20100823 USING btree (product, version);


--
-- Name: reports_20100823_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100823_reason ON reports_20100823 USING btree (reason);


--
-- Name: reports_20100823_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100823_signature_date_processed_build_key ON reports_20100823 USING btree (signature, date_processed, build);


--
-- Name: reports_20100823_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100823_url_key ON reports_20100823 USING btree (url);


--
-- Name: reports_20100830_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100830_build_key ON reports_20100830 USING btree (build);


--
-- Name: reports_20100830_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100830_date_processed_key ON reports_20100830 USING btree (date_processed);


--
-- Name: reports_20100830_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100830_product_version_key ON reports_20100830 USING btree (product, version);


--
-- Name: reports_20100830_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100830_reason ON reports_20100830 USING btree (reason);


--
-- Name: reports_20100830_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100830_signature_date_processed_build_key ON reports_20100830 USING btree (signature, date_processed, build);


--
-- Name: reports_20100830_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100830_url_key ON reports_20100830 USING btree (url);


--
-- Name: reports_20100906_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100906_build_key ON reports_20100906 USING btree (build);


--
-- Name: reports_20100906_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100906_date_processed_key ON reports_20100906 USING btree (date_processed);


--
-- Name: reports_20100906_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100906_product_version_key ON reports_20100906 USING btree (product, version);


--
-- Name: reports_20100906_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100906_reason ON reports_20100906 USING btree (reason);


--
-- Name: reports_20100906_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100906_signature_date_processed_build_key ON reports_20100906 USING btree (signature, date_processed, build);


--
-- Name: reports_20100906_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100906_url_key ON reports_20100906 USING btree (url);


--
-- Name: reports_20100913_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100913_build_key ON reports_20100913 USING btree (build);


--
-- Name: reports_20100913_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100913_date_processed_key ON reports_20100913 USING btree (date_processed);


--
-- Name: reports_20100913_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100913_hangid_idx ON reports_20100913 USING btree (hangid);


--
-- Name: reports_20100913_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100913_product_version_key ON reports_20100913 USING btree (product, version);


--
-- Name: reports_20100913_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100913_reason ON reports_20100913 USING btree (reason);


--
-- Name: reports_20100913_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100913_signature_date_processed_build_key ON reports_20100913 USING btree (signature, date_processed, build);


--
-- Name: reports_20100913_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100913_url_key ON reports_20100913 USING btree (url);


--
-- Name: reports_20100920_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100920_build_key ON reports_20100920 USING btree (build);


--
-- Name: reports_20100920_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100920_date_processed_key ON reports_20100920 USING btree (date_processed);


--
-- Name: reports_20100920_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100920_product_version_key ON reports_20100920 USING btree (product, version);


--
-- Name: reports_20100920_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100920_reason ON reports_20100920 USING btree (reason);


--
-- Name: reports_20100920_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100920_signature_date_processed_build_key ON reports_20100920 USING btree (signature, date_processed, build);


--
-- Name: reports_20100920_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100920_url_key ON reports_20100920 USING btree (url);


--
-- Name: reports_20100927_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100927_build_key ON reports_20100927 USING btree (build);


--
-- Name: reports_20100927_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100927_date_processed_key ON reports_20100927 USING btree (date_processed);


--
-- Name: reports_20100927_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100927_product_version_key ON reports_20100927 USING btree (product, version);


--
-- Name: reports_20100927_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100927_reason ON reports_20100927 USING btree (reason);


--
-- Name: reports_20100927_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100927_signature_date_processed_build_key ON reports_20100927 USING btree (signature, date_processed, build);


--
-- Name: reports_20100927_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20100927_url_key ON reports_20100927 USING btree (url);


--
-- Name: reports_20101004_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101004_build_key ON reports_20101004 USING btree (build);


--
-- Name: reports_20101004_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101004_date_processed_key ON reports_20101004 USING btree (date_processed);


--
-- Name: reports_20101004_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101004_product_version_key ON reports_20101004 USING btree (product, version);


--
-- Name: reports_20101004_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101004_reason ON reports_20101004 USING btree (reason);


--
-- Name: reports_20101004_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101004_signature_date_processed_build_key ON reports_20101004 USING btree (signature, date_processed, build);


--
-- Name: reports_20101004_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101004_url_key ON reports_20101004 USING btree (url);


--
-- Name: reports_20101011_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101011_build_key ON reports_20101011 USING btree (build);


--
-- Name: reports_20101011_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101011_date_processed_key ON reports_20101011 USING btree (date_processed);


--
-- Name: reports_20101011_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101011_product_version_key ON reports_20101011 USING btree (product, version);


--
-- Name: reports_20101011_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101011_reason ON reports_20101011 USING btree (reason);


--
-- Name: reports_20101011_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101011_signature_date_processed_build_key ON reports_20101011 USING btree (signature, date_processed, build);


--
-- Name: reports_20101011_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101011_url_key ON reports_20101011 USING btree (url);


--
-- Name: reports_20101018_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101018_build_key ON reports_20101018 USING btree (build);


--
-- Name: reports_20101018_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101018_date_processed_key ON reports_20101018 USING btree (date_processed);


--
-- Name: reports_20101018_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101018_product_version_key ON reports_20101018 USING btree (product, version);


--
-- Name: reports_20101018_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101018_reason ON reports_20101018 USING btree (reason);


--
-- Name: reports_20101018_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101018_signature_date_processed_build_key ON reports_20101018 USING btree (signature, date_processed, build);


--
-- Name: reports_20101018_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101018_url_key ON reports_20101018 USING btree (url);


--
-- Name: reports_20101025_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101025_build_key ON reports_20101025 USING btree (build);


--
-- Name: reports_20101025_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101025_date_processed_key ON reports_20101025 USING btree (date_processed);


--
-- Name: reports_20101025_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101025_product_version_key ON reports_20101025 USING btree (product, version);


--
-- Name: reports_20101025_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101025_reason ON reports_20101025 USING btree (reason);


--
-- Name: reports_20101025_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101025_signature_date_processed_build_key ON reports_20101025 USING btree (signature, date_processed, build);


--
-- Name: reports_20101025_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101025_url_key ON reports_20101025 USING btree (url);


--
-- Name: reports_20101101_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101101_build_key ON reports_20101101 USING btree (build);


--
-- Name: reports_20101101_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101101_date_processed_key ON reports_20101101 USING btree (date_processed);


--
-- Name: reports_20101101_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101101_product_version_key ON reports_20101101 USING btree (product, version);


--
-- Name: reports_20101101_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101101_reason ON reports_20101101 USING btree (reason);


--
-- Name: reports_20101101_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101101_signature_date_processed_build_key ON reports_20101101 USING btree (signature, date_processed, build);


--
-- Name: reports_20101101_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101101_url_key ON reports_20101101 USING btree (url);


--
-- Name: reports_20101108_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101108_build_key ON reports_20101108 USING btree (build);


--
-- Name: reports_20101108_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101108_date_processed_key ON reports_20101108 USING btree (date_processed);


--
-- Name: reports_20101108_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101108_product_version_key ON reports_20101108 USING btree (product, version);


--
-- Name: reports_20101108_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101108_reason ON reports_20101108 USING btree (reason);


--
-- Name: reports_20101108_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101108_signature_date_processed_build_key ON reports_20101108 USING btree (signature, date_processed, build);


--
-- Name: reports_20101108_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101108_url_key ON reports_20101108 USING btree (url);


--
-- Name: reports_20101115_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101115_build_key ON reports_20101115 USING btree (build);


--
-- Name: reports_20101115_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101115_date_processed_key ON reports_20101115 USING btree (date_processed);


--
-- Name: reports_20101115_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101115_product_version_key ON reports_20101115 USING btree (product, version);


--
-- Name: reports_20101115_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101115_reason ON reports_20101115 USING btree (reason);


--
-- Name: reports_20101115_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101115_signature_date_processed_build_key ON reports_20101115 USING btree (signature, date_processed, build);


--
-- Name: reports_20101115_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101115_url_key ON reports_20101115 USING btree (url);


--
-- Name: reports_20101122_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101122_build_key ON reports_20101122 USING btree (build);


--
-- Name: reports_20101122_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101122_date_processed_key ON reports_20101122 USING btree (date_processed);


--
-- Name: reports_20101122_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101122_product_version_key ON reports_20101122 USING btree (product, version);


--
-- Name: reports_20101122_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101122_reason ON reports_20101122 USING btree (reason);


--
-- Name: reports_20101122_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101122_signature_date_processed_build_key ON reports_20101122 USING btree (signature, date_processed, build);


--
-- Name: reports_20101122_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101122_url_key ON reports_20101122 USING btree (url);


--
-- Name: reports_20101129_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101129_build_key ON reports_20101129 USING btree (build);


--
-- Name: reports_20101129_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101129_date_processed_key ON reports_20101129 USING btree (date_processed);


--
-- Name: reports_20101129_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101129_product_version_key ON reports_20101129 USING btree (product, version);


--
-- Name: reports_20101129_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101129_reason ON reports_20101129 USING btree (reason);


--
-- Name: reports_20101129_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101129_signature_date_processed_build_key ON reports_20101129 USING btree (signature, date_processed, build);


--
-- Name: reports_20101129_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101129_url_key ON reports_20101129 USING btree (url);


--
-- Name: reports_20101206_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101206_build_key ON reports_20101206 USING btree (build);


--
-- Name: reports_20101206_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101206_date_processed_key ON reports_20101206 USING btree (date_processed);


--
-- Name: reports_20101206_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101206_product_version_key ON reports_20101206 USING btree (product, version);


--
-- Name: reports_20101206_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101206_reason ON reports_20101206 USING btree (reason);


--
-- Name: reports_20101206_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101206_signature_date_processed_build_key ON reports_20101206 USING btree (signature, date_processed, build);


--
-- Name: reports_20101206_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101206_url_key ON reports_20101206 USING btree (url);


--
-- Name: reports_20101213_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101213_build_key ON reports_20101213 USING btree (build);


--
-- Name: reports_20101213_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101213_date_processed_key ON reports_20101213 USING btree (date_processed);


--
-- Name: reports_20101213_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101213_product_version_key ON reports_20101213 USING btree (product, version);


--
-- Name: reports_20101213_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101213_reason ON reports_20101213 USING btree (reason);


--
-- Name: reports_20101213_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101213_signature_date_processed_build_key ON reports_20101213 USING btree (signature, date_processed, build);


--
-- Name: reports_20101213_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101213_url_key ON reports_20101213 USING btree (url);


--
-- Name: reports_20101220_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101220_build_key ON reports_20101220 USING btree (build);


--
-- Name: reports_20101220_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101220_date_processed_key ON reports_20101220 USING btree (date_processed);


--
-- Name: reports_20101220_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101220_product_version_key ON reports_20101220 USING btree (product, version);


--
-- Name: reports_20101220_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101220_reason ON reports_20101220 USING btree (reason);


--
-- Name: reports_20101220_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101220_signature_date_processed_build_key ON reports_20101220 USING btree (signature, date_processed, build);


--
-- Name: reports_20101220_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101220_url_key ON reports_20101220 USING btree (url);


--
-- Name: reports_20101227_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101227_build_key ON reports_20101227 USING btree (build);


--
-- Name: reports_20101227_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101227_date_processed_key ON reports_20101227 USING btree (date_processed);


--
-- Name: reports_20101227_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101227_product_version_key ON reports_20101227 USING btree (product, version);


--
-- Name: reports_20101227_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101227_reason ON reports_20101227 USING btree (reason);


--
-- Name: reports_20101227_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101227_signature_date_processed_build_key ON reports_20101227 USING btree (signature, date_processed, build);


--
-- Name: reports_20101227_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20101227_url_key ON reports_20101227 USING btree (url);


--
-- Name: reports_20110103_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110103_build_key ON reports_20110103 USING btree (build);


--
-- Name: reports_20110103_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110103_date_processed_key ON reports_20110103 USING btree (date_processed);


--
-- Name: reports_20110103_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110103_product_version_key ON reports_20110103 USING btree (product, version);


--
-- Name: reports_20110103_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110103_reason ON reports_20110103 USING btree (reason);


--
-- Name: reports_20110103_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110103_signature_date_processed_build_key ON reports_20110103 USING btree (signature, date_processed, build);


--
-- Name: reports_20110103_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110103_url_key ON reports_20110103 USING btree (url);


--
-- Name: reports_20110110_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110110_build_key ON reports_20110110 USING btree (build);


--
-- Name: reports_20110110_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110110_date_processed_key ON reports_20110110 USING btree (date_processed);


--
-- Name: reports_20110110_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110110_hangid_idx ON reports_20110110 USING btree (hangid);


--
-- Name: reports_20110110_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110110_product_version_key ON reports_20110110 USING btree (product, version);


--
-- Name: reports_20110110_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110110_reason ON reports_20110110 USING btree (reason);


--
-- Name: reports_20110110_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110110_signature_date_processed_build_key ON reports_20110110 USING btree (signature, date_processed, build);


--
-- Name: reports_20110110_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110110_url_key ON reports_20110110 USING btree (url);


--
-- Name: reports_20110117_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110117_build_key ON reports_20110117 USING btree (build);


--
-- Name: reports_20110117_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110117_date_processed_key ON reports_20110117 USING btree (date_processed);


--
-- Name: reports_20110117_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110117_hangid_idx ON reports_20110117 USING btree (hangid);


--
-- Name: reports_20110117_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110117_product_version_key ON reports_20110117 USING btree (product, version);


--
-- Name: reports_20110117_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110117_reason ON reports_20110117 USING btree (reason);


--
-- Name: reports_20110117_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110117_signature_date_processed_build_key ON reports_20110117 USING btree (signature, date_processed, build);


--
-- Name: reports_20110117_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110117_url_key ON reports_20110117 USING btree (url);


--
-- Name: reports_20110124_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110124_build_key ON reports_20110124 USING btree (build);


--
-- Name: reports_20110124_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110124_date_processed_key ON reports_20110124 USING btree (date_processed);


--
-- Name: reports_20110124_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110124_hangid_idx ON reports_20110124 USING btree (hangid);


--
-- Name: reports_20110124_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110124_product_version_key ON reports_20110124 USING btree (product, version);


--
-- Name: reports_20110124_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110124_reason ON reports_20110124 USING btree (reason);


--
-- Name: reports_20110124_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110124_signature_date_processed_build_key ON reports_20110124 USING btree (signature, date_processed, build);


--
-- Name: reports_20110124_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110124_url_key ON reports_20110124 USING btree (url);


--
-- Name: reports_20110131_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110131_build_key ON reports_20110131 USING btree (build);


--
-- Name: reports_20110131_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110131_date_processed_key ON reports_20110131 USING btree (date_processed);


--
-- Name: reports_20110131_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110131_hangid_idx ON reports_20110131 USING btree (hangid);


--
-- Name: reports_20110131_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110131_product_version_key ON reports_20110131 USING btree (product, version);


--
-- Name: reports_20110131_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110131_reason ON reports_20110131 USING btree (reason);


--
-- Name: reports_20110131_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110131_signature_date_processed_build_key ON reports_20110131 USING btree (signature, date_processed, build);


--
-- Name: reports_20110131_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110131_url_key ON reports_20110131 USING btree (url);


--
-- Name: reports_20110207_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110207_build_key ON reports_20110207 USING btree (build);


--
-- Name: reports_20110207_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110207_date_processed_key ON reports_20110207 USING btree (date_processed);


--
-- Name: reports_20110207_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110207_hangid_idx ON reports_20110207 USING btree (hangid);


--
-- Name: reports_20110207_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110207_product_version_key ON reports_20110207 USING btree (product, version);


--
-- Name: reports_20110207_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110207_reason ON reports_20110207 USING btree (reason);


--
-- Name: reports_20110207_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110207_signature_date_processed_build_key ON reports_20110207 USING btree (signature, date_processed, build);


--
-- Name: reports_20110207_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110207_url_key ON reports_20110207 USING btree (url);


--
-- Name: reports_20110214_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110214_build_key ON reports_20110214 USING btree (build);


--
-- Name: reports_20110214_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110214_date_processed_key ON reports_20110214 USING btree (date_processed);


--
-- Name: reports_20110214_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110214_hangid_idx ON reports_20110214 USING btree (hangid);


--
-- Name: reports_20110214_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110214_product_version_key ON reports_20110214 USING btree (product, version);


--
-- Name: reports_20110214_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110214_reason ON reports_20110214 USING btree (reason);


--
-- Name: reports_20110214_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110214_signature_date_processed_build_key ON reports_20110214 USING btree (signature, date_processed, build);


--
-- Name: reports_20110214_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110214_url_key ON reports_20110214 USING btree (url);


--
-- Name: reports_20110221_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110221_build_key ON reports_20110221 USING btree (build);


--
-- Name: reports_20110221_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110221_date_processed_key ON reports_20110221 USING btree (date_processed);


--
-- Name: reports_20110221_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110221_hangid_idx ON reports_20110221 USING btree (hangid);


--
-- Name: reports_20110221_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110221_product_version_key ON reports_20110221 USING btree (product, version);


--
-- Name: reports_20110221_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110221_reason ON reports_20110221 USING btree (reason);


--
-- Name: reports_20110221_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110221_signature_date_processed_build_key ON reports_20110221 USING btree (signature, date_processed, build);


--
-- Name: reports_20110221_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110221_url_key ON reports_20110221 USING btree (url);


--
-- Name: reports_20110228_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110228_build_key ON reports_20110228 USING btree (build);


--
-- Name: reports_20110228_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110228_date_processed_key ON reports_20110228 USING btree (date_processed);


--
-- Name: reports_20110228_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110228_hangid_idx ON reports_20110228 USING btree (hangid);


--
-- Name: reports_20110228_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110228_product_version_key ON reports_20110228 USING btree (product, version);


--
-- Name: reports_20110228_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110228_reason ON reports_20110228 USING btree (reason);


--
-- Name: reports_20110228_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110228_signature_date_processed_build_key ON reports_20110228 USING btree (signature, date_processed, build);


--
-- Name: reports_20110228_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110228_url_key ON reports_20110228 USING btree (url);


--
-- Name: reports_20110307_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110307_build_key ON reports_20110307 USING btree (build);


--
-- Name: reports_20110307_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110307_date_processed_key ON reports_20110307 USING btree (date_processed);


--
-- Name: reports_20110307_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110307_hangid_idx ON reports_20110307 USING btree (hangid);


--
-- Name: reports_20110307_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110307_product_version_key ON reports_20110307 USING btree (product, version);


--
-- Name: reports_20110307_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110307_reason ON reports_20110307 USING btree (reason);


--
-- Name: reports_20110307_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110307_signature_date_processed_build_key ON reports_20110307 USING btree (signature, date_processed, build);


--
-- Name: reports_20110307_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110307_url_key ON reports_20110307 USING btree (url);


--
-- Name: reports_20110314_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110314_build_key ON reports_20110314 USING btree (build);


--
-- Name: reports_20110314_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110314_date_processed_key ON reports_20110314 USING btree (date_processed);


--
-- Name: reports_20110314_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110314_hangid_idx ON reports_20110314 USING btree (hangid);


--
-- Name: reports_20110314_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110314_product_version_key ON reports_20110314 USING btree (product, version);


--
-- Name: reports_20110314_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110314_reason ON reports_20110314 USING btree (reason);


--
-- Name: reports_20110314_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110314_signature_date_processed_build_key ON reports_20110314 USING btree (signature, date_processed, build);


--
-- Name: reports_20110314_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110314_url_key ON reports_20110314 USING btree (url);


--
-- Name: reports_20110321_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110321_build_key ON reports_20110321 USING btree (build);


--
-- Name: reports_20110321_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110321_date_processed_key ON reports_20110321 USING btree (date_processed);


--
-- Name: reports_20110321_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110321_hangid_idx ON reports_20110321 USING btree (hangid);


--
-- Name: reports_20110321_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110321_product_version_key ON reports_20110321 USING btree (product, version);


--
-- Name: reports_20110321_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110321_reason ON reports_20110321 USING btree (reason);


--
-- Name: reports_20110321_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110321_signature_date_processed_build_key ON reports_20110321 USING btree (signature, date_processed, build);


--
-- Name: reports_20110321_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110321_url_key ON reports_20110321 USING btree (url);


--
-- Name: reports_20110328_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110328_build_key ON reports_20110328 USING btree (build);


--
-- Name: reports_20110328_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110328_date_processed_key ON reports_20110328 USING btree (date_processed);


--
-- Name: reports_20110328_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110328_hangid_idx ON reports_20110328 USING btree (hangid);


--
-- Name: reports_20110328_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110328_product_version_key ON reports_20110328 USING btree (product, version);


--
-- Name: reports_20110328_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110328_reason ON reports_20110328 USING btree (reason);


--
-- Name: reports_20110328_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110328_signature_date_processed_build_key ON reports_20110328 USING btree (signature, date_processed, build);


--
-- Name: reports_20110328_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110328_url_key ON reports_20110328 USING btree (url);


--
-- Name: reports_20110404_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110404_build_key ON reports_20110404 USING btree (build);


--
-- Name: reports_20110404_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110404_date_processed_key ON reports_20110404 USING btree (date_processed);


--
-- Name: reports_20110404_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110404_hangid_idx ON reports_20110404 USING btree (hangid);


--
-- Name: reports_20110404_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110404_product_version_key ON reports_20110404 USING btree (product, version);


--
-- Name: reports_20110404_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110404_reason ON reports_20110404 USING btree (reason);


--
-- Name: reports_20110404_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110404_signature_date_processed_build_key ON reports_20110404 USING btree (signature, date_processed, build);


--
-- Name: reports_20110404_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110404_url_key ON reports_20110404 USING btree (url);


--
-- Name: reports_20110411_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110411_build_key ON reports_20110411 USING btree (build);


--
-- Name: reports_20110411_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110411_date_processed_key ON reports_20110411 USING btree (date_processed);


--
-- Name: reports_20110411_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110411_hangid_idx ON reports_20110411 USING btree (hangid);


--
-- Name: reports_20110411_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110411_product_version_key ON reports_20110411 USING btree (product, version);


--
-- Name: reports_20110411_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110411_reason ON reports_20110411 USING btree (reason);


--
-- Name: reports_20110411_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110411_signature_date_processed_build_key ON reports_20110411 USING btree (signature, date_processed, build);


--
-- Name: reports_20110411_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110411_url_key ON reports_20110411 USING btree (url);


--
-- Name: reports_20110418_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110418_build_key ON reports_20110418 USING btree (build);


--
-- Name: reports_20110418_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110418_date_processed_key ON reports_20110418 USING btree (date_processed);


--
-- Name: reports_20110418_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110418_hangid_idx ON reports_20110418 USING btree (hangid);


--
-- Name: reports_20110418_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110418_product_version_key ON reports_20110418 USING btree (product, version);


--
-- Name: reports_20110418_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110418_reason ON reports_20110418 USING btree (reason);


--
-- Name: reports_20110418_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110418_signature_date_processed_build_key ON reports_20110418 USING btree (signature, date_processed, build);


--
-- Name: reports_20110418_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110418_url_key ON reports_20110418 USING btree (url);


--
-- Name: reports_20110425_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110425_build_key ON reports_20110425 USING btree (build);


--
-- Name: reports_20110425_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110425_date_processed_key ON reports_20110425 USING btree (date_processed);


--
-- Name: reports_20110425_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110425_hangid_idx ON reports_20110425 USING btree (hangid);


--
-- Name: reports_20110425_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110425_product_version_key ON reports_20110425 USING btree (product, version);


--
-- Name: reports_20110425_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110425_reason ON reports_20110425 USING btree (reason);


--
-- Name: reports_20110425_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110425_signature_date_processed_build_key ON reports_20110425 USING btree (signature, date_processed, build);


--
-- Name: reports_20110425_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110425_url_key ON reports_20110425 USING btree (url);


--
-- Name: reports_20110502_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110502_build_key ON reports_20110502 USING btree (build);


--
-- Name: reports_20110502_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110502_date_processed_key ON reports_20110502 USING btree (date_processed);


--
-- Name: reports_20110502_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110502_hangid_idx ON reports_20110502 USING btree (hangid);


--
-- Name: reports_20110502_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110502_product_version_key ON reports_20110502 USING btree (product, version);


--
-- Name: reports_20110502_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110502_reason ON reports_20110502 USING btree (reason);


--
-- Name: reports_20110502_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110502_signature_date_processed_build_key ON reports_20110502 USING btree (signature, date_processed, build);


--
-- Name: reports_20110502_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110502_url_key ON reports_20110502 USING btree (url);


--
-- Name: reports_20110509_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110509_build_key ON reports_20110509 USING btree (build);


--
-- Name: reports_20110509_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110509_date_processed_key ON reports_20110509 USING btree (date_processed);


--
-- Name: reports_20110509_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110509_hangid_idx ON reports_20110509 USING btree (hangid);


--
-- Name: reports_20110509_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110509_product_version_key ON reports_20110509 USING btree (product, version);


--
-- Name: reports_20110509_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110509_reason ON reports_20110509 USING btree (reason);


--
-- Name: reports_20110509_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110509_signature_date_processed_build_key ON reports_20110509 USING btree (signature, date_processed, build);


--
-- Name: reports_20110509_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110509_url_key ON reports_20110509 USING btree (url);


--
-- Name: reports_20110516_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110516_build_key ON reports_20110516 USING btree (build);


--
-- Name: reports_20110516_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110516_date_processed_key ON reports_20110516 USING btree (date_processed);


--
-- Name: reports_20110516_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110516_hangid_idx ON reports_20110516 USING btree (hangid);


--
-- Name: reports_20110516_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110516_product_version_key ON reports_20110516 USING btree (product, version);


--
-- Name: reports_20110516_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110516_reason ON reports_20110516 USING btree (reason);


--
-- Name: reports_20110516_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110516_signature_date_processed_build_key ON reports_20110516 USING btree (signature, date_processed, build);


--
-- Name: reports_20110516_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110516_url_key ON reports_20110516 USING btree (url);


--
-- Name: reports_20110523_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110523_build_key ON reports_20110523 USING btree (build);


--
-- Name: reports_20110523_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110523_date_processed_key ON reports_20110523 USING btree (date_processed);


--
-- Name: reports_20110523_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110523_hangid_idx ON reports_20110523 USING btree (hangid);


--
-- Name: reports_20110523_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110523_product_version_key ON reports_20110523 USING btree (product, version);


--
-- Name: reports_20110523_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110523_reason ON reports_20110523 USING btree (reason);


--
-- Name: reports_20110523_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110523_signature_date_processed_build_key ON reports_20110523 USING btree (signature, date_processed, build);


--
-- Name: reports_20110523_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110523_url_key ON reports_20110523 USING btree (url);


--
-- Name: reports_20110530_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110530_build_key ON reports_20110530 USING btree (build);


--
-- Name: reports_20110530_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110530_date_processed_key ON reports_20110530 USING btree (date_processed);


--
-- Name: reports_20110530_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110530_hangid_idx ON reports_20110530 USING btree (hangid);


--
-- Name: reports_20110530_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110530_product_version_key ON reports_20110530 USING btree (product, version);


--
-- Name: reports_20110530_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110530_reason ON reports_20110530 USING btree (reason);


--
-- Name: reports_20110530_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110530_signature_date_processed_build_key ON reports_20110530 USING btree (signature, date_processed, build);


--
-- Name: reports_20110530_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110530_url_key ON reports_20110530 USING btree (url);


--
-- Name: reports_20110606_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110606_build_key ON reports_20110606 USING btree (build);


--
-- Name: reports_20110606_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110606_date_processed_key ON reports_20110606 USING btree (date_processed);


--
-- Name: reports_20110606_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110606_hangid_idx ON reports_20110606 USING btree (hangid);


--
-- Name: reports_20110606_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110606_product_version_key ON reports_20110606 USING btree (product, version);


--
-- Name: reports_20110606_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110606_reason ON reports_20110606 USING btree (reason);


--
-- Name: reports_20110606_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110606_signature_date_processed_build_key ON reports_20110606 USING btree (signature, date_processed, build);


--
-- Name: reports_20110606_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110606_url_key ON reports_20110606 USING btree (url);


--
-- Name: reports_20110613_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110613_build_key ON reports_20110613 USING btree (build);


--
-- Name: reports_20110613_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110613_date_processed_key ON reports_20110613 USING btree (date_processed);


--
-- Name: reports_20110613_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110613_hangid_idx ON reports_20110613 USING btree (hangid);


--
-- Name: reports_20110613_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110613_product_version_key ON reports_20110613 USING btree (product, version);


--
-- Name: reports_20110613_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110613_reason ON reports_20110613 USING btree (reason);


--
-- Name: reports_20110613_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110613_signature_date_processed_build_key ON reports_20110613 USING btree (signature, date_processed, build);


--
-- Name: reports_20110613_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110613_url_key ON reports_20110613 USING btree (url);


--
-- Name: reports_20110620_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110620_build_key ON reports_20110620 USING btree (build);


--
-- Name: reports_20110620_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110620_date_processed_key ON reports_20110620 USING btree (date_processed);


--
-- Name: reports_20110620_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110620_hangid_idx ON reports_20110620 USING btree (hangid);


--
-- Name: reports_20110620_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110620_product_version_key ON reports_20110620 USING btree (product, version);


--
-- Name: reports_20110620_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110620_reason ON reports_20110620 USING btree (reason);


--
-- Name: reports_20110620_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110620_signature_date_processed_build_key ON reports_20110620 USING btree (signature, date_processed, build);


--
-- Name: reports_20110620_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110620_url_key ON reports_20110620 USING btree (url);


--
-- Name: reports_20110627_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110627_build_key ON reports_20110627 USING btree (build);


--
-- Name: reports_20110627_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110627_date_processed_key ON reports_20110627 USING btree (date_processed);


--
-- Name: reports_20110627_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110627_hangid_idx ON reports_20110627 USING btree (hangid);


--
-- Name: reports_20110627_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110627_product_version_key ON reports_20110627 USING btree (product, version);


--
-- Name: reports_20110627_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110627_reason ON reports_20110627 USING btree (reason);


--
-- Name: reports_20110627_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110627_signature_date_processed_build_key ON reports_20110627 USING btree (signature, date_processed, build);


--
-- Name: reports_20110627_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110627_url_key ON reports_20110627 USING btree (url);


--
-- Name: reports_20110704_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110704_build_key ON reports_20110704 USING btree (build);


--
-- Name: reports_20110704_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110704_date_processed_key ON reports_20110704 USING btree (date_processed);


--
-- Name: reports_20110704_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110704_hangid_idx ON reports_20110704 USING btree (hangid);


--
-- Name: reports_20110704_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110704_product_version_key ON reports_20110704 USING btree (product, version);


--
-- Name: reports_20110704_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110704_reason ON reports_20110704 USING btree (reason);


--
-- Name: reports_20110704_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110704_signature_date_processed_build_key ON reports_20110704 USING btree (signature, date_processed, build);


--
-- Name: reports_20110704_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110704_url_key ON reports_20110704 USING btree (url);


--
-- Name: reports_20110704_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110704_uuid_key ON reports_20110704 USING btree (uuid);


--
-- Name: reports_20110711_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110711_build_key ON reports_20110711 USING btree (build);


--
-- Name: reports_20110711_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110711_date_processed_key ON reports_20110711 USING btree (date_processed);


--
-- Name: reports_20110711_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110711_hangid_idx ON reports_20110711 USING btree (hangid);


--
-- Name: reports_20110711_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110711_product_version_key ON reports_20110711 USING btree (product, version);


--
-- Name: reports_20110711_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110711_reason ON reports_20110711 USING btree (reason);


--
-- Name: reports_20110711_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110711_signature_date_processed_build_key ON reports_20110711 USING btree (signature, date_processed, build);


--
-- Name: reports_20110711_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110711_url_key ON reports_20110711 USING btree (url);


--
-- Name: reports_20110711_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110711_uuid_key ON reports_20110711 USING btree (uuid);


--
-- Name: reports_20110718_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110718_build_key ON reports_20110718 USING btree (build);


--
-- Name: reports_20110718_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110718_date_processed_key ON reports_20110718 USING btree (date_processed);


--
-- Name: reports_20110718_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110718_hangid_idx ON reports_20110718 USING btree (hangid);


--
-- Name: reports_20110718_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110718_product_version_key ON reports_20110718 USING btree (product, version);


--
-- Name: reports_20110718_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110718_reason ON reports_20110718 USING btree (reason);


--
-- Name: reports_20110718_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110718_signature_date_processed_build_key ON reports_20110718 USING btree (signature, date_processed, build);


--
-- Name: reports_20110718_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110718_url_key ON reports_20110718 USING btree (url);


--
-- Name: reports_20110718_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110718_uuid_key ON reports_20110718 USING btree (uuid);


--
-- Name: reports_20110725_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110725_build_key ON reports_20110725 USING btree (build);


--
-- Name: reports_20110725_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110725_date_processed_key ON reports_20110725 USING btree (date_processed);


--
-- Name: reports_20110725_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110725_hangid_idx ON reports_20110725 USING btree (hangid);


--
-- Name: reports_20110725_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110725_product_version_key ON reports_20110725 USING btree (product, version);


--
-- Name: reports_20110725_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110725_reason ON reports_20110725 USING btree (reason);


--
-- Name: reports_20110725_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110725_signature_date_processed_build_key ON reports_20110725 USING btree (signature, date_processed, build);


--
-- Name: reports_20110725_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110725_url_key ON reports_20110725 USING btree (url);


--
-- Name: reports_20110725_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110725_uuid_key ON reports_20110725 USING btree (uuid);


--
-- Name: reports_20110801_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110801_build_key ON reports_20110801 USING btree (build);


--
-- Name: reports_20110801_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110801_date_processed_key ON reports_20110801 USING btree (date_processed);


--
-- Name: reports_20110801_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110801_hangid_idx ON reports_20110801 USING btree (hangid);


--
-- Name: reports_20110801_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110801_product_version_key ON reports_20110801 USING btree (product, version);


--
-- Name: reports_20110801_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110801_reason ON reports_20110801 USING btree (reason);


--
-- Name: reports_20110801_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110801_signature_date_processed_build_key ON reports_20110801 USING btree (signature, date_processed, build);


--
-- Name: reports_20110801_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110801_url_key ON reports_20110801 USING btree (url);


--
-- Name: reports_20110801_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110801_uuid_key ON reports_20110801 USING btree (uuid);


--
-- Name: reports_20110808_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110808_build_key ON reports_20110808 USING btree (build);


--
-- Name: reports_20110808_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110808_date_processed_key ON reports_20110808 USING btree (date_processed);


--
-- Name: reports_20110808_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110808_hangid_idx ON reports_20110808 USING btree (hangid);


--
-- Name: reports_20110808_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110808_product_version_key ON reports_20110808 USING btree (product, version);


--
-- Name: reports_20110808_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110808_reason ON reports_20110808 USING btree (reason);


--
-- Name: reports_20110808_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110808_signature_date_processed_build_key ON reports_20110808 USING btree (signature, date_processed, build);


--
-- Name: reports_20110808_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110808_url_key ON reports_20110808 USING btree (url);


--
-- Name: reports_20110808_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110808_uuid_key ON reports_20110808 USING btree (uuid);


--
-- Name: reports_20110815_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110815_build_key ON reports_20110815 USING btree (build);


--
-- Name: reports_20110815_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110815_date_processed_key ON reports_20110815 USING btree (date_processed);


--
-- Name: reports_20110815_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110815_hangid_idx ON reports_20110815 USING btree (hangid);


--
-- Name: reports_20110815_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110815_product_version_key ON reports_20110815 USING btree (product, version);


--
-- Name: reports_20110815_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110815_reason ON reports_20110815 USING btree (reason);


--
-- Name: reports_20110815_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110815_signature_date_processed_build_key ON reports_20110815 USING btree (signature, date_processed, build);


--
-- Name: reports_20110815_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110815_url_key ON reports_20110815 USING btree (url);


--
-- Name: reports_20110815_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110815_uuid_key ON reports_20110815 USING btree (uuid);


--
-- Name: reports_20110822_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110822_build_key ON reports_20110822 USING btree (build);


--
-- Name: reports_20110822_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110822_date_processed_key ON reports_20110822 USING btree (date_processed);


--
-- Name: reports_20110822_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110822_hangid_idx ON reports_20110822 USING btree (hangid);


--
-- Name: reports_20110822_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110822_product_version_key ON reports_20110822 USING btree (product, version);


--
-- Name: reports_20110822_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110822_reason ON reports_20110822 USING btree (reason);


--
-- Name: reports_20110822_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110822_signature_date_processed_build_key ON reports_20110822 USING btree (signature, date_processed, build);


--
-- Name: reports_20110822_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110822_url_key ON reports_20110822 USING btree (url);


--
-- Name: reports_20110822_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110822_uuid_key ON reports_20110822 USING btree (uuid);


--
-- Name: reports_20110829_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110829_build_key ON reports_20110829 USING btree (build);


--
-- Name: reports_20110829_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110829_date_processed_key ON reports_20110829 USING btree (date_processed);


--
-- Name: reports_20110829_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110829_hangid_idx ON reports_20110829 USING btree (hangid);


--
-- Name: reports_20110829_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110829_product_version_key ON reports_20110829 USING btree (product, version);


--
-- Name: reports_20110829_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110829_reason ON reports_20110829 USING btree (reason);


--
-- Name: reports_20110829_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110829_signature_date_processed_build_key ON reports_20110829 USING btree (signature, date_processed, build);


--
-- Name: reports_20110829_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110829_url_key ON reports_20110829 USING btree (url);


--
-- Name: reports_20110829_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110829_uuid_key ON reports_20110829 USING btree (uuid);


--
-- Name: reports_20110905_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110905_build_key ON reports_20110905 USING btree (build);


--
-- Name: reports_20110905_date_processed_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110905_date_processed_key ON reports_20110905 USING btree (date_processed);


--
-- Name: reports_20110905_hangid_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110905_hangid_idx ON reports_20110905 USING btree (hangid);


--
-- Name: reports_20110905_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110905_product_version_key ON reports_20110905 USING btree (product, version);


--
-- Name: reports_20110905_reason; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110905_reason ON reports_20110905 USING btree (reason);


--
-- Name: reports_20110905_signature_date_processed_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110905_signature_date_processed_build_key ON reports_20110905 USING btree (signature, date_processed, build);


--
-- Name: reports_20110905_url_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110905_url_key ON reports_20110905 USING btree (url);


--
-- Name: reports_20110905_uuid_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_20110905_uuid_key ON reports_20110905 USING btree (uuid);


--
-- Name: reports_duplicates_leader; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX reports_duplicates_leader ON reports_duplicates USING btree (duplicate_of);


--
-- Name: signature_build_first_report; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX signature_build_first_report ON signature_build USING btree (first_report);


--
-- Name: signature_build_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE UNIQUE INDEX signature_build_key ON signature_build USING btree (signature, product, version, os_name, build);


--
-- Name: signature_build_product; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX signature_build_product ON signature_build USING btree (product, version);


--
-- Name: signature_build_productdims; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX signature_build_productdims ON signature_build USING btree (productdims_id);


--
-- Name: signature_build_signature; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX signature_build_signature ON signature_build USING btree (signature);


--
-- Name: signature_products_product_version; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX signature_products_product_version ON signature_products USING btree (product_version_id);


--
-- Name: tcbs_product_version; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX tcbs_product_version ON tcbs USING btree (product_version_id, report_date);


--
-- Name: tcbs_report_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX tcbs_report_date ON tcbs USING btree (report_date);


--
-- Name: tcbs_signature; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX tcbs_signature ON tcbs USING btree (signature_id);


--
-- Name: top_crashes_by_signature2_osdims_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX top_crashes_by_signature2_osdims_key ON top_crashes_by_signature USING btree (osdims_id);


--
-- Name: top_crashes_by_signature2_productdims_window_end_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX top_crashes_by_signature2_productdims_window_end_idx ON top_crashes_by_signature USING btree (productdims_id, window_end DESC);


--
-- Name: top_crashes_by_signature2_signature_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX top_crashes_by_signature2_signature_key ON top_crashes_by_signature USING btree (signature);


--
-- Name: top_crashes_by_signature2_window_end_productdims_id_idx; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX top_crashes_by_signature2_window_end_productdims_id_idx ON top_crashes_by_signature USING btree (window_end DESC, productdims_id);


--
-- Name: top_crashes_by_url2_count_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX top_crashes_by_url2_count_key ON top_crashes_by_url USING btree (count);


--
-- Name: top_crashes_by_url2_osdims_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX top_crashes_by_url2_osdims_key ON top_crashes_by_url USING btree (osdims_id);


--
-- Name: top_crashes_by_url2_productdims_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX top_crashes_by_url2_productdims_key ON top_crashes_by_url USING btree (productdims_id);


--
-- Name: top_crashes_by_url2_urldims_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX top_crashes_by_url2_urldims_key ON top_crashes_by_url USING btree (urldims_id);


--
-- Name: top_crashes_by_url2_window_end_window_size_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX top_crashes_by_url2_window_end_window_size_key ON top_crashes_by_url USING btree (window_end, window_size);


--
-- Name: topcrashurlfactsreports_topcrashurlfacts_id_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX topcrashurlfactsreports_topcrashurlfacts_id_key ON topcrashurlfactsreports USING btree (topcrashurlfacts_id);


--
-- Name: urldims_url_domain_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE UNIQUE INDEX urldims_url_domain_key ON urldims USING btree (url, domain);


--
-- Name: log_priorityjobs; Type: TRIGGER; Schema: public; Owner: breakpad_rw
--

CREATE TRIGGER log_priorityjobs AFTER INSERT ON priorityjobs FOR EACH ROW EXECUTE PROCEDURE log_priorityjobs();


--
-- Name: version_sort_insert_trigger; Type: TRIGGER; Schema: public; Owner: breakpad_rw
--

CREATE TRIGGER version_sort_insert_trigger AFTER INSERT ON productdims FOR EACH ROW EXECUTE PROCEDURE version_sort_insert_trigger();


--
-- Name: version_sort_update_trigger_after; Type: TRIGGER; Schema: public; Owner: breakpad_rw
--

CREATE TRIGGER version_sort_update_trigger_after AFTER UPDATE ON productdims_version_sort FOR EACH ROW EXECUTE PROCEDURE version_sort_update_trigger_after();


--
-- Name: version_sort_update_trigger_before; Type: TRIGGER; Schema: public; Owner: breakpad_rw
--

CREATE TRIGGER version_sort_update_trigger_before BEFORE UPDATE ON productdims_version_sort FOR EACH ROW EXECUTE PROCEDURE version_sort_update_trigger_before();


--
-- Name: bug_associations_bugs_fk; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY bug_associations
    ADD CONSTRAINT bug_associations_bugs_fk FOREIGN KEY (bug_id) REFERENCES bugs(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: email_campaigns_contacts_email_campaigns_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY email_campaigns_contacts
    ADD CONSTRAINT email_campaigns_contacts_email_campaigns_id_fkey FOREIGN KEY (email_campaigns_id) REFERENCES email_campaigns(id);


--
-- Name: email_campaigns_contacts_email_contacts_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY email_campaigns_contacts
    ADD CONSTRAINT email_campaigns_contacts_email_contacts_id_fkey FOREIGN KEY (email_contacts_id) REFERENCES email_contacts(id);


--
-- Name: extensions_20100607_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100607
    ADD CONSTRAINT extensions_20100607_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100607(id) ON DELETE CASCADE;


--
-- Name: extensions_20100614_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100614
    ADD CONSTRAINT extensions_20100614_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100614(id) ON DELETE CASCADE;


--
-- Name: extensions_20100621_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100621
    ADD CONSTRAINT extensions_20100621_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100621(id) ON DELETE CASCADE;


--
-- Name: extensions_20100628_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100628
    ADD CONSTRAINT extensions_20100628_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100628(id) ON DELETE CASCADE;


--
-- Name: extensions_20100705_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100705
    ADD CONSTRAINT extensions_20100705_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100705(id) ON DELETE CASCADE;


--
-- Name: extensions_20100712_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100712
    ADD CONSTRAINT extensions_20100712_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100712(id) ON DELETE CASCADE;


--
-- Name: extensions_20100719_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100719
    ADD CONSTRAINT extensions_20100719_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100719(id) ON DELETE CASCADE;


--
-- Name: extensions_20100726_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100726
    ADD CONSTRAINT extensions_20100726_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100726(id) ON DELETE CASCADE;


--
-- Name: extensions_20100802_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100802
    ADD CONSTRAINT extensions_20100802_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100802(id) ON DELETE CASCADE;


--
-- Name: extensions_20100809_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100809
    ADD CONSTRAINT extensions_20100809_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100809(id) ON DELETE CASCADE;


--
-- Name: extensions_20100816_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100816
    ADD CONSTRAINT extensions_20100816_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100816(id) ON DELETE CASCADE;


--
-- Name: extensions_20100823_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100823
    ADD CONSTRAINT extensions_20100823_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100823(id) ON DELETE CASCADE;


--
-- Name: extensions_20100830_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100830
    ADD CONSTRAINT extensions_20100830_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100830(id) ON DELETE CASCADE;


--
-- Name: extensions_20100906_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100906
    ADD CONSTRAINT extensions_20100906_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100906(id) ON DELETE CASCADE;


--
-- Name: extensions_20100913_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100913
    ADD CONSTRAINT extensions_20100913_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100913(id) ON DELETE CASCADE;


--
-- Name: extensions_20100920_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100920
    ADD CONSTRAINT extensions_20100920_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100920(id) ON DELETE CASCADE;


--
-- Name: extensions_20100927_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20100927
    ADD CONSTRAINT extensions_20100927_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100927(id) ON DELETE CASCADE;


--
-- Name: extensions_20101004_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101004
    ADD CONSTRAINT extensions_20101004_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101004(id) ON DELETE CASCADE;


--
-- Name: extensions_20101011_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101011
    ADD CONSTRAINT extensions_20101011_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101011(id) ON DELETE CASCADE;


--
-- Name: extensions_20101018_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101018
    ADD CONSTRAINT extensions_20101018_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101018(id) ON DELETE CASCADE;


--
-- Name: extensions_20101025_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101025
    ADD CONSTRAINT extensions_20101025_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101025(id) ON DELETE CASCADE;


--
-- Name: extensions_20101101_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101101
    ADD CONSTRAINT extensions_20101101_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101101(id) ON DELETE CASCADE;


--
-- Name: extensions_20101108_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101108
    ADD CONSTRAINT extensions_20101108_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101108(id) ON DELETE CASCADE;


--
-- Name: extensions_20101115_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101115
    ADD CONSTRAINT extensions_20101115_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101115(id) ON DELETE CASCADE;


--
-- Name: extensions_20101122_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101122
    ADD CONSTRAINT extensions_20101122_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101122(id) ON DELETE CASCADE;


--
-- Name: extensions_20101129_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101129
    ADD CONSTRAINT extensions_20101129_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101129(id) ON DELETE CASCADE;


--
-- Name: extensions_20101206_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101206
    ADD CONSTRAINT extensions_20101206_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101206(id) ON DELETE CASCADE;


--
-- Name: extensions_20101213_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101213
    ADD CONSTRAINT extensions_20101213_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101213(id) ON DELETE CASCADE;


--
-- Name: extensions_20101220_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101220
    ADD CONSTRAINT extensions_20101220_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101220(id) ON DELETE CASCADE;


--
-- Name: extensions_20101227_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20101227
    ADD CONSTRAINT extensions_20101227_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101227(id) ON DELETE CASCADE;


--
-- Name: extensions_20110103_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110103
    ADD CONSTRAINT extensions_20110103_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110103(id) ON DELETE CASCADE;


--
-- Name: extensions_20110110_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110110
    ADD CONSTRAINT extensions_20110110_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110110(id) ON DELETE CASCADE;


--
-- Name: extensions_20110124_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110124
    ADD CONSTRAINT extensions_20110124_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110124(id) ON DELETE CASCADE;


--
-- Name: extensions_20110131_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110131
    ADD CONSTRAINT extensions_20110131_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110131(id) ON DELETE CASCADE;


--
-- Name: extensions_20110207_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110207
    ADD CONSTRAINT extensions_20110207_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110207(id) ON DELETE CASCADE;


--
-- Name: extensions_20110214_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110214
    ADD CONSTRAINT extensions_20110214_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110214(id) ON DELETE CASCADE;


--
-- Name: extensions_20110221_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110221
    ADD CONSTRAINT extensions_20110221_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110221(id) ON DELETE CASCADE;


--
-- Name: extensions_20110228_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110228
    ADD CONSTRAINT extensions_20110228_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110228(id) ON DELETE CASCADE;


--
-- Name: extensions_20110307_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110307
    ADD CONSTRAINT extensions_20110307_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110307(id) ON DELETE CASCADE;


--
-- Name: extensions_20110314_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110314
    ADD CONSTRAINT extensions_20110314_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110314(id) ON DELETE CASCADE;


--
-- Name: extensions_20110321_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110321
    ADD CONSTRAINT extensions_20110321_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110321(id) ON DELETE CASCADE;


--
-- Name: extensions_20110328_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110328
    ADD CONSTRAINT extensions_20110328_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110328(id) ON DELETE CASCADE;


--
-- Name: extensions_20110404_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110404
    ADD CONSTRAINT extensions_20110404_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110404(id) ON DELETE CASCADE;


--
-- Name: extensions_20110411_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110411
    ADD CONSTRAINT extensions_20110411_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110411(id) ON DELETE CASCADE;


--
-- Name: extensions_20110418_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110418
    ADD CONSTRAINT extensions_20110418_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110418(id) ON DELETE CASCADE;


--
-- Name: extensions_20110425_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110425
    ADD CONSTRAINT extensions_20110425_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110425(id) ON DELETE CASCADE;


--
-- Name: extensions_20110502_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110502
    ADD CONSTRAINT extensions_20110502_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110502(id) ON DELETE CASCADE;


--
-- Name: extensions_20110509_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110509
    ADD CONSTRAINT extensions_20110509_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110509(id) ON DELETE CASCADE;


--
-- Name: extensions_20110516_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110516
    ADD CONSTRAINT extensions_20110516_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110516(id) ON DELETE CASCADE;


--
-- Name: extensions_20110523_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110523
    ADD CONSTRAINT extensions_20110523_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110523(id) ON DELETE CASCADE;


--
-- Name: extensions_20110530_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110530
    ADD CONSTRAINT extensions_20110530_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110530(id) ON DELETE CASCADE;


--
-- Name: extensions_20110606_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110606
    ADD CONSTRAINT extensions_20110606_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110606(id) ON DELETE CASCADE;


--
-- Name: extensions_20110613_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110613
    ADD CONSTRAINT extensions_20110613_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110613(id) ON DELETE CASCADE;


--
-- Name: extensions_20110620_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110620
    ADD CONSTRAINT extensions_20110620_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110620(id) ON DELETE CASCADE;


--
-- Name: extensions_20110627_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110627
    ADD CONSTRAINT extensions_20110627_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110627(id) ON DELETE CASCADE;


--
-- Name: extensions_20110704_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110704
    ADD CONSTRAINT extensions_20110704_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110704(id) ON DELETE CASCADE;


--
-- Name: extensions_20110711_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110711
    ADD CONSTRAINT extensions_20110711_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110711(id) ON DELETE CASCADE;


--
-- Name: extensions_20110718_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110718
    ADD CONSTRAINT extensions_20110718_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110718(id) ON DELETE CASCADE;


--
-- Name: extensions_20110725_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110725
    ADD CONSTRAINT extensions_20110725_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110725(id) ON DELETE CASCADE;


--
-- Name: extensions_20110801_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110801
    ADD CONSTRAINT extensions_20110801_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110801(id) ON DELETE CASCADE;


--
-- Name: extensions_20110808_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110808
    ADD CONSTRAINT extensions_20110808_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110808(id) ON DELETE CASCADE;


--
-- Name: extensions_20110815_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110815
    ADD CONSTRAINT extensions_20110815_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110815(id) ON DELETE CASCADE;


--
-- Name: extensions_20110822_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110822
    ADD CONSTRAINT extensions_20110822_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110822(id) ON DELETE CASCADE;


--
-- Name: extensions_20110829_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110829
    ADD CONSTRAINT extensions_20110829_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110829(id) ON DELETE CASCADE;


--
-- Name: extensions_20110905_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY extensions_20110905
    ADD CONSTRAINT extensions_20110905_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110905(id) ON DELETE CASCADE;


--
-- Name: frames_20100607_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100607
    ADD CONSTRAINT frames_20100607_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100607(id) ON DELETE CASCADE;


--
-- Name: frames_20100614_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100614
    ADD CONSTRAINT frames_20100614_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100614(id) ON DELETE CASCADE;


--
-- Name: frames_20100621_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100621
    ADD CONSTRAINT frames_20100621_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100621(id) ON DELETE CASCADE;


--
-- Name: frames_20100628_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100628
    ADD CONSTRAINT frames_20100628_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100628(id) ON DELETE CASCADE;


--
-- Name: frames_20100705_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100705
    ADD CONSTRAINT frames_20100705_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100705(id) ON DELETE CASCADE;


--
-- Name: frames_20100712_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100712
    ADD CONSTRAINT frames_20100712_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100712(id) ON DELETE CASCADE;


--
-- Name: frames_20100719_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100719
    ADD CONSTRAINT frames_20100719_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100719(id) ON DELETE CASCADE;


--
-- Name: frames_20100726_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100726
    ADD CONSTRAINT frames_20100726_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100726(id) ON DELETE CASCADE;


--
-- Name: frames_20100802_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100802
    ADD CONSTRAINT frames_20100802_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100802(id) ON DELETE CASCADE;


--
-- Name: frames_20100809_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100809
    ADD CONSTRAINT frames_20100809_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100809(id) ON DELETE CASCADE;


--
-- Name: frames_20100816_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100816
    ADD CONSTRAINT frames_20100816_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100816(id) ON DELETE CASCADE;


--
-- Name: frames_20100823_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100823
    ADD CONSTRAINT frames_20100823_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100823(id) ON DELETE CASCADE;


--
-- Name: frames_20100830_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100830
    ADD CONSTRAINT frames_20100830_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100830(id) ON DELETE CASCADE;


--
-- Name: frames_20100906_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100906
    ADD CONSTRAINT frames_20100906_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100906(id) ON DELETE CASCADE;


--
-- Name: frames_20100913_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100913
    ADD CONSTRAINT frames_20100913_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100913(id) ON DELETE CASCADE;


--
-- Name: frames_20100920_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100920
    ADD CONSTRAINT frames_20100920_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100920(id) ON DELETE CASCADE;


--
-- Name: frames_20100927_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20100927
    ADD CONSTRAINT frames_20100927_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100927(id) ON DELETE CASCADE;


--
-- Name: frames_20101004_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101004
    ADD CONSTRAINT frames_20101004_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101004(id) ON DELETE CASCADE;


--
-- Name: frames_20101011_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101011
    ADD CONSTRAINT frames_20101011_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101011(id) ON DELETE CASCADE;


--
-- Name: frames_20101018_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101018
    ADD CONSTRAINT frames_20101018_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101018(id) ON DELETE CASCADE;


--
-- Name: frames_20101025_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101025
    ADD CONSTRAINT frames_20101025_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101025(id) ON DELETE CASCADE;


--
-- Name: frames_20101101_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101101
    ADD CONSTRAINT frames_20101101_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101101(id) ON DELETE CASCADE;


--
-- Name: frames_20101108_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101108
    ADD CONSTRAINT frames_20101108_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101108(id) ON DELETE CASCADE;


--
-- Name: frames_20101115_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101115
    ADD CONSTRAINT frames_20101115_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101115(id) ON DELETE CASCADE;


--
-- Name: frames_20101122_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101122
    ADD CONSTRAINT frames_20101122_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101122(id) ON DELETE CASCADE;


--
-- Name: frames_20101129_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101129
    ADD CONSTRAINT frames_20101129_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101129(id) ON DELETE CASCADE;


--
-- Name: frames_20101206_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101206
    ADD CONSTRAINT frames_20101206_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101206(id) ON DELETE CASCADE;


--
-- Name: frames_20101213_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101213
    ADD CONSTRAINT frames_20101213_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101213(id) ON DELETE CASCADE;


--
-- Name: frames_20101220_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101220
    ADD CONSTRAINT frames_20101220_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101220(id) ON DELETE CASCADE;


--
-- Name: frames_20101227_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20101227
    ADD CONSTRAINT frames_20101227_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101227(id) ON DELETE CASCADE;


--
-- Name: frames_20110103_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110103
    ADD CONSTRAINT frames_20110103_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110103(id) ON DELETE CASCADE;


--
-- Name: frames_20110110_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110110
    ADD CONSTRAINT frames_20110110_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110110(id) ON DELETE CASCADE;


--
-- Name: frames_20110124_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110124
    ADD CONSTRAINT frames_20110124_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110124(id) ON DELETE CASCADE;


--
-- Name: frames_20110131_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110131
    ADD CONSTRAINT frames_20110131_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110131(id) ON DELETE CASCADE;


--
-- Name: frames_20110207_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110207
    ADD CONSTRAINT frames_20110207_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110207(id) ON DELETE CASCADE;


--
-- Name: frames_20110214_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110214
    ADD CONSTRAINT frames_20110214_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110214(id) ON DELETE CASCADE;


--
-- Name: frames_20110221_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110221
    ADD CONSTRAINT frames_20110221_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110221(id) ON DELETE CASCADE;


--
-- Name: frames_20110228_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110228
    ADD CONSTRAINT frames_20110228_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110228(id) ON DELETE CASCADE;


--
-- Name: frames_20110307_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110307
    ADD CONSTRAINT frames_20110307_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110307(id) ON DELETE CASCADE;


--
-- Name: frames_20110314_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110314
    ADD CONSTRAINT frames_20110314_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110314(id) ON DELETE CASCADE;


--
-- Name: frames_20110321_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110321
    ADD CONSTRAINT frames_20110321_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110321(id) ON DELETE CASCADE;


--
-- Name: frames_20110328_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110328
    ADD CONSTRAINT frames_20110328_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110328(id) ON DELETE CASCADE;


--
-- Name: frames_20110404_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110404
    ADD CONSTRAINT frames_20110404_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110404(id) ON DELETE CASCADE;


--
-- Name: frames_20110411_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110411
    ADD CONSTRAINT frames_20110411_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110411(id) ON DELETE CASCADE;


--
-- Name: frames_20110418_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110418
    ADD CONSTRAINT frames_20110418_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110418(id) ON DELETE CASCADE;


--
-- Name: frames_20110425_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110425
    ADD CONSTRAINT frames_20110425_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110425(id) ON DELETE CASCADE;


--
-- Name: frames_20110502_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110502
    ADD CONSTRAINT frames_20110502_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110502(id) ON DELETE CASCADE;


--
-- Name: frames_20110509_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110509
    ADD CONSTRAINT frames_20110509_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110509(id) ON DELETE CASCADE;


--
-- Name: frames_20110516_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110516
    ADD CONSTRAINT frames_20110516_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110516(id) ON DELETE CASCADE;


--
-- Name: frames_20110523_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110523
    ADD CONSTRAINT frames_20110523_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110523(id) ON DELETE CASCADE;


--
-- Name: frames_20110530_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110530
    ADD CONSTRAINT frames_20110530_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110530(id) ON DELETE CASCADE;


--
-- Name: frames_20110606_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110606
    ADD CONSTRAINT frames_20110606_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110606(id) ON DELETE CASCADE;


--
-- Name: frames_20110613_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110613
    ADD CONSTRAINT frames_20110613_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110613(id) ON DELETE CASCADE;


--
-- Name: frames_20110620_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110620
    ADD CONSTRAINT frames_20110620_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110620(id) ON DELETE CASCADE;


--
-- Name: frames_20110627_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110627
    ADD CONSTRAINT frames_20110627_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110627(id) ON DELETE CASCADE;


--
-- Name: frames_20110704_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110704
    ADD CONSTRAINT frames_20110704_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110704(id) ON DELETE CASCADE;


--
-- Name: frames_20110711_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110711
    ADD CONSTRAINT frames_20110711_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110711(id) ON DELETE CASCADE;


--
-- Name: frames_20110718_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110718
    ADD CONSTRAINT frames_20110718_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110718(id) ON DELETE CASCADE;


--
-- Name: frames_20110725_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110725
    ADD CONSTRAINT frames_20110725_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110725(id) ON DELETE CASCADE;


--
-- Name: frames_20110801_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110801
    ADD CONSTRAINT frames_20110801_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110801(id) ON DELETE CASCADE;


--
-- Name: frames_20110808_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110808
    ADD CONSTRAINT frames_20110808_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110808(id) ON DELETE CASCADE;


--
-- Name: frames_20110815_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110815
    ADD CONSTRAINT frames_20110815_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110815(id) ON DELETE CASCADE;


--
-- Name: frames_20110822_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110822
    ADD CONSTRAINT frames_20110822_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110822(id) ON DELETE CASCADE;


--
-- Name: frames_20110829_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110829
    ADD CONSTRAINT frames_20110829_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110829(id) ON DELETE CASCADE;


--
-- Name: frames_20110905_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY frames_20110905
    ADD CONSTRAINT frames_20110905_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110905(id) ON DELETE CASCADE;


--
-- Name: jobs_owner_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_owner_fkey FOREIGN KEY (owner) REFERENCES processors(id) ON DELETE CASCADE;


--
-- Name: os_name_matches_os_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY os_name_matches
    ADD CONSTRAINT os_name_matches_os_name_fkey FOREIGN KEY (os_name) REFERENCES os_names(os_name);


--
-- Name: os_versions_os_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY os_versions
    ADD CONSTRAINT os_versions_os_name_fkey FOREIGN KEY (os_name) REFERENCES os_names(os_name);


--
-- Name: plugins_reports_20100607_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100607
    ADD CONSTRAINT plugins_reports_20100607_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100607(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100614_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100614
    ADD CONSTRAINT plugins_reports_20100614_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100614(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100621_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100621
    ADD CONSTRAINT plugins_reports_20100621_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100621(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100628_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100628
    ADD CONSTRAINT plugins_reports_20100628_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100628(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100705_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100705
    ADD CONSTRAINT plugins_reports_20100705_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100705(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100712_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100712
    ADD CONSTRAINT plugins_reports_20100712_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100712(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100719_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100719
    ADD CONSTRAINT plugins_reports_20100719_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100719(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100726_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100726
    ADD CONSTRAINT plugins_reports_20100726_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100726(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100802_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100802
    ADD CONSTRAINT plugins_reports_20100802_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100802(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100809_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100809
    ADD CONSTRAINT plugins_reports_20100809_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100809(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100816_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100816
    ADD CONSTRAINT plugins_reports_20100816_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100816(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100823_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100823
    ADD CONSTRAINT plugins_reports_20100823_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100823(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100830_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100830
    ADD CONSTRAINT plugins_reports_20100830_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100830(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100906_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100906
    ADD CONSTRAINT plugins_reports_20100906_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100906(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100913_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100913
    ADD CONSTRAINT plugins_reports_20100913_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100913(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100920_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100920
    ADD CONSTRAINT plugins_reports_20100920_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100920(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20100927_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20100927
    ADD CONSTRAINT plugins_reports_20100927_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20100927(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101004_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101004
    ADD CONSTRAINT plugins_reports_20101004_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101004(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101011_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101011
    ADD CONSTRAINT plugins_reports_20101011_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101011(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101018_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101018
    ADD CONSTRAINT plugins_reports_20101018_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101018(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101025_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101025
    ADD CONSTRAINT plugins_reports_20101025_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101025(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101101_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101101
    ADD CONSTRAINT plugins_reports_20101101_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101101(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101108_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101108
    ADD CONSTRAINT plugins_reports_20101108_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101108(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101115_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101115
    ADD CONSTRAINT plugins_reports_20101115_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101115(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101122_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101122
    ADD CONSTRAINT plugins_reports_20101122_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101122(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101129_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101129
    ADD CONSTRAINT plugins_reports_20101129_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101129(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101206_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101206
    ADD CONSTRAINT plugins_reports_20101206_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101206(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101213_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101213
    ADD CONSTRAINT plugins_reports_20101213_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101213(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101220_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101220
    ADD CONSTRAINT plugins_reports_20101220_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101220(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20101227_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20101227
    ADD CONSTRAINT plugins_reports_20101227_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20101227(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110103_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110103
    ADD CONSTRAINT plugins_reports_20110103_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110103(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110110_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110110
    ADD CONSTRAINT plugins_reports_20110110_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110110(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110124_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110124
    ADD CONSTRAINT plugins_reports_20110124_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110124(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110131_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110131
    ADD CONSTRAINT plugins_reports_20110131_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110131(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110207_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110207
    ADD CONSTRAINT plugins_reports_20110207_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110207(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110214_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110214
    ADD CONSTRAINT plugins_reports_20110214_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110214(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110221_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110221
    ADD CONSTRAINT plugins_reports_20110221_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110221_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110221
    ADD CONSTRAINT plugins_reports_20110221_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110221(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110228_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110228
    ADD CONSTRAINT plugins_reports_20110228_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110228_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110228
    ADD CONSTRAINT plugins_reports_20110228_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110228(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110307_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110307
    ADD CONSTRAINT plugins_reports_20110307_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110307_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110307
    ADD CONSTRAINT plugins_reports_20110307_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110307(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110314_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110314
    ADD CONSTRAINT plugins_reports_20110314_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110314_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110314
    ADD CONSTRAINT plugins_reports_20110314_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110314(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110321_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110321
    ADD CONSTRAINT plugins_reports_20110321_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110321_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110321
    ADD CONSTRAINT plugins_reports_20110321_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110321(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110328_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110328
    ADD CONSTRAINT plugins_reports_20110328_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110328_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110328
    ADD CONSTRAINT plugins_reports_20110328_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110328(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110404_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110404
    ADD CONSTRAINT plugins_reports_20110404_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110404_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110404
    ADD CONSTRAINT plugins_reports_20110404_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110404(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110411_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110411
    ADD CONSTRAINT plugins_reports_20110411_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110411_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110411
    ADD CONSTRAINT plugins_reports_20110411_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110411(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110418_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110418
    ADD CONSTRAINT plugins_reports_20110418_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110418_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110418
    ADD CONSTRAINT plugins_reports_20110418_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110418(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110425_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110425
    ADD CONSTRAINT plugins_reports_20110425_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110425_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110425
    ADD CONSTRAINT plugins_reports_20110425_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110425(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110502_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110502
    ADD CONSTRAINT plugins_reports_20110502_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110502_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110502
    ADD CONSTRAINT plugins_reports_20110502_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110502(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110509_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110509
    ADD CONSTRAINT plugins_reports_20110509_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110509_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110509
    ADD CONSTRAINT plugins_reports_20110509_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110509(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110516_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110516
    ADD CONSTRAINT plugins_reports_20110516_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110516_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110516
    ADD CONSTRAINT plugins_reports_20110516_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110516(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110523_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110523
    ADD CONSTRAINT plugins_reports_20110523_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110523_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110523
    ADD CONSTRAINT plugins_reports_20110523_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110523(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110530_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110530
    ADD CONSTRAINT plugins_reports_20110530_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110530_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110530
    ADD CONSTRAINT plugins_reports_20110530_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110530(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110606_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110606
    ADD CONSTRAINT plugins_reports_20110606_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110606_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110606
    ADD CONSTRAINT plugins_reports_20110606_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110606(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110613_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110613
    ADD CONSTRAINT plugins_reports_20110613_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110613_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110613
    ADD CONSTRAINT plugins_reports_20110613_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110613(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110620_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110620
    ADD CONSTRAINT plugins_reports_20110620_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110620_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110620
    ADD CONSTRAINT plugins_reports_20110620_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110620(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110627_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110627
    ADD CONSTRAINT plugins_reports_20110627_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110627_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110627
    ADD CONSTRAINT plugins_reports_20110627_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110627(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110704_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110704
    ADD CONSTRAINT plugins_reports_20110704_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110704_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110704
    ADD CONSTRAINT plugins_reports_20110704_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110704(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110711_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110711
    ADD CONSTRAINT plugins_reports_20110711_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110711_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110711
    ADD CONSTRAINT plugins_reports_20110711_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110711(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110718_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110718
    ADD CONSTRAINT plugins_reports_20110718_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110718_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110718
    ADD CONSTRAINT plugins_reports_20110718_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110718(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110725_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110725
    ADD CONSTRAINT plugins_reports_20110725_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110725_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110725
    ADD CONSTRAINT plugins_reports_20110725_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110725(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110801_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110801
    ADD CONSTRAINT plugins_reports_20110801_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110801_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110801
    ADD CONSTRAINT plugins_reports_20110801_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110801(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110808_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110808
    ADD CONSTRAINT plugins_reports_20110808_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110808_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110808
    ADD CONSTRAINT plugins_reports_20110808_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110808(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110815_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110815
    ADD CONSTRAINT plugins_reports_20110815_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110815_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110815
    ADD CONSTRAINT plugins_reports_20110815_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110815(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110822_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110822
    ADD CONSTRAINT plugins_reports_20110822_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110822_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110822
    ADD CONSTRAINT plugins_reports_20110822_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110822(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110829_plugin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110829
    ADD CONSTRAINT plugins_reports_20110829_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;


--
-- Name: plugins_reports_20110829_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY plugins_reports_20110829
    ADD CONSTRAINT plugins_reports_20110829_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_20110829(id) ON DELETE CASCADE;


--
-- Name: product_release_channels_product_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_release_channels
    ADD CONSTRAINT product_release_channels_product_name_fkey FOREIGN KEY (product_name) REFERENCES products(product_name);


--
-- Name: product_release_channels_release_channel_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_release_channels
    ADD CONSTRAINT product_release_channels_release_channel_fkey FOREIGN KEY (release_channel) REFERENCES release_channels(release_channel);


--
-- Name: product_version_builds_product_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_version_builds
    ADD CONSTRAINT product_version_builds_product_version_id_fkey FOREIGN KEY (product_version_id) REFERENCES product_versions(product_version_id);


--
-- Name: product_versions_product_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_versions
    ADD CONSTRAINT product_versions_product_name_fkey FOREIGN KEY (product_name) REFERENCES products(product_name);


--
-- Name: product_visibility_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY product_visibility
    ADD CONSTRAINT product_visibility_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id) ON DELETE CASCADE;


--
-- Name: productdims_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY top_crashes_by_signature
    ADD CONSTRAINT productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id) ON DELETE CASCADE;


--
-- Name: productdims_product_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY productdims_version_sort
    ADD CONSTRAINT productdims_product_version_fkey FOREIGN KEY (product, version) REFERENCES productdims(product, version) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: release_channel_matches_release_channel_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY release_channel_matches
    ADD CONSTRAINT release_channel_matches_release_channel_fkey FOREIGN KEY (release_channel) REFERENCES release_channels(release_channel);


--
-- Name: signature_bugs_rollup_signature_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY signature_bugs_rollup
    ADD CONSTRAINT signature_bugs_rollup_signature_id_fkey FOREIGN KEY (signature_id) REFERENCES signatures(signature_id);


--
-- Name: signature_products_product_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY signature_products
    ADD CONSTRAINT signature_products_product_version_id_fkey FOREIGN KEY (product_version_id) REFERENCES product_versions(product_version_id);


--
-- Name: signature_products_rollup_product_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY signature_products_rollup
    ADD CONSTRAINT signature_products_rollup_product_name_fkey FOREIGN KEY (product_name) REFERENCES products(product_name);


--
-- Name: signature_products_rollup_signature_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY signature_products_rollup
    ADD CONSTRAINT signature_products_rollup_signature_id_fkey FOREIGN KEY (signature_id) REFERENCES signatures(signature_id);


--
-- Name: signature_products_signature_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY signature_products
    ADD CONSTRAINT signature_products_signature_id_fkey FOREIGN KEY (signature_id) REFERENCES signatures(signature_id);


--
-- Name: tcbs_product_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY tcbs
    ADD CONSTRAINT tcbs_product_version_id_fkey FOREIGN KEY (product_version_id) REFERENCES product_versions(product_version_id);


--
-- Name: tcbs_release_channel_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY tcbs
    ADD CONSTRAINT tcbs_release_channel_fkey FOREIGN KEY (release_channel) REFERENCES release_channels(release_channel);


--
-- Name: tcbs_signature_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY tcbs
    ADD CONSTRAINT tcbs_signature_id_fkey FOREIGN KEY (signature_id) REFERENCES signatures(signature_id);


--
-- Name: top_crashes_by_url_productdims_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY top_crashes_by_url
    ADD CONSTRAINT top_crashes_by_url_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id) ON DELETE CASCADE;


--
-- Name: top_crashes_by_url_signature_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY top_crashes_by_url_signature
    ADD CONSTRAINT top_crashes_by_url_signature_fkey FOREIGN KEY (top_crashes_by_url_id) REFERENCES top_crashes_by_url(id) ON DELETE CASCADE;


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- Name: plpgsql; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON LANGUAGE plpgsql FROM PUBLIC;
REVOKE ALL ON LANGUAGE plpgsql FROM postgres;
GRANT ALL ON LANGUAGE plpgsql TO postgres;
GRANT ALL ON LANGUAGE plpgsql TO PUBLIC;
GRANT ALL ON LANGUAGE plpgsql TO breakpad_rw;


--
-- Name: pg_stat_statements_reset(); Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON FUNCTION pg_stat_statements_reset() FROM PUBLIC;
REVOKE ALL ON FUNCTION pg_stat_statements_reset() FROM postgres;
GRANT ALL ON FUNCTION pg_stat_statements_reset() TO postgres;


--
-- Name: alexa_topsites; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE alexa_topsites FROM PUBLIC;
REVOKE ALL ON TABLE alexa_topsites FROM breakpad_rw;
GRANT ALL ON TABLE alexa_topsites TO breakpad_rw;
GRANT SELECT ON TABLE alexa_topsites TO monitoring;
GRANT SELECT ON TABLE alexa_topsites TO breakpad_ro;
GRANT SELECT ON TABLE alexa_topsites TO breakpad;


--
-- Name: backfill_temp; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE backfill_temp FROM PUBLIC;
REVOKE ALL ON TABLE backfill_temp FROM postgres;
GRANT ALL ON TABLE backfill_temp TO postgres;
GRANT SELECT ON TABLE backfill_temp TO breakpad_ro;
GRANT SELECT ON TABLE backfill_temp TO breakpad;
GRANT ALL ON TABLE backfill_temp TO monitor;


--
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
-- Name: product_versions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_versions FROM PUBLIC;
REVOKE ALL ON TABLE product_versions FROM breakpad_rw;
GRANT ALL ON TABLE product_versions TO breakpad_rw;
GRANT SELECT ON TABLE product_versions TO breakpad_ro;
GRANT SELECT ON TABLE product_versions TO breakpad;
GRANT ALL ON TABLE product_versions TO monitor;


--
-- Name: productdims_id_seq1; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE productdims_id_seq1 FROM PUBLIC;
REVOKE ALL ON SEQUENCE productdims_id_seq1 FROM breakpad_rw;
GRANT ALL ON SEQUENCE productdims_id_seq1 TO breakpad_rw;


--
-- Name: productdims; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE productdims FROM PUBLIC;
REVOKE ALL ON TABLE productdims FROM breakpad_rw;
GRANT ALL ON TABLE productdims TO breakpad_rw;
GRANT SELECT ON TABLE productdims TO monitoring;
GRANT SELECT ON TABLE productdims TO breakpad_ro;
GRANT SELECT ON TABLE productdims TO breakpad;


--
-- Name: branches; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE branches FROM PUBLIC;
REVOKE ALL ON TABLE branches FROM breakpad_rw;
GRANT ALL ON TABLE branches TO breakpad_rw;
GRANT SELECT ON TABLE branches TO breakpad_ro;
GRANT SELECT ON TABLE branches TO breakpad;


--
-- Name: bug_associations; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE bug_associations FROM PUBLIC;
REVOKE ALL ON TABLE bug_associations FROM breakpad_rw;
GRANT ALL ON TABLE bug_associations TO breakpad_rw;
GRANT SELECT ON TABLE bug_associations TO monitoring;
GRANT SELECT ON TABLE bug_associations TO breakpad_ro;
GRANT SELECT ON TABLE bug_associations TO breakpad;


--
-- Name: bugs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE bugs FROM PUBLIC;
REVOKE ALL ON TABLE bugs FROM breakpad_rw;
GRANT ALL ON TABLE bugs TO breakpad_rw;
GRANT SELECT ON TABLE bugs TO monitoring;
GRANT SELECT ON TABLE bugs TO breakpad_ro;
GRANT SELECT ON TABLE bugs TO breakpad;


--
-- Name: builds; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE builds FROM PUBLIC;
REVOKE ALL ON TABLE builds FROM breakpad_rw;
GRANT ALL ON TABLE builds TO breakpad_rw;
GRANT SELECT ON TABLE builds TO monitoring;
GRANT SELECT ON TABLE builds TO breakpad_ro;
GRANT SELECT ON TABLE builds TO breakpad;


--
-- Name: cronjobs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE cronjobs FROM PUBLIC;
REVOKE ALL ON TABLE cronjobs FROM breakpad_rw;
GRANT ALL ON TABLE cronjobs TO breakpad_rw;
GRANT SELECT ON TABLE cronjobs TO breakpad_ro;
GRANT ALL ON TABLE cronjobs TO monitor;
GRANT SELECT ON TABLE cronjobs TO breakpad;


--
-- Name: daily_crash_codes; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE daily_crash_codes FROM PUBLIC;
REVOKE ALL ON TABLE daily_crash_codes FROM breakpad_rw;
GRANT ALL ON TABLE daily_crash_codes TO breakpad_rw;
GRANT SELECT ON TABLE daily_crash_codes TO breakpad_ro;
GRANT SELECT ON TABLE daily_crash_codes TO breakpad;
GRANT ALL ON TABLE daily_crash_codes TO monitor;


--
-- Name: daily_crashes; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE daily_crashes FROM PUBLIC;
REVOKE ALL ON TABLE daily_crashes FROM breakpad_rw;
GRANT ALL ON TABLE daily_crashes TO breakpad_rw;
GRANT SELECT ON TABLE daily_crashes TO monitoring;
GRANT SELECT ON TABLE daily_crashes TO breakpad_ro;
GRANT SELECT ON TABLE daily_crashes TO breakpad;


--
-- Name: daily_crashes_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE daily_crashes_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE daily_crashes_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE daily_crashes_id_seq TO breakpad_rw;


--
-- Name: drop_fks; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE drop_fks FROM PUBLIC;
REVOKE ALL ON TABLE drop_fks FROM postgres;
GRANT ALL ON TABLE drop_fks TO postgres;
GRANT SELECT ON TABLE drop_fks TO breakpad;
GRANT SELECT ON TABLE drop_fks TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE drop_fks TO breakpad_rw;


--
-- Name: email_campaigns; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE email_campaigns FROM PUBLIC;
REVOKE ALL ON TABLE email_campaigns FROM breakpad_rw;
GRANT ALL ON TABLE email_campaigns TO breakpad_rw;
GRANT SELECT ON TABLE email_campaigns TO monitoring;
GRANT SELECT ON TABLE email_campaigns TO breakpad_ro;
GRANT SELECT ON TABLE email_campaigns TO breakpad;


--
-- Name: email_campaigns_contacts; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE email_campaigns_contacts FROM PUBLIC;
REVOKE ALL ON TABLE email_campaigns_contacts FROM breakpad_rw;
GRANT ALL ON TABLE email_campaigns_contacts TO breakpad_rw;
GRANT SELECT ON TABLE email_campaigns_contacts TO monitoring;
GRANT SELECT ON TABLE email_campaigns_contacts TO breakpad_ro;
GRANT SELECT ON TABLE email_campaigns_contacts TO breakpad;


--
-- Name: email_campaigns_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE email_campaigns_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE email_campaigns_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE email_campaigns_id_seq TO breakpad_rw;


--
-- Name: email_contacts; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE email_contacts FROM PUBLIC;
REVOKE ALL ON TABLE email_contacts FROM breakpad_rw;
GRANT ALL ON TABLE email_contacts TO breakpad_rw;
GRANT SELECT ON TABLE email_contacts TO monitoring;
GRANT SELECT ON TABLE email_contacts TO breakpad_ro;
GRANT SELECT ON TABLE email_contacts TO breakpad;


--
-- Name: email_contacts_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE email_contacts_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE email_contacts_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE email_contacts_id_seq TO breakpad_rw;


--
-- Name: extensions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions FROM PUBLIC;
REVOKE ALL ON TABLE extensions FROM breakpad_rw;
GRANT ALL ON TABLE extensions TO breakpad_rw;
GRANT SELECT ON TABLE extensions TO monitoring;
GRANT SELECT ON TABLE extensions TO breakpad_ro;
GRANT SELECT ON TABLE extensions TO breakpad;


--
-- Name: extensions_20100607; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100607 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100607 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100607 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100607 TO monitoring;
GRANT SELECT ON TABLE extensions_20100607 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100607 TO breakpad;


--
-- Name: extensions_20100614; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100614 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100614 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100614 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100614 TO monitoring;
GRANT SELECT ON TABLE extensions_20100614 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100614 TO breakpad;


--
-- Name: extensions_20100621; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100621 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100621 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100621 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100621 TO monitoring;
GRANT SELECT ON TABLE extensions_20100621 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100621 TO breakpad;


--
-- Name: extensions_20100628; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100628 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100628 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100628 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100628 TO monitoring;
GRANT SELECT ON TABLE extensions_20100628 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100628 TO breakpad;


--
-- Name: extensions_20100705; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100705 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100705 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100705 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100705 TO monitoring;
GRANT SELECT ON TABLE extensions_20100705 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100705 TO breakpad;


--
-- Name: extensions_20100712; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100712 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100712 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100712 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100712 TO monitoring;
GRANT SELECT ON TABLE extensions_20100712 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100712 TO breakpad;


--
-- Name: extensions_20100719; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100719 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100719 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100719 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100719 TO monitoring;
GRANT SELECT ON TABLE extensions_20100719 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100719 TO breakpad;


--
-- Name: extensions_20100726; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100726 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100726 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100726 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100726 TO monitoring;
GRANT SELECT ON TABLE extensions_20100726 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100726 TO breakpad;


--
-- Name: extensions_20100802; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100802 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100802 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100802 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100802 TO monitoring;
GRANT SELECT ON TABLE extensions_20100802 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100802 TO breakpad;


--
-- Name: extensions_20100809; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100809 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100809 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100809 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100809 TO monitoring;
GRANT SELECT ON TABLE extensions_20100809 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100809 TO breakpad;


--
-- Name: extensions_20100816; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100816 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100816 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100816 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100816 TO monitoring;
GRANT SELECT ON TABLE extensions_20100816 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100816 TO breakpad;


--
-- Name: extensions_20100823; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100823 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100823 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100823 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100823 TO monitoring;
GRANT SELECT ON TABLE extensions_20100823 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100823 TO breakpad;


--
-- Name: extensions_20100830; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100830 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100830 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100830 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100830 TO monitoring;
GRANT SELECT ON TABLE extensions_20100830 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100830 TO breakpad;


--
-- Name: extensions_20100906; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100906 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100906 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100906 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100906 TO monitoring;
GRANT SELECT ON TABLE extensions_20100906 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100906 TO breakpad;


--
-- Name: extensions_20100913; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100913 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100913 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100913 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100913 TO monitoring;
GRANT SELECT ON TABLE extensions_20100913 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100913 TO breakpad;


--
-- Name: extensions_20100920; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100920 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100920 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100920 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100920 TO monitoring;
GRANT SELECT ON TABLE extensions_20100920 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100920 TO breakpad;


--
-- Name: extensions_20100927; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20100927 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20100927 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20100927 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20100927 TO monitoring;
GRANT SELECT ON TABLE extensions_20100927 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20100927 TO breakpad;


--
-- Name: extensions_20101004; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101004 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101004 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101004 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101004 TO monitoring;
GRANT SELECT ON TABLE extensions_20101004 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101004 TO breakpad;


--
-- Name: extensions_20101011; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101011 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101011 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101011 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101011 TO monitoring;
GRANT SELECT ON TABLE extensions_20101011 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101011 TO breakpad;


--
-- Name: extensions_20101018; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101018 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101018 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101018 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101018 TO monitoring;
GRANT SELECT ON TABLE extensions_20101018 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101018 TO breakpad;


--
-- Name: extensions_20101025; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101025 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101025 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101025 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101025 TO monitoring;
GRANT SELECT ON TABLE extensions_20101025 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101025 TO breakpad;


--
-- Name: extensions_20101101; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101101 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101101 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101101 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101101 TO monitoring;
GRANT SELECT ON TABLE extensions_20101101 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101101 TO breakpad;


--
-- Name: extensions_20101108; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101108 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101108 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101108 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101108 TO monitoring;
GRANT SELECT ON TABLE extensions_20101108 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101108 TO breakpad;


--
-- Name: extensions_20101115; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101115 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101115 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101115 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101115 TO monitoring;
GRANT SELECT ON TABLE extensions_20101115 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101115 TO breakpad;


--
-- Name: extensions_20101122; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101122 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101122 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101122 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101122 TO monitoring;
GRANT SELECT ON TABLE extensions_20101122 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101122 TO breakpad;


--
-- Name: extensions_20101129; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101129 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101129 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101129 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101129 TO monitoring;
GRANT SELECT ON TABLE extensions_20101129 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101129 TO breakpad;


--
-- Name: extensions_20101206; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101206 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101206 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101206 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101206 TO monitoring;
GRANT SELECT ON TABLE extensions_20101206 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101206 TO breakpad;


--
-- Name: extensions_20101213; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101213 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101213 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101213 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101213 TO monitoring;
GRANT SELECT ON TABLE extensions_20101213 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101213 TO breakpad;


--
-- Name: extensions_20101220; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101220 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101220 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101220 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101220 TO monitoring;
GRANT SELECT ON TABLE extensions_20101220 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101220 TO breakpad;


--
-- Name: extensions_20101227; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20101227 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20101227 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20101227 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20101227 TO monitoring;
GRANT SELECT ON TABLE extensions_20101227 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20101227 TO breakpad;


--
-- Name: extensions_20110103; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110103 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110103 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110103 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110103 TO monitoring;
GRANT SELECT ON TABLE extensions_20110103 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110103 TO breakpad;


--
-- Name: extensions_20110110; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110110 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110110 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110110 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110110 TO monitoring;
GRANT SELECT ON TABLE extensions_20110110 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110110 TO breakpad;


--
-- Name: extensions_20110117; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110117 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110117 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110117 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110117 TO monitoring;
GRANT SELECT ON TABLE extensions_20110117 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110117 TO breakpad;


--
-- Name: extensions_20110124; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110124 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110124 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110124 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110124 TO monitoring;
GRANT SELECT ON TABLE extensions_20110124 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110124 TO breakpad;


--
-- Name: extensions_20110131; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110131 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110131 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110131 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110131 TO monitoring;
GRANT SELECT ON TABLE extensions_20110131 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110131 TO breakpad;


--
-- Name: extensions_20110207; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110207 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110207 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110207 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110207 TO monitoring;
GRANT SELECT ON TABLE extensions_20110207 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110207 TO breakpad;


--
-- Name: extensions_20110214; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110214 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110214 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110214 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110214 TO monitoring;
GRANT SELECT ON TABLE extensions_20110214 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110214 TO breakpad;


--
-- Name: extensions_20110221; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110221 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110221 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110221 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110221 TO breakpad;
GRANT SELECT ON TABLE extensions_20110221 TO breakpad_ro;


--
-- Name: extensions_20110228; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110228 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110228 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110228 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110228 TO breakpad;
GRANT SELECT ON TABLE extensions_20110228 TO breakpad_ro;


--
-- Name: extensions_20110307; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110307 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110307 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110307 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110307 TO breakpad;
GRANT SELECT ON TABLE extensions_20110307 TO breakpad_ro;


--
-- Name: extensions_20110314; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110314 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110314 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110314 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110314 TO breakpad;
GRANT SELECT ON TABLE extensions_20110314 TO breakpad_ro;


--
-- Name: extensions_20110321; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110321 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110321 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110321 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110321 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110321 TO breakpad;


--
-- Name: extensions_20110328; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110328 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110328 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110328 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110328 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110328 TO breakpad;


--
-- Name: extensions_20110404; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110404 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110404 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110404 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110404 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110404 TO breakpad;


--
-- Name: extensions_20110411; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110411 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110411 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110411 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110411 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110411 TO breakpad;


--
-- Name: extensions_20110418; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110418 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110418 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110418 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110418 TO breakpad_ro;
GRANT SELECT ON TABLE extensions_20110418 TO breakpad;


--
-- Name: extensions_20110425; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110425 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110425 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110425 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110425 TO breakpad;


--
-- Name: extensions_20110502; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110502 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110502 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110502 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110502 TO breakpad;


--
-- Name: extensions_20110509; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110509 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110509 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110509 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110509 TO breakpad;


--
-- Name: extensions_20110516; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110516 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110516 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110516 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110516 TO breakpad;


--
-- Name: extensions_20110523; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110523 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110523 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110523 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110523 TO breakpad;


--
-- Name: extensions_20110530; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110530 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110530 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110530 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110530 TO breakpad;


--
-- Name: extensions_20110606; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110606 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110606 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110606 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110606 TO breakpad;


--
-- Name: extensions_20110613; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110613 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110613 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110613 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110613 TO breakpad;


--
-- Name: extensions_20110620; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110620 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110620 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110620 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110620 TO breakpad;


--
-- Name: extensions_20110627; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110627 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110627 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110627 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110627 TO breakpad;


--
-- Name: extensions_20110704; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110704 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110704 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110704 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110704 TO breakpad;


--
-- Name: extensions_20110711; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110711 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110711 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110711 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110711 TO breakpad;


--
-- Name: extensions_20110718; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110718 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110718 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110718 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110718 TO breakpad;


--
-- Name: extensions_20110725; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110725 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110725 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110725 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110725 TO breakpad;


--
-- Name: extensions_20110801; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110801 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110801 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110801 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110801 TO breakpad;


--
-- Name: extensions_20110808; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE extensions_20110808 FROM PUBLIC;
REVOKE ALL ON TABLE extensions_20110808 FROM breakpad_rw;
GRANT ALL ON TABLE extensions_20110808 TO breakpad_rw;
GRANT SELECT ON TABLE extensions_20110808 TO breakpad;


--
-- Name: frames; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames FROM PUBLIC;
REVOKE ALL ON TABLE frames FROM breakpad_rw;
GRANT ALL ON TABLE frames TO breakpad_rw;
GRANT SELECT ON TABLE frames TO monitoring;
GRANT SELECT ON TABLE frames TO breakpad_ro;
GRANT SELECT ON TABLE frames TO breakpad;


--
-- Name: frames_20100607; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100607 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100607 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100607 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100607 TO monitoring;
GRANT SELECT ON TABLE frames_20100607 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100607 TO breakpad;


--
-- Name: frames_20100614; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100614 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100614 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100614 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100614 TO monitoring;
GRANT SELECT ON TABLE frames_20100614 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100614 TO breakpad;


--
-- Name: frames_20100621; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100621 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100621 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100621 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100621 TO monitoring;
GRANT SELECT ON TABLE frames_20100621 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100621 TO breakpad;


--
-- Name: frames_20100628; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100628 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100628 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100628 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100628 TO monitoring;
GRANT SELECT ON TABLE frames_20100628 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100628 TO breakpad;


--
-- Name: frames_20100705; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100705 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100705 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100705 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100705 TO monitoring;
GRANT SELECT ON TABLE frames_20100705 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100705 TO breakpad;


--
-- Name: frames_20100712; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100712 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100712 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100712 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100712 TO monitoring;
GRANT SELECT ON TABLE frames_20100712 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100712 TO breakpad;


--
-- Name: frames_20100719; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100719 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100719 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100719 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100719 TO monitoring;
GRANT SELECT ON TABLE frames_20100719 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100719 TO breakpad;


--
-- Name: frames_20100726; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100726 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100726 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100726 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100726 TO monitoring;
GRANT SELECT ON TABLE frames_20100726 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100726 TO breakpad;


--
-- Name: frames_20100802; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100802 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100802 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100802 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100802 TO monitoring;
GRANT SELECT ON TABLE frames_20100802 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100802 TO breakpad;


--
-- Name: frames_20100809; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100809 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100809 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100809 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100809 TO monitoring;
GRANT SELECT ON TABLE frames_20100809 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100809 TO breakpad;


--
-- Name: frames_20100816; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100816 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100816 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100816 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100816 TO monitoring;
GRANT SELECT ON TABLE frames_20100816 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100816 TO breakpad;


--
-- Name: frames_20100823; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100823 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100823 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100823 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100823 TO monitoring;
GRANT SELECT ON TABLE frames_20100823 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100823 TO breakpad;


--
-- Name: frames_20100830; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100830 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100830 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100830 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100830 TO monitoring;
GRANT SELECT ON TABLE frames_20100830 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100830 TO breakpad;


--
-- Name: frames_20100906; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100906 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100906 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100906 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100906 TO monitoring;
GRANT SELECT ON TABLE frames_20100906 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100906 TO breakpad;


--
-- Name: frames_20100913; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100913 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100913 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100913 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100913 TO monitoring;
GRANT SELECT ON TABLE frames_20100913 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100913 TO breakpad;


--
-- Name: frames_20100920; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100920 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100920 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100920 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100920 TO monitoring;
GRANT SELECT ON TABLE frames_20100920 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100920 TO breakpad;


--
-- Name: frames_20100927; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20100927 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20100927 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20100927 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20100927 TO monitoring;
GRANT SELECT ON TABLE frames_20100927 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20100927 TO breakpad;


--
-- Name: frames_20101004; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101004 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101004 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101004 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101004 TO monitoring;
GRANT SELECT ON TABLE frames_20101004 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101004 TO breakpad;


--
-- Name: frames_20101011; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101011 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101011 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101011 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101011 TO monitoring;
GRANT SELECT ON TABLE frames_20101011 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101011 TO breakpad;


--
-- Name: frames_20101018; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101018 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101018 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101018 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101018 TO monitoring;
GRANT SELECT ON TABLE frames_20101018 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101018 TO breakpad;


--
-- Name: frames_20101025; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101025 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101025 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101025 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101025 TO monitoring;
GRANT SELECT ON TABLE frames_20101025 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101025 TO breakpad;


--
-- Name: frames_20101101; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101101 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101101 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101101 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101101 TO monitoring;
GRANT SELECT ON TABLE frames_20101101 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101101 TO breakpad;


--
-- Name: frames_20101108; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101108 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101108 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101108 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101108 TO monitoring;
GRANT SELECT ON TABLE frames_20101108 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101108 TO breakpad;


--
-- Name: frames_20101115; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101115 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101115 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101115 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101115 TO monitoring;
GRANT SELECT ON TABLE frames_20101115 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101115 TO breakpad;


--
-- Name: frames_20101122; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101122 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101122 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101122 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101122 TO monitoring;
GRANT SELECT ON TABLE frames_20101122 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101122 TO breakpad;


--
-- Name: frames_20101129; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101129 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101129 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101129 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101129 TO monitoring;
GRANT SELECT ON TABLE frames_20101129 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101129 TO breakpad;


--
-- Name: frames_20101206; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101206 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101206 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101206 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101206 TO monitoring;
GRANT SELECT ON TABLE frames_20101206 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101206 TO breakpad;


--
-- Name: frames_20101213; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101213 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101213 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101213 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101213 TO monitoring;
GRANT SELECT ON TABLE frames_20101213 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101213 TO breakpad;


--
-- Name: frames_20101220; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101220 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101220 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101220 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101220 TO monitoring;
GRANT SELECT ON TABLE frames_20101220 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101220 TO breakpad;


--
-- Name: frames_20101227; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20101227 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20101227 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20101227 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20101227 TO monitoring;
GRANT SELECT ON TABLE frames_20101227 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20101227 TO breakpad;


--
-- Name: frames_20110103; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110103 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110103 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110103 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110103 TO monitoring;
GRANT SELECT ON TABLE frames_20110103 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110103 TO breakpad;


--
-- Name: frames_20110110; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110110 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110110 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110110 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110110 TO monitoring;
GRANT SELECT ON TABLE frames_20110110 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110110 TO breakpad;


--
-- Name: frames_20110117; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110117 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110117 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110117 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110117 TO monitoring;
GRANT SELECT ON TABLE frames_20110117 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110117 TO breakpad;


--
-- Name: frames_20110124; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110124 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110124 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110124 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110124 TO monitoring;
GRANT SELECT ON TABLE frames_20110124 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110124 TO breakpad;


--
-- Name: frames_20110131; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110131 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110131 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110131 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110131 TO monitoring;
GRANT SELECT ON TABLE frames_20110131 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110131 TO breakpad;


--
-- Name: frames_20110207; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110207 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110207 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110207 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110207 TO monitoring;
GRANT SELECT ON TABLE frames_20110207 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110207 TO breakpad;


--
-- Name: frames_20110214; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110214 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110214 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110214 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110214 TO monitoring;
GRANT SELECT ON TABLE frames_20110214 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110214 TO breakpad;


--
-- Name: frames_20110221; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110221 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110221 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110221 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110221 TO breakpad;
GRANT SELECT ON TABLE frames_20110221 TO breakpad_ro;


--
-- Name: frames_20110228; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110228 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110228 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110228 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110228 TO breakpad;
GRANT SELECT ON TABLE frames_20110228 TO breakpad_ro;


--
-- Name: frames_20110307; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110307 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110307 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110307 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110307 TO breakpad;
GRANT SELECT ON TABLE frames_20110307 TO breakpad_ro;


--
-- Name: frames_20110314; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110314 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110314 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110314 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110314 TO breakpad;
GRANT SELECT ON TABLE frames_20110314 TO breakpad_ro;


--
-- Name: frames_20110321; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110321 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110321 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110321 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110321 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110321 TO breakpad;


--
-- Name: frames_20110328; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110328 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110328 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110328 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110328 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110328 TO breakpad;


--
-- Name: frames_20110404; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110404 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110404 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110404 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110404 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110404 TO breakpad;


--
-- Name: frames_20110411; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110411 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110411 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110411 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110411 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110411 TO breakpad;


--
-- Name: frames_20110418; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110418 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110418 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110418 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110418 TO breakpad_ro;
GRANT SELECT ON TABLE frames_20110418 TO breakpad;


--
-- Name: frames_20110425; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110425 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110425 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110425 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110425 TO breakpad;


--
-- Name: frames_20110502; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110502 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110502 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110502 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110502 TO breakpad;


--
-- Name: frames_20110509; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110509 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110509 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110509 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110509 TO breakpad;


--
-- Name: frames_20110516; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110516 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110516 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110516 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110516 TO breakpad;


--
-- Name: frames_20110523; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110523 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110523 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110523 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110523 TO breakpad;


--
-- Name: frames_20110530; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110530 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110530 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110530 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110530 TO breakpad;


--
-- Name: frames_20110606; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110606 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110606 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110606 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110606 TO breakpad;


--
-- Name: frames_20110613; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110613 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110613 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110613 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110613 TO breakpad;


--
-- Name: frames_20110620; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110620 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110620 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110620 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110620 TO breakpad;


--
-- Name: frames_20110627; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110627 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110627 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110627 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110627 TO breakpad;


--
-- Name: frames_20110704; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110704 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110704 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110704 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110704 TO breakpad;


--
-- Name: frames_20110711; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110711 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110711 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110711 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110711 TO breakpad;


--
-- Name: frames_20110718; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110718 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110718 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110718 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110718 TO breakpad;


--
-- Name: frames_20110725; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110725 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110725 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110725 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110725 TO breakpad;


--
-- Name: frames_20110801; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110801 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110801 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110801 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110801 TO breakpad;


--
-- Name: frames_20110808; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE frames_20110808 FROM PUBLIC;
REVOKE ALL ON TABLE frames_20110808 FROM breakpad_rw;
GRANT ALL ON TABLE frames_20110808 TO breakpad_rw;
GRANT SELECT ON TABLE frames_20110808 TO breakpad;


--
-- Name: jobs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE jobs FROM PUBLIC;
REVOKE ALL ON TABLE jobs FROM breakpad_rw;
GRANT ALL ON TABLE jobs TO breakpad_rw;
GRANT SELECT ON TABLE jobs TO monitoring;
GRANT SELECT ON TABLE jobs TO breakpad_ro;
GRANT SELECT ON TABLE jobs TO breakpad;


--
-- Name: jobs_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE jobs_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE jobs_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE jobs_id_seq TO breakpad_rw;


--
-- Name: jobs_in_queue; Type: ACL; Schema: public; Owner: monitoring
--

REVOKE ALL ON TABLE jobs_in_queue FROM PUBLIC;
REVOKE ALL ON TABLE jobs_in_queue FROM monitoring;
GRANT ALL ON TABLE jobs_in_queue TO monitoring;
GRANT SELECT ON TABLE jobs_in_queue TO breakpad_ro;
GRANT SELECT ON TABLE jobs_in_queue TO breakpad;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE jobs_in_queue TO breakpad_rw;


--
-- Name: last_backfill_temp; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE last_backfill_temp FROM PUBLIC;
REVOKE ALL ON TABLE last_backfill_temp FROM postgres;
GRANT ALL ON TABLE last_backfill_temp TO postgres;
GRANT SELECT ON TABLE last_backfill_temp TO breakpad_ro;
GRANT SELECT ON TABLE last_backfill_temp TO breakpad;
GRANT ALL ON TABLE last_backfill_temp TO monitor;


--
-- Name: last_tcbsig; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE last_tcbsig FROM PUBLIC;
REVOKE ALL ON TABLE last_tcbsig FROM postgres;
GRANT ALL ON TABLE last_tcbsig TO postgres;
GRANT SELECT ON TABLE last_tcbsig TO breakpad;
GRANT SELECT ON TABLE last_tcbsig TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE last_tcbsig TO breakpad_rw;


--
-- Name: last_tcburl; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE last_tcburl FROM PUBLIC;
REVOKE ALL ON TABLE last_tcburl FROM postgres;
GRANT ALL ON TABLE last_tcburl TO postgres;
GRANT SELECT ON TABLE last_tcburl TO breakpad;
GRANT SELECT ON TABLE last_tcburl TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE last_tcburl TO breakpad_rw;


--
-- Name: last_urlsig; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE last_urlsig FROM PUBLIC;
REVOKE ALL ON TABLE last_urlsig FROM postgres;
GRANT ALL ON TABLE last_urlsig TO postgres;
GRANT SELECT ON TABLE last_urlsig TO breakpad;
GRANT SELECT ON TABLE last_urlsig TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE last_urlsig TO breakpad_rw;


--
-- Name: os_name_matches; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE os_name_matches FROM PUBLIC;
REVOKE ALL ON TABLE os_name_matches FROM breakpad_rw;
GRANT ALL ON TABLE os_name_matches TO breakpad_rw;
GRANT SELECT ON TABLE os_name_matches TO breakpad_ro;
GRANT SELECT ON TABLE os_name_matches TO breakpad;
GRANT ALL ON TABLE os_name_matches TO monitor;


--
-- Name: os_names; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE os_names FROM PUBLIC;
REVOKE ALL ON TABLE os_names FROM breakpad_rw;
GRANT ALL ON TABLE os_names TO breakpad_rw;
GRANT SELECT ON TABLE os_names TO breakpad_ro;
GRANT SELECT ON TABLE os_names TO breakpad;
GRANT ALL ON TABLE os_names TO monitor;


--
-- Name: os_versions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE os_versions FROM PUBLIC;
REVOKE ALL ON TABLE os_versions FROM breakpad_rw;
GRANT ALL ON TABLE os_versions TO breakpad_rw;
GRANT SELECT ON TABLE os_versions TO breakpad_ro;
GRANT SELECT ON TABLE os_versions TO breakpad;
GRANT ALL ON TABLE os_versions TO monitor;


--
-- Name: osdims; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE osdims FROM PUBLIC;
REVOKE ALL ON TABLE osdims FROM breakpad_rw;
GRANT ALL ON TABLE osdims TO breakpad_rw;
GRANT SELECT ON TABLE osdims TO monitoring;
GRANT SELECT ON TABLE osdims TO breakpad_ro;
GRANT SELECT ON TABLE osdims TO breakpad;


--
-- Name: osdims_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE osdims_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE osdims_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE osdims_id_seq TO breakpad_rw;


--
-- Name: top_crashes_by_signature; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE top_crashes_by_signature FROM PUBLIC;
REVOKE ALL ON TABLE top_crashes_by_signature FROM breakpad_rw;
GRANT ALL ON TABLE top_crashes_by_signature TO breakpad_rw;
GRANT SELECT ON TABLE top_crashes_by_signature TO monitoring;
GRANT SELECT ON TABLE top_crashes_by_signature TO breakpad_ro;
GRANT SELECT ON TABLE top_crashes_by_signature TO breakpad;


--
-- Name: performance_check_1; Type: ACL; Schema: public; Owner: monitoring
--

REVOKE ALL ON TABLE performance_check_1 FROM PUBLIC;
REVOKE ALL ON TABLE performance_check_1 FROM monitoring;
GRANT ALL ON TABLE performance_check_1 TO monitoring;
GRANT SELECT ON TABLE performance_check_1 TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE performance_check_1 TO breakpad_rw;
GRANT SELECT ON TABLE performance_check_1 TO breakpad;


--
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
-- Name: plugins; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins FROM PUBLIC;
REVOKE ALL ON TABLE plugins FROM breakpad_rw;
GRANT ALL ON TABLE plugins TO breakpad_rw;
GRANT SELECT ON TABLE plugins TO monitoring;
GRANT SELECT ON TABLE plugins TO breakpad_ro;
GRANT SELECT ON TABLE plugins TO breakpad;


--
-- Name: plugins_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE plugins_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE plugins_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE plugins_id_seq TO breakpad_rw;


--
-- Name: plugins_reports; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports TO monitoring;
GRANT SELECT ON TABLE plugins_reports TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports TO breakpad;


--
-- Name: plugins_reports_20100607; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100607 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100607 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100607 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100607 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100607 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100607 TO breakpad;


--
-- Name: plugins_reports_20100614; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100614 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100614 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100614 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100614 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100614 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100614 TO breakpad;


--
-- Name: plugins_reports_20100621; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100621 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100621 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100621 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100621 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100621 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100621 TO breakpad;


--
-- Name: plugins_reports_20100628; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100628 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100628 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100628 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100628 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100628 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100628 TO breakpad;


--
-- Name: plugins_reports_20100705; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100705 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100705 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100705 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100705 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100705 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100705 TO breakpad;


--
-- Name: plugins_reports_20100712; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100712 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100712 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100712 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100712 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100712 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100712 TO breakpad;


--
-- Name: plugins_reports_20100719; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100719 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100719 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100719 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100719 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100719 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100719 TO breakpad;


--
-- Name: plugins_reports_20100726; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100726 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100726 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100726 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100726 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100726 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100726 TO breakpad;


--
-- Name: plugins_reports_20100802; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100802 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100802 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100802 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100802 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100802 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100802 TO breakpad;


--
-- Name: plugins_reports_20100809; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100809 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100809 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100809 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100809 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100809 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100809 TO breakpad;


--
-- Name: plugins_reports_20100816; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100816 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100816 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100816 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100816 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100816 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100816 TO breakpad;


--
-- Name: plugins_reports_20100823; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100823 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100823 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100823 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100823 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100823 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100823 TO breakpad;


--
-- Name: plugins_reports_20100830; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100830 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100830 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100830 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100830 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100830 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100830 TO breakpad;


--
-- Name: plugins_reports_20100906; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100906 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100906 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100906 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100906 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100906 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100906 TO breakpad;


--
-- Name: plugins_reports_20100913; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100913 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100913 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100913 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100913 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100913 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100913 TO breakpad;


--
-- Name: plugins_reports_20100920; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100920 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100920 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100920 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100920 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100920 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100920 TO breakpad;


--
-- Name: plugins_reports_20100927; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20100927 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20100927 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20100927 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20100927 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20100927 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20100927 TO breakpad;


--
-- Name: plugins_reports_20101004; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101004 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101004 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101004 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101004 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101004 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101004 TO breakpad;


--
-- Name: plugins_reports_20101011; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101011 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101011 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101011 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101011 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101011 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101011 TO breakpad;


--
-- Name: plugins_reports_20101018; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101018 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101018 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101018 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101018 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101018 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101018 TO breakpad;


--
-- Name: plugins_reports_20101025; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101025 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101025 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101025 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101025 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101025 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101025 TO breakpad;


--
-- Name: plugins_reports_20101101; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101101 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101101 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101101 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101101 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101101 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101101 TO breakpad;


--
-- Name: plugins_reports_20101108; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101108 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101108 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101108 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101108 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101108 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101108 TO breakpad;


--
-- Name: plugins_reports_20101115; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101115 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101115 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101115 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101115 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101115 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101115 TO breakpad;


--
-- Name: plugins_reports_20101122; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101122 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101122 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101122 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101122 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101122 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101122 TO breakpad;


--
-- Name: plugins_reports_20101129; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101129 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101129 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101129 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101129 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101129 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101129 TO breakpad;


--
-- Name: plugins_reports_20101206; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101206 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101206 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101206 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101206 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101206 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101206 TO breakpad;


--
-- Name: plugins_reports_20101213; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101213 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101213 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101213 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101213 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101213 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101213 TO breakpad;


--
-- Name: plugins_reports_20101220; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101220 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101220 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101220 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101220 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101220 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101220 TO breakpad;


--
-- Name: plugins_reports_20101227; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20101227 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20101227 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20101227 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20101227 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20101227 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20101227 TO breakpad;


--
-- Name: plugins_reports_20110103; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110103 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110103 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110103 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110103 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20110103 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110103 TO breakpad;


--
-- Name: plugins_reports_20110110; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110110 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110110 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110110 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110110 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20110110 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110110 TO breakpad;


--
-- Name: plugins_reports_20110117; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110117 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110117 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110117 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110117 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20110117 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110117 TO breakpad;


--
-- Name: plugins_reports_20110124; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110124 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110124 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110124 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110124 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20110124 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110124 TO breakpad;


--
-- Name: plugins_reports_20110131; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110131 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110131 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110131 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110131 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20110131 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110131 TO breakpad;


--
-- Name: plugins_reports_20110207; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110207 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110207 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110207 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110207 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20110207 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110207 TO breakpad;


--
-- Name: plugins_reports_20110214; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110214 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110214 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110214 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110214 TO monitoring;
GRANT SELECT ON TABLE plugins_reports_20110214 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110214 TO breakpad;


--
-- Name: plugins_reports_20110221; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110221 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110221 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110221 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110221 TO breakpad;
GRANT SELECT ON TABLE plugins_reports_20110221 TO breakpad_ro;


--
-- Name: plugins_reports_20110228; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110228 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110228 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110228 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110228 TO breakpad;
GRANT SELECT ON TABLE plugins_reports_20110228 TO breakpad_ro;


--
-- Name: plugins_reports_20110307; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110307 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110307 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110307 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110307 TO breakpad;
GRANT SELECT ON TABLE plugins_reports_20110307 TO breakpad_ro;


--
-- Name: plugins_reports_20110314; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110314 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110314 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110314 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110314 TO breakpad;
GRANT SELECT ON TABLE plugins_reports_20110314 TO breakpad_ro;


--
-- Name: plugins_reports_20110321; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110321 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110321 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110321 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110321 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110321 TO breakpad;


--
-- Name: plugins_reports_20110328; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110328 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110328 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110328 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110328 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110328 TO breakpad;


--
-- Name: plugins_reports_20110404; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110404 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110404 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110404 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110404 TO breakpad_ro;
GRANT SELECT ON TABLE plugins_reports_20110404 TO breakpad;


--
-- Name: plugins_reports_20110411; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110411 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110411 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110411 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110411 TO breakpad;


--
-- Name: plugins_reports_20110418; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110418 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110418 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110418 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110418 TO breakpad;


--
-- Name: plugins_reports_20110425; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110425 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110425 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110425 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110425 TO breakpad;


--
-- Name: plugins_reports_20110502; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110502 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110502 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110502 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110502 TO breakpad;


--
-- Name: plugins_reports_20110509; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110509 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110509 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110509 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110509 TO breakpad;


--
-- Name: plugins_reports_20110516; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110516 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110516 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110516 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110516 TO breakpad;


--
-- Name: plugins_reports_20110523; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110523 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110523 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110523 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110523 TO breakpad;


--
-- Name: plugins_reports_20110530; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110530 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110530 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110530 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110530 TO breakpad;


--
-- Name: plugins_reports_20110606; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110606 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110606 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110606 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110606 TO breakpad;


--
-- Name: plugins_reports_20110613; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110613 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110613 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110613 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110613 TO breakpad;


--
-- Name: plugins_reports_20110620; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110620 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110620 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110620 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110620 TO breakpad;


--
-- Name: plugins_reports_20110627; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110627 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110627 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110627 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110627 TO breakpad;


--
-- Name: plugins_reports_20110704; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110704 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110704 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110704 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110704 TO breakpad;


--
-- Name: plugins_reports_20110711; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110711 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110711 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110711 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110711 TO breakpad;


--
-- Name: plugins_reports_20110718; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110718 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110718 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110718 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110718 TO breakpad;


--
-- Name: plugins_reports_20110725; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110725 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110725 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110725 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110725 TO breakpad;


--
-- Name: plugins_reports_20110801; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE plugins_reports_20110801 FROM PUBLIC;
REVOKE ALL ON TABLE plugins_reports_20110801 FROM breakpad_rw;
GRANT ALL ON TABLE plugins_reports_20110801 TO breakpad_rw;
GRANT SELECT ON TABLE plugins_reports_20110801 TO breakpad;


--
-- Name: priority_jobs_1445; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1445 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1445 FROM processor;
GRANT ALL ON TABLE priority_jobs_1445 TO processor;
GRANT ALL ON TABLE priority_jobs_1445 TO breakpad_rw;


--
-- Name: priority_jobs_1447; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1447 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1447 FROM processor;
GRANT ALL ON TABLE priority_jobs_1447 TO processor;
GRANT ALL ON TABLE priority_jobs_1447 TO breakpad_rw;


--
-- Name: priority_jobs_1449; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1449 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1449 FROM processor;
GRANT ALL ON TABLE priority_jobs_1449 TO processor;
GRANT ALL ON TABLE priority_jobs_1449 TO breakpad_rw;


--
-- Name: priority_jobs_1450; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1450 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1450 FROM processor;
GRANT ALL ON TABLE priority_jobs_1450 TO processor;
GRANT ALL ON TABLE priority_jobs_1450 TO breakpad_rw;


--
-- Name: priority_jobs_1451; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1451 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1451 FROM processor;
GRANT ALL ON TABLE priority_jobs_1451 TO processor;
GRANT ALL ON TABLE priority_jobs_1451 TO breakpad_rw;


--
-- Name: priority_jobs_1452; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1452 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1452 FROM processor;
GRANT ALL ON TABLE priority_jobs_1452 TO processor;
GRANT ALL ON TABLE priority_jobs_1452 TO breakpad_rw;


--
-- Name: priority_jobs_1453; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1453 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1453 FROM processor;
GRANT ALL ON TABLE priority_jobs_1453 TO processor;
GRANT ALL ON TABLE priority_jobs_1453 TO breakpad_rw;


--
-- Name: priority_jobs_1454; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1454 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1454 FROM processor;
GRANT ALL ON TABLE priority_jobs_1454 TO processor;
GRANT ALL ON TABLE priority_jobs_1454 TO breakpad_rw;


--
-- Name: priority_jobs_1455; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1455 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1455 FROM processor;
GRANT ALL ON TABLE priority_jobs_1455 TO processor;
GRANT ALL ON TABLE priority_jobs_1455 TO breakpad_rw;


--
-- Name: priority_jobs_1456; Type: ACL; Schema: public; Owner: processor
--

REVOKE ALL ON TABLE priority_jobs_1456 FROM PUBLIC;
REVOKE ALL ON TABLE priority_jobs_1456 FROM processor;
GRANT ALL ON TABLE priority_jobs_1456 TO processor;
GRANT ALL ON TABLE priority_jobs_1456 TO breakpad_rw;


--
-- Name: priorityjobs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE priorityjobs FROM PUBLIC;
REVOKE ALL ON TABLE priorityjobs FROM breakpad_rw;
GRANT ALL ON TABLE priorityjobs TO breakpad_rw;
GRANT SELECT ON TABLE priorityjobs TO monitoring;
GRANT SELECT ON TABLE priorityjobs TO breakpad_ro;
GRANT SELECT ON TABLE priorityjobs TO breakpad;


--
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
-- Name: priorityjobs_log_sjc_backup; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE priorityjobs_log_sjc_backup FROM PUBLIC;
REVOKE ALL ON TABLE priorityjobs_log_sjc_backup FROM postgres;
GRANT ALL ON TABLE priorityjobs_log_sjc_backup TO postgres;
GRANT SELECT ON TABLE priorityjobs_log_sjc_backup TO breakpad;
GRANT SELECT ON TABLE priorityjobs_log_sjc_backup TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE priorityjobs_log_sjc_backup TO breakpad_rw;


--
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
-- Name: processors; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE processors FROM PUBLIC;
REVOKE ALL ON TABLE processors FROM breakpad_rw;
GRANT ALL ON TABLE processors TO breakpad_rw;
GRANT SELECT ON TABLE processors TO monitoring;
GRANT SELECT ON TABLE processors TO breakpad_ro;
GRANT SELECT ON TABLE processors TO breakpad;


--
-- Name: processors_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE processors_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE processors_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE processors_id_seq TO breakpad_rw;


--
-- Name: product_adu; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_adu FROM PUBLIC;
REVOKE ALL ON TABLE product_adu FROM breakpad_rw;
GRANT ALL ON TABLE product_adu TO breakpad_rw;
GRANT SELECT ON TABLE product_adu TO breakpad_ro;
GRANT SELECT ON TABLE product_adu TO breakpad;
GRANT ALL ON TABLE product_adu TO monitor;


--
-- Name: product_release_channels; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_release_channels FROM PUBLIC;
REVOKE ALL ON TABLE product_release_channels FROM breakpad_rw;
GRANT ALL ON TABLE product_release_channels TO breakpad_rw;
GRANT SELECT ON TABLE product_release_channels TO breakpad_ro;
GRANT SELECT ON TABLE product_release_channels TO breakpad;
GRANT ALL ON TABLE product_release_channels TO monitor;


--
-- Name: product_visibility; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_visibility FROM PUBLIC;
REVOKE ALL ON TABLE product_visibility FROM breakpad_rw;
GRANT ALL ON TABLE product_visibility TO breakpad_rw;
GRANT SELECT ON TABLE product_visibility TO monitoring;
GRANT SELECT ON TABLE product_visibility TO breakpad_ro;
GRANT SELECT ON TABLE product_visibility TO breakpad;


--
-- Name: release_build_type_map; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE release_build_type_map FROM PUBLIC;
REVOKE ALL ON TABLE release_build_type_map FROM breakpad_rw;
GRANT ALL ON TABLE release_build_type_map TO breakpad_rw;
GRANT SELECT ON TABLE release_build_type_map TO breakpad_ro;
GRANT SELECT ON TABLE release_build_type_map TO breakpad;
GRANT ALL ON TABLE release_build_type_map TO monitor;


--
-- Name: product_info; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_info FROM PUBLIC;
REVOKE ALL ON TABLE product_info FROM breakpad_rw;
GRANT ALL ON TABLE product_info TO breakpad_rw;
GRANT SELECT ON TABLE product_info TO breakpad_ro;
GRANT SELECT ON TABLE product_info TO breakpad;
GRANT ALL ON TABLE product_info TO monitor;


--
-- Name: product_selector; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_selector FROM PUBLIC;
REVOKE ALL ON TABLE product_selector FROM breakpad_rw;
GRANT ALL ON TABLE product_selector TO breakpad_rw;
GRANT SELECT ON TABLE product_selector TO breakpad_ro;
GRANT SELECT ON TABLE product_selector TO breakpad;
GRANT ALL ON TABLE product_selector TO monitor;


--
-- Name: product_version_builds; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE product_version_builds FROM PUBLIC;
REVOKE ALL ON TABLE product_version_builds FROM breakpad_rw;
GRANT ALL ON TABLE product_version_builds TO breakpad_rw;
GRANT SELECT ON TABLE product_version_builds TO breakpad_ro;
GRANT SELECT ON TABLE product_version_builds TO breakpad;
GRANT ALL ON TABLE product_version_builds TO monitor;


--
-- Name: productdims_version_sort; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE productdims_version_sort FROM PUBLIC;
REVOKE ALL ON TABLE productdims_version_sort FROM breakpad_rw;
GRANT ALL ON TABLE productdims_version_sort TO breakpad_rw;
GRANT SELECT ON TABLE productdims_version_sort TO breakpad_ro;
GRANT SELECT ON TABLE productdims_version_sort TO breakpad;


--
-- Name: products; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE products FROM PUBLIC;
REVOKE ALL ON TABLE products FROM breakpad_rw;
GRANT ALL ON TABLE products TO breakpad_rw;
GRANT SELECT ON TABLE products TO breakpad_ro;
GRANT SELECT ON TABLE products TO breakpad;
GRANT ALL ON TABLE products TO monitor;


--
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


--
-- Name: release_channel_matches; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE release_channel_matches FROM PUBLIC;
REVOKE ALL ON TABLE release_channel_matches FROM breakpad_rw;
GRANT ALL ON TABLE release_channel_matches TO breakpad_rw;
GRANT SELECT ON TABLE release_channel_matches TO breakpad_ro;
GRANT SELECT ON TABLE release_channel_matches TO breakpad;
GRANT ALL ON TABLE release_channel_matches TO monitor;


--
-- Name: release_channels; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE release_channels FROM PUBLIC;
REVOKE ALL ON TABLE release_channels FROM breakpad_rw;
GRANT ALL ON TABLE release_channels TO breakpad_rw;
GRANT SELECT ON TABLE release_channels TO breakpad_ro;
GRANT SELECT ON TABLE release_channels TO breakpad;
GRANT ALL ON TABLE release_channels TO monitor;


--
-- Name: releasechannel_backfill; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE releasechannel_backfill FROM PUBLIC;
REVOKE ALL ON TABLE releasechannel_backfill FROM postgres;
GRANT ALL ON TABLE releasechannel_backfill TO postgres;
GRANT SELECT ON TABLE releasechannel_backfill TO breakpad_ro;
GRANT SELECT ON TABLE releasechannel_backfill TO breakpad;
GRANT ALL ON TABLE releasechannel_backfill TO monitor;


--
-- Name: releases_raw; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE releases_raw FROM PUBLIC;
REVOKE ALL ON TABLE releases_raw FROM breakpad_rw;
GRANT ALL ON TABLE releases_raw TO breakpad_rw;
GRANT SELECT ON TABLE releases_raw TO breakpad_ro;
GRANT SELECT ON TABLE releases_raw TO breakpad;
GRANT ALL ON TABLE releases_raw TO monitor;


--
-- Name: replication_test; Type: ACL; Schema: public; Owner: monitoring
--

REVOKE ALL ON TABLE replication_test FROM PUBLIC;
REVOKE ALL ON TABLE replication_test FROM monitoring;
GRANT ALL ON TABLE replication_test TO monitoring;
GRANT SELECT ON TABLE replication_test TO breakpad;
GRANT SELECT ON TABLE replication_test TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE replication_test TO breakpad_rw;


--
-- Name: reports; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports FROM PUBLIC;
REVOKE ALL ON TABLE reports FROM breakpad_rw;
GRANT ALL ON TABLE reports TO breakpad_rw;
GRANT SELECT ON TABLE reports TO monitoring;
GRANT SELECT ON TABLE reports TO breakpad_ro;
GRANT SELECT ON TABLE reports TO breakpad;


--
-- Name: reports_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE reports_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE reports_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE reports_id_seq TO breakpad_rw;


--
-- Name: reports_20100607; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100607 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100607 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100607 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100607 TO monitoring;
GRANT SELECT ON TABLE reports_20100607 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100607 TO breakpad;


--
-- Name: reports_20100614; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100614 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100614 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100614 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100614 TO monitoring;
GRANT SELECT ON TABLE reports_20100614 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100614 TO breakpad;


--
-- Name: reports_20100621; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100621 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100621 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100621 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100621 TO monitoring;
GRANT SELECT ON TABLE reports_20100621 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100621 TO breakpad;


--
-- Name: reports_20100628; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100628 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100628 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100628 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100628 TO monitoring;
GRANT SELECT ON TABLE reports_20100628 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100628 TO breakpad;


--
-- Name: reports_20100705; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100705 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100705 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100705 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100705 TO monitoring;
GRANT SELECT ON TABLE reports_20100705 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100705 TO breakpad;


--
-- Name: reports_20100712; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100712 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100712 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100712 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100712 TO monitoring;
GRANT SELECT ON TABLE reports_20100712 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100712 TO breakpad;


--
-- Name: reports_20100719; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100719 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100719 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100719 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100719 TO monitoring;
GRANT SELECT ON TABLE reports_20100719 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100719 TO breakpad;


--
-- Name: reports_20100726; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100726 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100726 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100726 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100726 TO monitoring;
GRANT SELECT ON TABLE reports_20100726 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100726 TO breakpad;


--
-- Name: reports_20100802; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100802 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100802 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100802 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100802 TO monitoring;
GRANT SELECT ON TABLE reports_20100802 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100802 TO breakpad;


--
-- Name: reports_20100809; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100809 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100809 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100809 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100809 TO monitoring;
GRANT SELECT ON TABLE reports_20100809 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100809 TO breakpad;


--
-- Name: reports_20100816; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100816 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100816 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100816 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100816 TO monitoring;
GRANT SELECT ON TABLE reports_20100816 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100816 TO breakpad;


--
-- Name: reports_20100823; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100823 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100823 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100823 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100823 TO monitoring;
GRANT SELECT ON TABLE reports_20100823 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100823 TO breakpad;


--
-- Name: reports_20100830; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100830 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100830 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100830 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100830 TO monitoring;
GRANT SELECT ON TABLE reports_20100830 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100830 TO breakpad;


--
-- Name: reports_20100906; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100906 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100906 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100906 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100906 TO monitoring;
GRANT SELECT ON TABLE reports_20100906 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100906 TO breakpad;


--
-- Name: reports_20100913; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100913 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100913 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100913 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100913 TO monitoring;
GRANT SELECT ON TABLE reports_20100913 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100913 TO breakpad;


--
-- Name: reports_20100920; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100920 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100920 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100920 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100920 TO monitoring;
GRANT SELECT ON TABLE reports_20100920 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100920 TO breakpad;


--
-- Name: reports_20100927; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20100927 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20100927 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20100927 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20100927 TO monitoring;
GRANT SELECT ON TABLE reports_20100927 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20100927 TO breakpad;


--
-- Name: reports_20101004; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101004 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101004 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101004 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101004 TO monitoring;
GRANT SELECT ON TABLE reports_20101004 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101004 TO breakpad;


--
-- Name: reports_20101011; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101011 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101011 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101011 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101011 TO monitoring;
GRANT SELECT ON TABLE reports_20101011 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101011 TO breakpad;


--
-- Name: reports_20101018; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101018 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101018 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101018 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101018 TO monitoring;
GRANT SELECT ON TABLE reports_20101018 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101018 TO breakpad;


--
-- Name: reports_20101025; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101025 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101025 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101025 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101025 TO monitoring;
GRANT SELECT ON TABLE reports_20101025 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101025 TO breakpad;


--
-- Name: reports_20101101; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101101 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101101 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101101 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101101 TO monitoring;
GRANT SELECT ON TABLE reports_20101101 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101101 TO breakpad;


--
-- Name: reports_20101108; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101108 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101108 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101108 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101108 TO monitoring;
GRANT SELECT ON TABLE reports_20101108 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101108 TO breakpad;


--
-- Name: reports_20101115; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101115 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101115 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101115 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101115 TO monitoring;
GRANT SELECT ON TABLE reports_20101115 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101115 TO breakpad;


--
-- Name: reports_20101122; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101122 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101122 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101122 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101122 TO monitoring;
GRANT SELECT ON TABLE reports_20101122 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101122 TO breakpad;


--
-- Name: reports_20101129; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101129 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101129 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101129 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101129 TO monitoring;
GRANT SELECT ON TABLE reports_20101129 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101129 TO breakpad;


--
-- Name: reports_20101206; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101206 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101206 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101206 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101206 TO monitoring;
GRANT SELECT ON TABLE reports_20101206 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101206 TO breakpad;


--
-- Name: reports_20101213; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101213 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101213 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101213 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101213 TO monitoring;
GRANT SELECT ON TABLE reports_20101213 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101213 TO breakpad;


--
-- Name: reports_20101220; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101220 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101220 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101220 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101220 TO monitoring;
GRANT SELECT ON TABLE reports_20101220 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101220 TO breakpad;


--
-- Name: reports_20101227; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20101227 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20101227 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20101227 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20101227 TO monitoring;
GRANT SELECT ON TABLE reports_20101227 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20101227 TO breakpad;


--
-- Name: reports_20110103; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110103 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110103 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110103 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110103 TO monitoring;
GRANT SELECT ON TABLE reports_20110103 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110103 TO breakpad;


--
-- Name: reports_20110110; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110110 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110110 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110110 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110110 TO monitoring;
GRANT SELECT ON TABLE reports_20110110 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110110 TO breakpad;


--
-- Name: reports_20110117; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110117 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110117 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110117 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110117 TO monitoring;
GRANT SELECT ON TABLE reports_20110117 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110117 TO breakpad;


--
-- Name: reports_20110124; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110124 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110124 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110124 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110124 TO monitoring;
GRANT SELECT ON TABLE reports_20110124 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110124 TO breakpad;


--
-- Name: reports_20110131; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110131 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110131 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110131 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110131 TO monitoring;
GRANT SELECT ON TABLE reports_20110131 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110131 TO breakpad;


--
-- Name: reports_20110207; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110207 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110207 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110207 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110207 TO monitoring;
GRANT SELECT ON TABLE reports_20110207 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110207 TO breakpad;


--
-- Name: reports_20110214; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110214 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110214 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110214 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110214 TO monitoring;
GRANT SELECT ON TABLE reports_20110214 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110214 TO breakpad;


--
-- Name: reports_20110221; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110221 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110221 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110221 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110221 TO breakpad;
GRANT SELECT ON TABLE reports_20110221 TO breakpad_ro;


--
-- Name: reports_20110228; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110228 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110228 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110228 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110228 TO breakpad;
GRANT SELECT ON TABLE reports_20110228 TO breakpad_ro;


--
-- Name: reports_20110307; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110307 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110307 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110307 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110307 TO breakpad;
GRANT SELECT ON TABLE reports_20110307 TO breakpad_ro;


--
-- Name: reports_20110314; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110314 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110314 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110314 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110314 TO breakpad;
GRANT SELECT ON TABLE reports_20110314 TO breakpad_ro;


--
-- Name: reports_20110321; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110321 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110321 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110321 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110321 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110321 TO breakpad;


--
-- Name: reports_20110328; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110328 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110328 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110328 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110328 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110328 TO breakpad;


--
-- Name: reports_20110404; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110404 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110404 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110404 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110404 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110404 TO breakpad;


--
-- Name: reports_20110411; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110411 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110411 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110411 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110411 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110411 TO breakpad;


--
-- Name: reports_20110418; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110418 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110418 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110418 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110418 TO breakpad_ro;
GRANT SELECT ON TABLE reports_20110418 TO breakpad;


--
-- Name: reports_20110425; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110425 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110425 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110425 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110425 TO breakpad;


--
-- Name: reports_20110502; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110502 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110502 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110502 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110502 TO breakpad;


--
-- Name: reports_20110509; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110509 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110509 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110509 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110509 TO breakpad;


--
-- Name: reports_20110516; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110516 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110516 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110516 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110516 TO breakpad;


--
-- Name: reports_20110523; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110523 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110523 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110523 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110523 TO breakpad;


--
-- Name: reports_20110530; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110530 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110530 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110530 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110530 TO breakpad;


--
-- Name: reports_20110606; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110606 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110606 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110606 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110606 TO breakpad;


--
-- Name: reports_20110613; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110613 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110613 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110613 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110613 TO breakpad;


--
-- Name: reports_20110620; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110620 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110620 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110620 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110620 TO breakpad;


--
-- Name: reports_20110627; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110627 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110627 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110627 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110627 TO breakpad;


--
-- Name: reports_20110704; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110704 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110704 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110704 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110704 TO breakpad;


--
-- Name: reports_20110711; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110711 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110711 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110711 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110711 TO breakpad;


--
-- Name: reports_20110718; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110718 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110718 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110718 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110718 TO breakpad;


--
-- Name: reports_20110725; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110725 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110725 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110725 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110725 TO breakpad;


--
-- Name: reports_20110801; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110801 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110801 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110801 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110801 TO breakpad;


--
-- Name: reports_20110808; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_20110808 FROM PUBLIC;
REVOKE ALL ON TABLE reports_20110808 FROM breakpad_rw;
GRANT ALL ON TABLE reports_20110808 TO breakpad_rw;
GRANT SELECT ON TABLE reports_20110808 TO breakpad;


--
-- Name: reports_duplicates; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE reports_duplicates FROM PUBLIC;
REVOKE ALL ON TABLE reports_duplicates FROM breakpad_rw;
GRANT ALL ON TABLE reports_duplicates TO breakpad_rw;
GRANT SELECT ON TABLE reports_duplicates TO breakpad_ro;
GRANT SELECT ON TABLE reports_duplicates TO breakpad;


--
-- Name: seq_reports_id; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE seq_reports_id FROM PUBLIC;
REVOKE ALL ON SEQUENCE seq_reports_id FROM breakpad_rw;
GRANT ALL ON SEQUENCE seq_reports_id TO breakpad_rw;


--
-- Name: sequence_numbers; Type: ACL; Schema: public; Owner: postgres
--

REVOKE ALL ON TABLE sequence_numbers FROM PUBLIC;
REVOKE ALL ON TABLE sequence_numbers FROM postgres;
GRANT ALL ON TABLE sequence_numbers TO postgres;
GRANT SELECT ON TABLE sequence_numbers TO breakpad;
GRANT SELECT ON TABLE sequence_numbers TO breakpad_ro;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE sequence_numbers TO breakpad_rw;


--
-- Name: server_status; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE server_status FROM PUBLIC;
REVOKE ALL ON TABLE server_status FROM breakpad_rw;
GRANT ALL ON TABLE server_status TO breakpad_rw;
GRANT SELECT ON TABLE server_status TO monitoring;
GRANT SELECT ON TABLE server_status TO breakpad_ro;
GRANT SELECT ON TABLE server_status TO breakpad;


--
-- Name: server_status_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE server_status_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE server_status_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE server_status_id_seq TO breakpad_rw;


--
-- Name: sessions; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE sessions FROM PUBLIC;
REVOKE ALL ON TABLE sessions FROM breakpad_rw;
GRANT ALL ON TABLE sessions TO breakpad_rw;
GRANT SELECT ON TABLE sessions TO breakpad_ro;
GRANT SELECT ON TABLE sessions TO breakpad;


--
-- Name: signature_bugs_rollup; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signature_bugs_rollup FROM PUBLIC;
REVOKE ALL ON TABLE signature_bugs_rollup FROM breakpad_rw;
GRANT ALL ON TABLE signature_bugs_rollup TO breakpad_rw;
GRANT SELECT ON TABLE signature_bugs_rollup TO breakpad_ro;
GRANT SELECT ON TABLE signature_bugs_rollup TO breakpad;
GRANT ALL ON TABLE signature_bugs_rollup TO monitor;


--
-- Name: signature_build; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signature_build FROM PUBLIC;
REVOKE ALL ON TABLE signature_build FROM breakpad_rw;
GRANT ALL ON TABLE signature_build TO breakpad_rw;
GRANT SELECT ON TABLE signature_build TO breakpad_ro;
GRANT SELECT ON TABLE signature_build TO breakpad;


--
-- Name: signature_first; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signature_first FROM PUBLIC;
REVOKE ALL ON TABLE signature_first FROM breakpad_rw;
GRANT ALL ON TABLE signature_first TO breakpad_rw;
GRANT SELECT ON TABLE signature_first TO breakpad_ro;
GRANT SELECT ON TABLE signature_first TO breakpad;


--
-- Name: signature_productdims; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signature_productdims FROM PUBLIC;
REVOKE ALL ON TABLE signature_productdims FROM breakpad_rw;
GRANT ALL ON TABLE signature_productdims TO breakpad_rw;
GRANT SELECT ON TABLE signature_productdims TO monitoring;
GRANT SELECT ON TABLE signature_productdims TO breakpad_ro;
GRANT SELECT ON TABLE signature_productdims TO breakpad;


--
-- Name: signature_products; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signature_products FROM PUBLIC;
REVOKE ALL ON TABLE signature_products FROM breakpad_rw;
GRANT ALL ON TABLE signature_products TO breakpad_rw;
GRANT SELECT ON TABLE signature_products TO breakpad_ro;
GRANT SELECT ON TABLE signature_products TO breakpad;
GRANT ALL ON TABLE signature_products TO monitor;


--
-- Name: signature_products_rollup; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signature_products_rollup FROM PUBLIC;
REVOKE ALL ON TABLE signature_products_rollup FROM breakpad_rw;
GRANT ALL ON TABLE signature_products_rollup TO breakpad_rw;
GRANT SELECT ON TABLE signature_products_rollup TO breakpad_ro;
GRANT SELECT ON TABLE signature_products_rollup TO breakpad;
GRANT ALL ON TABLE signature_products_rollup TO monitor;


--
-- Name: signatures; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE signatures FROM PUBLIC;
REVOKE ALL ON TABLE signatures FROM breakpad_rw;
GRANT ALL ON TABLE signatures TO breakpad_rw;
GRANT SELECT ON TABLE signatures TO breakpad_ro;
GRANT SELECT ON TABLE signatures TO breakpad;
GRANT ALL ON TABLE signatures TO monitor;


--
-- Name: tcbs; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE tcbs FROM PUBLIC;
REVOKE ALL ON TABLE tcbs FROM breakpad_rw;
GRANT ALL ON TABLE tcbs TO breakpad_rw;
GRANT SELECT ON TABLE tcbs TO breakpad_ro;
GRANT SELECT ON TABLE tcbs TO breakpad;
GRANT ALL ON TABLE tcbs TO monitor;


--
-- Name: tcbs_ranking; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE tcbs_ranking FROM PUBLIC;
REVOKE ALL ON TABLE tcbs_ranking FROM breakpad_rw;
GRANT ALL ON TABLE tcbs_ranking TO breakpad_rw;
GRANT SELECT ON TABLE tcbs_ranking TO breakpad_ro;
GRANT SELECT ON TABLE tcbs_ranking TO breakpad;
GRANT ALL ON TABLE tcbs_ranking TO monitor;


--
-- Name: top_crashes_by_signature_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE top_crashes_by_signature_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE top_crashes_by_signature_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE top_crashes_by_signature_id_seq TO breakpad_rw;


--
-- Name: top_crashes_by_url; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE top_crashes_by_url FROM PUBLIC;
REVOKE ALL ON TABLE top_crashes_by_url FROM breakpad_rw;
GRANT ALL ON TABLE top_crashes_by_url TO breakpad_rw;
GRANT SELECT ON TABLE top_crashes_by_url TO monitoring;
GRANT SELECT ON TABLE top_crashes_by_url TO breakpad_ro;
GRANT SELECT ON TABLE top_crashes_by_url TO breakpad;


--
-- Name: top_crashes_by_url_id_seq; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE top_crashes_by_url_id_seq FROM PUBLIC;
REVOKE ALL ON SEQUENCE top_crashes_by_url_id_seq FROM breakpad_rw;
GRANT ALL ON SEQUENCE top_crashes_by_url_id_seq TO breakpad_rw;


--
-- Name: top_crashes_by_url_signature; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE top_crashes_by_url_signature FROM PUBLIC;
REVOKE ALL ON TABLE top_crashes_by_url_signature FROM breakpad_rw;
GRANT ALL ON TABLE top_crashes_by_url_signature TO breakpad_rw;
GRANT SELECT ON TABLE top_crashes_by_url_signature TO monitoring;
GRANT SELECT ON TABLE top_crashes_by_url_signature TO breakpad_ro;
GRANT SELECT ON TABLE top_crashes_by_url_signature TO breakpad;


--
-- Name: topcrashurlfactsreports; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE topcrashurlfactsreports FROM PUBLIC;
REVOKE ALL ON TABLE topcrashurlfactsreports FROM breakpad_rw;
GRANT ALL ON TABLE topcrashurlfactsreports TO breakpad_rw;
GRANT SELECT ON TABLE topcrashurlfactsreports TO monitoring;
GRANT SELECT ON TABLE topcrashurlfactsreports TO breakpad_ro;
GRANT SELECT ON TABLE topcrashurlfactsreports TO breakpad;


--
-- Name: topcrashurlfactsreports_id_seq1; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE topcrashurlfactsreports_id_seq1 FROM PUBLIC;
REVOKE ALL ON SEQUENCE topcrashurlfactsreports_id_seq1 FROM breakpad_rw;
GRANT ALL ON SEQUENCE topcrashurlfactsreports_id_seq1 TO breakpad_rw;


--
-- Name: urldims; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON TABLE urldims FROM PUBLIC;
REVOKE ALL ON TABLE urldims FROM breakpad_rw;
GRANT ALL ON TABLE urldims TO breakpad_rw;
GRANT SELECT ON TABLE urldims TO monitoring;
GRANT SELECT ON TABLE urldims TO breakpad_ro;
GRANT SELECT ON TABLE urldims TO breakpad;


--
-- Name: urldims_id_seq1; Type: ACL; Schema: public; Owner: breakpad_rw
--

REVOKE ALL ON SEQUENCE urldims_id_seq1 FROM PUBLIC;
REVOKE ALL ON SEQUENCE urldims_id_seq1 FROM breakpad_rw;
GRANT ALL ON SEQUENCE urldims_id_seq1 TO breakpad_rw;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: -; Owner: processor
--

ALTER DEFAULT PRIVILEGES FOR ROLE processor REVOKE ALL ON SEQUENCES  FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE processor REVOKE ALL ON SEQUENCES  FROM processor;
ALTER DEFAULT PRIVILEGES FOR ROLE processor GRANT ALL ON SEQUENCES  TO processor;
ALTER DEFAULT PRIVILEGES FOR ROLE processor GRANT ALL ON SEQUENCES  TO breakpad_rw;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: -; Owner: monitor
--

ALTER DEFAULT PRIVILEGES FOR ROLE monitor REVOKE ALL ON SEQUENCES  FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE monitor REVOKE ALL ON SEQUENCES  FROM monitor;
ALTER DEFAULT PRIVILEGES FOR ROLE monitor GRANT ALL ON SEQUENCES  TO monitor;
ALTER DEFAULT PRIVILEGES FOR ROLE monitor GRANT ALL ON SEQUENCES  TO breakpad_rw;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres REVOKE ALL ON TABLES  FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres REVOKE ALL ON TABLES  FROM postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TABLES  TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT SELECT ON TABLES  TO breakpad_ro;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES  FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES  FROM postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT ON TABLES  TO breakpad;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON TABLES  TO monitor;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: processor
--

ALTER DEFAULT PRIVILEGES FOR ROLE processor REVOKE ALL ON TABLES  FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE processor REVOKE ALL ON TABLES  FROM processor;
ALTER DEFAULT PRIVILEGES FOR ROLE processor GRANT ALL ON TABLES  TO processor;
ALTER DEFAULT PRIVILEGES FOR ROLE processor GRANT ALL ON TABLES  TO breakpad_rw;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: monitor
--

ALTER DEFAULT PRIVILEGES FOR ROLE monitor REVOKE ALL ON TABLES  FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE monitor REVOKE ALL ON TABLES  FROM monitor;
ALTER DEFAULT PRIVILEGES FOR ROLE monitor GRANT ALL ON TABLES  TO monitor;
ALTER DEFAULT PRIVILEGES FOR ROLE monitor GRANT ALL ON TABLES  TO breakpad_rw;


--
-- PostgreSQL database dump complete
--

