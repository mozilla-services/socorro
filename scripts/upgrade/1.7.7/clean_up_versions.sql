
-- install citext in the database

begin;
lock table productdims;
drop view performance_check_1;
drop view branches;
alter table productdims add column sort_key int;
drop index productdims_release_key;
drop index productdims_product_version_key;
alter table productdims alter column product type citext;
alter table productdims alter column version type citext;
create unique index productdims_product_version_key on productdims (product, version);
create index productdims_sort_key on productdims (product, sort_key);
create view performance_check_1 as
 SELECT productdims.product, top_crashes_by_signature.signature, count(*) AS count
   FROM top_crashes_by_signature
   JOIN productdims ON top_crashes_by_signature.productdims_id = productdims.id
  WHERE top_crashes_by_signature.window_end > (now() - '1 day'::interval)
  GROUP BY productdims.product, top_crashes_by_signature.signature
  ORDER BY count(*)
 LIMIT 50;
create view branches as
 SELECT productdims.product, productdims.version, productdims.branch
   FROM productdims;
commit;

begin;
lock table builds;
alter table builds drop constraint builds_key;
alter table builds alter column product type citext;
alter table builds alter column version type citext;
alter table builds alter column platform type citext;
create unique index builds_key on builds (product, version, platform, buildid);
commit;

create table productdims_version_sort (
	id int not null unique,
	product citext not null,
	version citext not null,
	sec1_num1 int,
	sec1_string1 text,
	sec1_num2 int,
	sec1_string2 text,
	sec2_num1 int,
	sec2_string1 text,
	sec2_num2 int,
	sec2_string2 text,
	sec3_num1 int,
	sec3_string1 text,
	sec3_num2 int,
	sec3_string2 text,
	extra text,
	constraint productdims_version_sort_key primary key (product, version),
	constraint productdims_product_version_fkey foreign key ( product, version ) 
		references productdims(product, version) on delete cascade on update cascade
);

ALTER TABLE productdims_version_sort OWNER TO breakpad_rw;

INSERT INTO productdims_version_sort 
SELECT id, product, version, 
	(tokenize_version(version)).*
FROM productdims
ORDER BY product, version;

update productdims
	set sort_key = running_count
from (
	select product, version, 
		row_number() over ( partition by product
			order by sec1_num1 ASC NULLS FIRST,
					sec1_string1 ASC NULLS LAST,
					sec1_num2 ASC NULLS FIRST,
					sec1_string2 ASC NULLS LAST,
					sec2_num1 ASC NULLS FIRST,
					sec2_string1 ASC NULLS LAST,
					sec2_num2 ASC NULLS FIRST,
					sec2_string2 ASC NULLS LAST,
					sec3_num1 ASC NULLS FIRST,
					sec3_string1 ASC NULLS LAST,
					sec3_num2 ASC NULLS FIRST,
					sec3_string2 ASC NULLS LAST,
					extra ASC NULLS FIRST)
					as running_count
	 from productdims_version_sort ) as sorter
where productdims.product = sorter.product
	and productdims.version = sorter.version;

CREATE OR REPLACE FUNCTION product_version_sort_number (
	sproduct text )
RETURNS BOOLEAN
LANGUAGE plpgsql AS $f$
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
END;$f$;

CREATE OR REPLACE FUNCTION version_sort_insert_trigger ()
RETURNS TRIGGER
LANGUAGE plpgsql AS $f$
BEGIN
-- updates productdims_version_sort and adds a sort_key
-- for sorting, renumbering all products-versions if
-- required

-- add new sort record
INSERT INTO productdims_version_sort (
	id,
	product,
	version,
	sec1_num1,	sec1_string1,	sec1_num2,	sec1_string2,
	sec2_num1,	sec2_string1,	sec2_num2,	sec2_string2,
	sec3_num1,	sec3_string1,	sec3_num2,	sec3_string2,
	extra )
SELECT 
	NEW.id,
	NEW.product,
	NEW.version,
	s1n1,	s1s1,	s1n2,	s1s2,
	s2n1,	s2s1,	s2n2,	s2s2,
	s3n1,	s3s1,	s3n2,	s3s2,
	ext 
FROM tokenize_version(NEW.version);

-- update sort key
PERFORM product_version_sort_number(NEW.product);

RETURN NEW;
END; $f$;

CREATE TRIGGER version_sort_insert_trigger AFTER INSERT
ON productdims FOR EACH ROW EXECUTE PROCEDURE version_sort_insert_trigger();

CREATE OR REPLACE FUNCTION version_sort_update_trigger_before ()
RETURNS TRIGGER 
LANGUAGE plpgsql AS $f$
BEGIN
-- updates productdims_version_sort
-- should be called only by a cascading update from productdims

-- update sort record
SELECT 	s1n1,	s1s1,	s1n2,	s1s2,
	s2n1,	s2s1,	s2n2,	s2s2,
	s3n1,	s3s1,	s3n2,	s3s2,
	ext
INTO 
	NEW.sec1_num1,	NEW.sec1_string1,	NEW.sec1_num2,	NEW.sec1_string2,
	NEW.sec2_num1,	NEW.sec2_string1,	NEW.sec2_num2,	NEW.sec2_string2,
	NEW.sec3_num1,	NEW.sec3_string1,	NEW.sec3_num2,	NEW.sec3_string2,
	NEW.extra
FROM tokenize_version(NEW.version);

RETURN NEW;
END; $f$;

CREATE OR REPLACE FUNCTION version_sort_update_trigger_after ()
RETURNS TRIGGER 
LANGUAGE plpgsql AS $f$
BEGIN
-- update sort keys
PERFORM product_version_sort_number(NEW.product);
RETURN NEW;
END; $f$;

CREATE TRIGGER version_sort_update_trigger_before BEFORE UPDATE
ON productdims_version_sort FOR EACH ROW 
EXECUTE PROCEDURE version_sort_update_trigger_before();

CREATE TRIGGER version_sort_update_trigger_after AFTER UPDATE
ON productdims_version_sort FOR EACH ROW 
EXECUTE PROCEDURE version_sort_update_trigger_after();
