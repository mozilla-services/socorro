/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

DO $f$
DECLARE thisdate DATE;
BEGIN

	thisdate := '2011-11-16';
	
	WHILE thisdate < current_date LOOP
	
		PERFORM backfill_hang_report(thisdate);
		
		thisdate := thisdate + 1;
		
		RAISE INFO 'backfilled %',thisdate;
		
	END LOOP;
	
END; $f$;
