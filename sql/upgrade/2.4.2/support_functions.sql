/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

CREATE OR REPLACE FUNCTION get_cores(
	cpudetails TEXT )
RETURNS INT
IMMUTABLE
LANGUAGE sql
AS $f$
SELECT substring($1 from $x$\| (\d+)$$x$)::INT;
$f$;
