create or replace function create_weekly_partition(
	tablename citext, theweek date, partcol text default 'date_processed', 
	tableowner text default '', 
	uniques text[] default '{}',
	indexes text[] default '{}', 
	fkeys text[] default '{}',
	is_utc BOOLEAN default false,
	timetype text default 'TIMESTAMP' )
returns boolean
language plpgsql 
as $f$
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
$f$;


select create_table_if_not_exists ( 'report_partition_info', $x$
CREATE TABLE report_partition_info (
	table_name citext not null primary key,
	build_order int not null default 1,
	keys text[] not null default '{}',
	indexes text[] not null default '{}',
	fkeys text[] not null default '{}'
);

INSERT INTO report_partition_info 
VALUES ( 'reports', 1, ARRAY [ 'id', 'uuid' ], 
	ARRAY [ 'date_processed', 'hangid', 'product,version', 'reason', 'signature','url' ], '{}' ),
	( 'plugins_reports', 2, ARRAY [ 'report_id,plugin_id' ],
	ARRAY [ 'report_id,date_processed' ],
	ARRAY [ '(plugin_id) REFERENCES plugins(id)', '(report_id) REFERENCES reports_WEEKNUM(id)'] ),
	( 'extensions', 3, ARRAY [ 'report_id,extension_key' ],
		ARRAY [ 'extension_id,extension_version', 'report_id,date_processed' ],
		ARRAY [ '(report_id) REFERENCES reports_WEEKNUM(id)' ] ),
	( 'frames', 4, ARRAY [ 'report_id,frame_num' ],
		ARRAY [ 'report_id,date_processed' ],
		ARRAY [ '(report_id) REFERENCES reports_WEEKNUM(id)' ] );
$x$,'breakpad_rw', NULL );
	

create or replace function weekly_report_partitions (
	numweeks int default 2, 
	targetdate timestamptz default null  )
returns boolean
language plpgsql
as $f$
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
	
END; $f$;







