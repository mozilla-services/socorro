\set ON_ERROR_STOP 1

-- adu by build date

SELECT create_table_if_not_exists ( 
-- new table name here
'build_adu', 
-- full SQL create table statement here
$q$
create table build_adu (
    product_version_id int not null,
    build_date date not null,
    adu_date DATE not null,
    os_name citext not null,
    adu_count INT not null,
    constraint build_adu_key primary key ( product_version_id, build_date, adu_date )
);$q$, 
-- owner of table; always breakpad_rw
'breakpad_rw' );


-- daily update function
CREATE OR REPLACE FUNCTION update_build_adu (
    updateday DATE, checkdata BOOLEAN default TRUE )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
SET client_min_messages = 'ERROR'
AS $f$
BEGIN
-- this function populates a daily matview
-- for **new_matview_description**
-- depends on the new reports_clean

-- check if we've been run
IF checkdata THEN
    PERFORM 1 FROM build_adu
    WHERE report_date = updateday
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

INSERT INTO build_adu ( product_version_id, os_name,
        build_date, adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    build_date(prod_adu.build_id)
    coalesce(sum(adu_count), 0)
FROM product_versions
    LEFT OUTER JOIN ( 
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            raw_adu.adu_count,
            build_numeric(raw_adu.build) as build_id,
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

INSERT INTO build_adu ( product_version_id, os_name,
        adu_date, build_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    build_date(prod_adu.build_id),
    coalesce(sum(adu_count), 0)
FROM product_versions
    LEFT OUTER JOIN ( 
        SELECT COALESCE(prodmap.product_name, raw_adu.product_name)::citext
            as product_name, raw_adu.product_version::citext as product_version,
            raw_adu.build_channel::citext as build_channel,
            build_numeric(raw_adu.build) as build_id,
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

INSERT INTO build_adu ( product_version_id, os_name,
        adu_date, adu_count )
SELECT product_version_id, coalesce(os_name,'Unknown') as os,
    updateday,
    build_date(prod_adu.build_id),
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
END; $f$;

-- now create a backfill function 
-- so that we can backfill missing data
CREATE OR REPLACE FUNCTION backfill_build_adu(
    updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$f$
BEGIN

DELETE FROM build_adu WHERE report_date = updateday;
PERFORM update_build_adu(updateday, false);

RETURN TRUE;
END; $f$;


-- sample backfill script
-- for initialization
DO $f$
DECLARE 
    thisday DATE := **first_day_of_backfill**;
    lastday DATE;
BEGIN

    -- set backfill to the last day we have ADU for
    SELECT max("date") 
    INTO lastday
    FROM raw_adu;
    
    WHILE thisday <= lastday LOOP
    
        RAISE INFO 'backfilling %', thisday;
    
        PERFORM backfill_build_adu(thisday);
        
        thisday := thisday + 1;
        
    END LOOP;
    
END;$f$;