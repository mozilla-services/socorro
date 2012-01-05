\set ON_ERROR_STOP 1

set timezone = 'UTC';

drop table if exists timestamp_tables;
create table timestamp_tables ( tablename text );
insert into timestamp_tables values 
	( 'daily_crashes' ),
	( 'extensions' ),
	( 'extensions_2%' ),
	( 'frames' ),
	( 'jobs' ),
	( 'plugins_reports' ),
	( 'plugins_reports_2%'),
	( 'raw_adu' ),
	( 'reports' ),
	( 'reports_2%' ),
	( 'server_status' ),
	( 'signature_build' ),
	( 'signature_first' ),
	( 'signature_products' ),
	( 'signatures' );


DO $f$
DECLARE frame_name TEXT;
	curtab TEXT;
	currel INT;
	curcol TEXT;
BEGIN

SET timezone = 'UTC';

-- drop all frames partitions
RAISE INFO 'dropping frames';
FOR frame_name IN SELECT relname FROM pg_stat_user_tables
	WHERE relname LIKE 'frames_2%' LOOP
	
	EXECUTE 'DROP TABLE ' || frame_name;
	
END LOOP;

-- create table of constraints

RAISE INFO 'creating table of constraints';
DROP TABLE IF EXISTS partition_constraints;
CREATE TABLE partition_constraints AS 
SELECT 'ALTER TABLE ' || relname || ' ADD CONSTRAINT ' || relname 
	|| '_date_check CHECK  ( date_processed >= ' 
	|| quote_literal(week_begins_partition_string( relname ))
	|| ' AND date_processed < ' 
	|| quote_literal(week_ends_partition_string( relname ))
	|| ');'
FROM timestamp_tables JOIN pg_stat_user_tables
	ON relname ILIKE tablename
WHERE relname LIKE '%_20%'
ORDER BY relname;

-- where tables are partitions, drop the constraints from each
RAISE INFO 'dropping constraints';
FOR curtab IN SELECT relname 
	FROM timestamp_tables JOIN pg_stat_user_tables
		ON relname ILIKE tablename
	WHERE relname LIKE '%_20%'
	ORDER BY relname LOOP
	
	EXECUTE 'ALTER TABLE ' || curtab || ' DROP CONSTRAINT ' 
		|| curtab || '_date_check;';
		
END LOOP;

-- truncate some tables

RAISE INFO 'truncating tables';
TRUNCATE TABLE processors CASCADE;
TRUNCATE TABLE server_status CASCADE;

-- modify each column of each table
RAISE INFO 'changing columns';
FOR currel, curcol IN 
	SELECT pg_class.oid, attname
	FROM pg_class JOIN pg_attribute ON pg_class.oid = attrelid
		JOIN timestamp_tables ON pg_class.relname ILIKE timestamp_tables.tablename
	WHERE atttypid = 1114
		AND relkind = 'r'
	ORDER BY relname, attnum LOOP
	
	UPDATE pg_attribute SET atttypid = 1184
	WHERE attrelid = currel
		AND attname::text = curcol;

END LOOP;

-- modify each column of each index
RAISE INFO 'changing indexes';
FOR currel, curcol IN 
	SELECT indclass.oid, attname
	FROM pg_class indclass JOIN pg_attribute ON indclass.oid = attrelid
		JOIN pg_index ON indclass.oid = indexrelid
		JOIN pg_class relclass on indrelid = relclass.oid
		JOIN timestamp_tables ON relclass.relname ILIKE timestamp_tables.tablename
	WHERE atttypid = 1114
		AND indclass.relkind = 'i'
		AND relclass.relkind = 'r'
	ORDER BY relclass.relname, indclass.relname, attnum LOOP
	
	UPDATE pg_attribute SET atttypid = 1184
	WHERE attrelid = currel
		AND attname::text = curcol;

END LOOP;

-- done

RAISE INFO 'done with datatype changes.  Now run the restore for the constraints';

END;
$f$;

\copy partition_constraints to partition_constraints.txt





