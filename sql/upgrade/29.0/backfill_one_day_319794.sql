\set ON_ERROR_STOP 1

BEGIN;

CREATE OR REPLACE FUNCTION public.backfill_one_day(bkdate date)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
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

END; $function$
;

COMMIT;
