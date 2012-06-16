/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */


DO $f$
DECLARE rc_part TEXT;
BEGIN
	SET maintenance_work_mem = '512MB';

	FOR rc_part IN SELECT relname FROM pg_stat_user_tables
		WHERE relname LIKE 'reports_clean_201%'
		ORDER BY relname
		LOOP
		
		EXECUTE 'CREATE INDEX ' || rc_part || '_sig_prod_date'
			|| ' ON ' || rc_part || '( signature_id, product_version_id, date_processed);';
			
		RAISE INFO 'index created on %',rc_part;
			
	END LOOP;
	
END;$f$;