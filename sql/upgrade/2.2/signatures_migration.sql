\set ON_ERROR_STOP 1

set work_mem = '1GB';
set maintenance_work_mem = '1GB';

begin;

-- populate signatures

insert into signatures ( signature, first_report, first_build )
select signature, min(first_report), min(first_build)::numeric
from signature_first where first_build ~ $x$^\d+$$x$
group by signature;

-- populate signature_products

insert into signature_products (product_version_id, signature_id, first_report)
select product_versions.product_version_id,
	signatures.signature_id,
	min(signature_productdims.first_report)
from product_versions
	join productdims ON product_versions.product_name = productdims.product
		and product_versions.version_string = productdims.version
	join signature_productdims on
		productdims.id = signature_productdims.productdims_id
	join signatures
		ON coalesce(signature_productdims.signature, '') = signatures.signature
group by product_versions.product_version_id,
	signatures.signature_id;

analyze signatures;
analyze signature_products;

insert into signature_products_rollup ( signature_id, product_name, ver_count, version_list )
select
	signature_id, product_name,
    count(*) as ver_count,
		array_accum(version_string ORDER BY product_versions.version_sort)
from signature_products JOIN product_versions
	USING (product_version_id)
group by signature_id, product_name;

analyze signature_products_rollup;

INSERT INTO signature_bugs_rollup
SELECT signature_id, count(*), array_accum(bug_id)
FROM signatures JOIN bug_associations USING (signature)
GROUP BY signature_id;

analyze signature_bugs_rollup;


commit;

----------------------------

-- %s = current_timestamp
-- %w = # hours behind -- start with 3
-- %h = # hours for total window -- start with 2

CREATE OR REPLACE FUNCTION update_signatures (
	updateday DATE )
RETURNS BOOLEAN
LANGUAGE plpgsql
SET work_mem = '512MB'
SET temp_buffers = '512MB'
AS $f$
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
$f$;


