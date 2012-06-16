/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

DO $f$
BEGIN

PERFORM try_lock_table('reports','ACCESS EXCLUSIVE');

ALTER TABLE reports DROP COLUMN build_date;

END;$f$;