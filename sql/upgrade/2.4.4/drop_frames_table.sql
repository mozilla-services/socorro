/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

DELETE FROM report_partition_info WHERE table_name = 'frames';

DO $f$
DECLARE curpart TEXT;
BEGIN

FOR curpart IN SELECT relname FROM pg_stat_user_tables
	WHERE relname LIKE 'frames_20%' LOOP
	
	IF try_lock_table(curpart,'ACCESS EXCLUSIVE') THEN
	
		EXECUTE 'ALTER TABLE ' || curpart ||
			' DROP CONSTRAINT ' || curpart || '_report_id_fkey';
			
		RAISE NOTICE 'dropped fk for %',curpart;
		
	ELSE
	
		RAISE NOTICE 'unable to drop fks for %',curpart;
			
	END IF;
	
	
END LOOP;
END;
$f$;

DROP TABLE frames CASCADE;