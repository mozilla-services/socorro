CREATE OR REPLACE FUNCTION update_signatures_hourly(
    fromtime timestamp with time zone,
    fortime interval DEFAULT '01:00:00'::interval,
    checkdata boolean DEFAULT true
)
    RETURNS boolean
    LANGUAGE plpgsql
    SET "TimeZone" TO 'UTC'
AS $$
DECLARE
    newfortime INTERVAL;
BEGIN

-- Function for updating signature information
-- designed to be run once per UTC day.
-- running it repeatedly won't cause issues
-- combines NULL and empty signatures

-- since we do allow dynamic timestamps, check if we split over a week
-- boundary.  if so, call self recursively for the first half of the period

IF (week_begins_utc(fromtime) <> week_begins_utc(fromtime + fortime - interval '1 second')) THEN
        PERFORM update_signatures_hourly(
            fromtime,
            (week_begins_utc(fromtime + fortime) - fromtime),
            checkdata
        );
        newfortime := (fromtime + fortime) - week_begins_utc(fromtime + fortime);
        fromtime := week_begins_utc( fromtime + fortime );
        fortime := newfortime;
END IF;

-- prevent calling for a period of more than one day

IF fortime > INTERVAL '1 day' THEN
    RAISE NOTICE 'You may not execute this function on more than one day of data.';
    RETURN FALSE;
END IF;

-- create temporary table

create temporary table new_signatures
on commit drop as
select coalesce(signature,'') as signature,
    product::citext as product,
    version::citext as version,
    build, NULL::INT as product_version_id,
    min(date_processed) as first_report
from reports
where date_processed >= fromtime
    and date_processed < (fromtime + fortime)
group by signature, product, version, build;

PERFORM 1 FROM new_signatures;
IF NOT FOUND THEN
    IF checkdata THEN
        RAISE NOTICE 'No signature data found in reports for the range  % to %',fromtime,fromtime + fortime;
        RETURN FALSE;
    END IF;
END IF;

ANALYZE new_signatures;

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
    and product_versions.build_type_enum IN ('release','nightly', 'aurora')
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

RETURN TRUE;
END;
$$;
