
\set ON_ERROR_STOP
set work_mem = '256MB';
set maintenance_work_mem = '256MB';

begin;

create table signature_build
as select signature, null::int as productdims_id, product::citext as product, version::citext as version, os_name::citext as os_name, build, min(date_processed) as first_report
from reports
where signature IS NOT NULL
	and date_processed BETWEEN '2011-03-01' AND '2011-04-01'
group by signature, product::citext, version::citext, os_name::citext, build
order by signature, product, version, os_name, build;

alter table signature_build owner to breakpad_rw;

create unique index signature_build_key on signature_build 
	( signature, product, version, os_name, build );
create index signature_build_signature on signature_build ( signature );
create index signature_build_product on signature_build ( product, version );

update signature_build set productdims_id = productdims.id
from productdims
where productdims.product = signature_build.product
	and productdims.version = signature_build.version;
	
create index signature_build_productdims on signature_build(productdims_id);

create table signature_first (
	signature text,
	productdims_id int,
	osdims_id int,
	first_report timestamp,
	first_build text,
	constraint signature_first_key primary key (signature, productdims_id, osdims_id)
);

alter table signature_first owner to breakpad_rw;

insert into signature_first (signature, productdims_id, osdims_id,
	first_report, first_build )
select sbup.signature, sbup.productdims_id, osdims.id, min(sbup.first_report),
	min(sbup.build)
from signature_build sbup
	join top_crashes_by_signature tcbs on
		sbup.signature = tcbs.signature
		and sbup.productdims_id = tcbs.productdims_id
	join osdims ON tcbs.osdims_id = osdims.id
where sbup.os_name = osdims.os_name
	and tcbs.window_end BETWEEN '2011-03-01' AND '2011-04-01'
group by sbup.signature, sbup.productdims_id, osdims.id;

commit;


begin;

lock table signature_productdims NOWAIT;
alter table signature_productdims add column first_report timestamp with time zone;
truncate signature_productdims;
insert into signature_productdims ( signature, productdims_id, first_report )
select signature, productdims_id, min(first_report)
from signature_build
	join productdims USING (product, version)
group by signature, productdims_id
order by signature, productdims_id;

commit;


----------------------------

-- %s = current_timestamp
-- %w = # hours behind -- start with 3
-- %h = # hours for total window -- start with 2

CREATE OR REPLACE FUNCTION update_signature_matviews (
	currenttime TIMESTAMP, hours_back INTEGER, hours_window INTEGER )
RETURNS BOOLEAN
LANGUAGE plpgsql AS $f$
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
group by sbup.signature, sbup.productdims_id, osdims.id;


RETURN TRUE;
END;
$f$;
