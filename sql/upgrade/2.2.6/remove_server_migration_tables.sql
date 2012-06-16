/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP 1

BEGIN;

DROP TABLE IF EXISTS last_tcbsig;
DROP TABLE IF EXISTS last_tcburl;
DROP TABLE IF EXISTS last_urlsig;
DROP TABLE IF EXISTS priorityjobs_log_sjc_backup;
DROP TABLE IF EXISTS sequence_numbers;
DROP TABLE IF EXISTS drop_fks;

END;


