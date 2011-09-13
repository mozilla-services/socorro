-- create table for possible duplicates
-- not partitioned, for now

\set ON_ERROR_STOP true
SET work_mem = '128MB';
SET maintenance_work_mem = '256MB';
SET temp_buffers = '128MB';

BEGIN;

create table reports_duplicates (
	uuid text not null primary key,
	duplicate_of text not null,
	date_processed timestamp not null
);

create index reports_duplicates_leader on reports_duplicates(duplicate_of);

alter table reports_duplicates owner to breakpad_rw;

-- SQL function to make comparing timestamp deltas a bit
-- less verbose

create or replace function same_time_fuzzy(
	date1 timestamptz, date2 timestamptz,
	interval_secs1 int, interval_secs2 int
) returns boolean
language sql as $f$
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
$f$;

-- function to be called hourly to update
-- possible duplicates table

create or replace function update_reports_duplicates (
	start_time timestamp, end_time timestamp )
returns int
set work_mem = '256MB'
set temp_buffers = '128MB'
language plpgsql as $f$
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
end;$f$;

COMMIT;
