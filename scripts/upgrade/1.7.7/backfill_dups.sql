-- one-time function to backfill possible dups for all history

create or replace function backfill_all_dups (
	start_date timestamp, end_date timestamp )
returns boolean
language plpgsql as $f$
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
end; $f$;




create or replace function backfill_reports_duplicates (
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
end;$f$;



	

