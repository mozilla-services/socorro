/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

BEGIN;

SELECT try_lock_table('reports');

SELECT add_column_if_not_exists('reports','productid',
$x$ALTER TABLE reports ADD COLUMN productid TEXT;$x$);

COMMIT;